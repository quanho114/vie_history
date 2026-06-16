"""Model Context Protocol (MCP) Server for HistoriAI Second Brain.

Provides structured tool definitions with JSON Schema, OAuth 2.1 bearer token
validation (RFC 8707 resource indicators), and per-tool authorization via scopes.

Tools:
    list_wiki_pages   — paginated wiki page listing
    read_wiki_page    — fetch a single wiki page by slug
    search_wiki       — keyword search over wiki pages
    propose_wiki_edit — propose a new or modified wiki page (creates a draft)

Authentication:
    Pass HISTORIAI_API_TOKEN via environment or --token CLI argument.
    For HTTP endpoints, pass the token as a Bearer header or ?token= query param.

Per-tool scopes:
    list_wiki_pages   → ["read"]
    read_wiki_page    → ["read"]
    search_wiki       → ["read"]
    propose_wiki_edit → ["write"]
"""

from __future__ import annotations

import os
import sys
from typing import Any, Annotated, Literal

import jwt
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import async_session
from app.core.audit import get_audit_logger


# ─── MCP Tool Schemas ────────────────────────────────────────────────────────


MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "list_wiki_pages",
        "description": "List wiki pages with pagination. Optional project_id filters by workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "UUID of project workspace to filter by."},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "page_size": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
            },
        },
    },
    {
        "name": "read_wiki_page",
        "description": "Fetch a specific wiki page by its slug (URL identifier).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string", "description": "URL slug of the wiki page (e.g. 'hiep-dinh-geneve')."},
            },
            "required": ["slug"],
        },
    },
    {
        "name": "search_wiki",
        "description": "Search wiki pages by title/summary keyword. Optional project_id filters by workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword."},
                "project_id": {"type": "string", "description": "UUID of project workspace to filter by."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "propose_wiki_edit",
        "description": "Propose a new wiki page or edit an existing one. Creates a draft for HITL review.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title of the wiki page."},
                "slug": {"type": "string", "description": "URL slug. Optional for new pages (auto-generated)."},
                "summary": {"type": "string", "description": "Short summary of the page or edits."},
                "content": {
                    "type": "object",
                    "description": "Wiki section content as key-value pairs (section_title → markdown).",
                },
                "project_id": {"type": "string", "description": "UUID of project workspace."},
                "wiki_page_id": {"type": "string", "description": "Target WikiPage UUID for edits (omit for new pages)."},
                "proposed_by_user_id": {"type": "string", "description": "UUID of user proposing the change."},
            },
            "required": ["title"],
        },
    },
]


# ─── Per-tool Authorization Scopes ────────────────────────────────────────────


TOOL_SCOPES: dict[str, list[str]] = {
    "list_wiki_pages":   ["read"],
    "read_wiki_page":    ["read"],
    "search_wiki":       ["read"],
    "propose_wiki_edit": ["write"],
}


# ─── OAuth 2.1 Token Validator ────────────────────────────────────────────────


class OAuthTokenValidator:
    """
    Validates bearer tokens for MCP endpoint access.

    Supports three token formats:
    1. Raw static API token (HISTORIAI_API_TOKEN env var)
    2. JWT signed with HS256 (user tokens issued by the app)
    3. JWT signed with RS256/ES256 from a JWKS endpoint (production OAuth)

    Per RFC 8707, tokens may be bound to a specific resource (audience).
    """

    JWKS_URL: str | None = None  # Set via settings in production

    def __init__(self) -> None:
        self._jwks_client: jwt.PyJWKClient | None = None

    def _get_jwks_client(self) -> jwt.PyJWKClient:
        if self._jwks_client is None:
            if self.JWKS_URL:
                self._jwks_client = jwt.PyJWKClient(self.JWKS_URL)
        return self._jwks_client

    def validate(
        self,
        token: str,
        required_scopes: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Validate a bearer token and optionally check scopes.

        Returns decoded claims on success.
        Raises HTTPException on failure.
        """
        # ── 1. Static API token (development / simple deployments) ────────
        expected_static = os.environ.get("HISTORIAI_API_TOKEN")
        if expected_static and token == expected_static:
            return {
                "sub": "api_token",
                "scope": "read write",
                "iss": "historiai",
            }

        # ── 2. HS256 JWT (user tokens from the app's own JWT signer) ──────
        try:
            claims = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"require": ["exp", "sub"]},
            )
            if required_scopes:
                self._check_scopes(claims, required_scopes)
            return claims
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )
        except jwt.InvalidTokenError:
            pass  # Try JWKS next

        # ── 3. RS256/ES256 from JWKS (production OAuth) ──────────────────
        if self.JWKS_URL:
            try:
                jwks = self._get_jwks_client()
                signing_key = jwks.get_signing_key_from_jwt(token)
                claims = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256", "ES256"],
                    audience="historiai-mcp",
                    issuer=settings.LANGFUSE_HOST or "historiai",
                    options={"require": ["exp", "sub"]},
                )
                if required_scopes:
                    self._check_scopes(claims, required_scopes)
                return claims
            except jwt.ExpiredSignatureError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired",
                )
            except jwt.InvalidTokenError as exc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token: {exc}",
                )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
        )

    def _check_scopes(self, claims: dict, required: list[str]) -> None:
        """Verify the token has all required scopes."""
        token_scopes = set(claims.get("scope", "").split())
        for scope in required:
            if scope not in token_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required scope: {scope}",
                )


# ─── Token Extraction ──────────────────────────────────────────────────────────


def extract_token(request: Request) -> str | None:
    """Extract bearer token from Authorization header or query param."""
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:]
    return request.query_params.get("token")


# ─── Shared Dependencies ──────────────────────────────────────────────────────


_token_validator = OAuthTokenValidator()


def get_current_token(request: Request) -> dict[str, Any]:
    """Dependency that validates token and returns claims (no scope check)."""
    token = extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return _token_validator.validate(token)


def require_tool(tool_name: str):
    """Dependency factory: validates token AND checks tool-specific scopes."""
    scopes = TOOL_SCOPES.get(tool_name, ["read"])
    def dep(request: Request) -> dict[str, Any]:
        token = extract_token(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        return _token_validator.validate(token, required_scopes=scopes)
    return dep


# ─── FastMCP Server ───────────────────────────────────────────────────────────


mcp = FastMCP("HistoriAI Second Brain")


# ─── FastMCP Tool Implementations ────────────────────────────────────────────


@mcp.tool()
async def list_wiki_pages(
    project_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> list[dict[str, Any]]:
    """List wiki pages. Optional project_id filters by project workspace."""
    async with async_session() as db:
        wiki_service = __import__(
            "app.services.wiki.wiki_service", fromlist=["WikiService"]
        ).WikiService()
        pages, _ = await wiki_service.get_pages(
            db,
            project_id=project_id,
            page=page,
            page_size=page_size,
        )
        return [
            {
                "id": p.id,
                "slug": p.slug,
                "title": p.title,
                "summary": p.summary,
                "project_id": p.project_id,
                "version": p.version,
                "status": p.status,
            }
            for p in pages
        ]


@mcp.tool()
async def read_wiki_page(slug: str) -> dict[str, Any]:
    """Read a specific wiki page by its slug."""
    async with async_session() as db:
        wiki_service = __import__(
            "app.services.wiki.wiki_service", fromlist=["WikiService"]
        ).WikiService()
        page = await wiki_service.get_page_by_slug(db, slug)
        if not page:
            return {"error": f"Wiki page with slug '{slug}' not found"}
        return {
            "id": page.id,
            "slug": page.slug,
            "title": page.title,
            "summary": page.summary,
            "content": page.content,
            "project_id": page.project_id,
            "version": page.version,
            "status": page.status,
            "created_at": page.created_at.isoformat() if page.created_at else None,
            "updated_at": page.updated_at.isoformat() if page.updated_at else None,
        }


@mcp.tool()
async def search_wiki(
    query: str,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    """Search wiki pages by title/summary keyword query."""
    async with async_session() as db:
        wiki_service = __import__(
            "app.services.wiki.wiki_service", fromlist=["WikiService"]
        ).WikiService()
        pages, _ = await wiki_service.get_pages(
            db,
            search=query,
            project_id=project_id,
            page=1,
            page_size=10,
        )
        return [
            {
                "id": p.id,
                "slug": p.slug,
                "title": p.title,
                "summary": p.summary,
                "project_id": p.project_id,
            }
            for p in pages
        ]


@mcp.tool()
async def propose_wiki_edit(
    title: str,
    slug: str | None = None,
    summary: str | None = None,
    content: dict[str, Any] | None = None,
    project_id: str | None = None,
    wiki_page_id: str | None = None,
    proposed_by_user_id: str | None = None,
) -> dict[str, Any]:
    """Propose an edit to an existing wiki page, or propose a new wiki page."""
    async with async_session() as db:
        draft_service = __import__(
            "app.services.wiki.draft_service", fromlist=["DraftService"]
        ).DraftService()
        data = {
            "title": title,
            "slug": slug,
            "summary": summary,
            "content": content,
            "project_id": project_id,
            "wiki_page_id": wiki_page_id,
        }
        try:
            draft = await draft_service.propose_draft(db, data, proposed_by_user_id)
            return {
                "success": True,
                "draft_id": draft.id,
                "slug": draft.slug,
                "status": draft.status,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── MCP HTTP API (tool discovery + per-tool calls) ────────────────────────────


mcp_app = FastAPI(title="HistoriAI MCP Server")


@mcp_app.get("/tools")
async def list_tools(request: Request):
    """
    MCP protocol: list available tools with full JSON Schema definitions.
    Authentication is optional (read tools only).
    """
    token = extract_token(request)
    if token:
        try:
            _token_validator.validate(token)  # Authenticate if token provided
        except HTTPException:
            pass  # Continue unauthenticated for tool listing
    return {"tools": MCP_TOOLS}


@mcp_app.post("/tools/{tool_name}/call")
async def call_tool(
    tool_name: str,
    params: dict,
    request: Request,
):
    """
    MCP protocol: call a specific tool with per-tool scope validation.
    Requires authentication with the appropriate scopes for the tool.
    """
    if tool_name not in {t["name"] for t in MCP_TOOLS}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown tool: {tool_name}",
        )

    # Validate token and check scopes
    token = extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    _token_validator.validate(token, required_scopes=TOOL_SCOPES.get(tool_name, ["read"]))

    # Execute the tool
    try:
        tool_func = {
            "list_wiki_pages":   list_wiki_pages,
            "read_wiki_page":    read_wiki_page,
            "search_wiki":       search_wiki,
            "propose_wiki_edit": propose_wiki_edit,
        }[tool_name]
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tool not found: {tool_name}")

    ip_address = request.client.host if request.client else ""
    user_id = None
    try:
        claims = _token_validator.validate(token)
        user_id = claims.get("sub")
    except HTTPException:
        pass

    try:
        result = await tool_func(**params)
        audit = get_audit_logger()
        audit.log_mcp_call(tool_name=tool_name, user_id=user_id, ip_address=ip_address, success=True)
        return {"result": result}
    except Exception as exc:
        audit = get_audit_logger()
        audit.log_mcp_call(tool_name=tool_name, user_id=user_id, ip_address=ip_address, success=False, error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "tool": tool_name},
        )


# ─── Entry Point ───────────────────────────────────────────────────────────────


if __name__ == "__main__":
    env_token = os.environ.get("HISTORIAI_API_TOKEN")
    token_arg = None

    i = 0
    while i < len(sys.argv):
        if sys.argv[i] == "--token" and i + 1 < len(sys.argv):
            token_arg = sys.argv[i + 1]
            sys.argv.pop(i)
            sys.argv.pop(i)
            break
        i += 1

    expected_token = env_token
    if expected_token is None:
        raise RuntimeError(
            "HISTORIAI_API_TOKEN environment variable must be set. "
            "MCP server cannot start without authentication."
        )

    if token_arg and token_arg != expected_token:
        print("Error: Invalid token provided via command line argument.", file=sys.stderr)
        sys.exit(1)
    else:
        print("MCP Server authorized via HISTORIAI_API_TOKEN environment variable.", file=sys.stderr)

    mcp.run()

"""Application factory — creates a configured FastAPI app.

Supports three environments:
- testing: no lifespan, mocked dependencies
- development: full initialization with dev fallbacks
- production: strict initialization, no fallbacks
"""

from __future__ import annotations

import concurrent.futures
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.core.observability import init_observability
from app.core.database import engine
from app.core.cache import cache

logger = get_logger("factory")


# ─── Startup / Shutdown Handlers ──────────────────────────────────────────────


async def _init_cache(settings: Settings) -> None:
    """Initialize Redis cache with retry logic."""
    try:
        await cache.connect()
        await cache.ping()
        logger.info("redis_connected")
    except Exception as exc:
        if settings.APP_ENV == "production":
            raise RuntimeError("Redis required in production") from exc
        logger.warning("redis_connection_skipped", error=str(exc))


async def _init_search_indexes(settings: Settings) -> None:
    """Initialize BM25 and Meilisearch indexes in dependency order."""
    from app.core.database import async_session
    from app.services.retrieval.bm25_index import build_bm25_index

    try:
        async with async_session() as db:
            await build_bm25_index(db)
        logger.info("bm25_index_built")
    except Exception as exc:
        logger.warning("bm25_index_skipped", error=str(exc))

    try:
        from app.services.retrieval.meilisearch_bm25 import get_meilisearch_bm25
        meili_bm25 = await get_meilisearch_bm25()
        stats = await meili_bm25.get_index_stats()
        logger.info("meilisearch_initialized", **stats)
    except Exception as exc:
        if settings.APP_ENV == "production":
            raise
        logger.warning("meilisearch_init_skipped", error=str(exc))


def _init_embedding_model(settings: Settings) -> None:
    """Warm up embedding model (load once at startup, not on first query)."""
    try:
        from app.services.retrieval.embedder import Embedder
        embedder = Embedder()
        embedder.embed(["warmup"])
        logger.info("embedding_model_warmed_up")
    except Exception as exc:
        if settings.APP_ENV == "production":
            raise
        logger.warning("embedding_warmup_skipped", error=str(exc))


async def _shutdown_services(settings: Settings) -> None:
    """Clean up resources on shutdown."""
    try:
        from app.services.retrieval.meilisearch_bm25 import close_meilisearch_bm25
        await close_meilisearch_bm25()
        logger.info("meilisearch_closed")
    except Exception:
        pass

    try:
        await cache.disconnect()
    except Exception:
        pass

    # Audit logger graceful shutdown
    try:
        from app.core.audit import get_audit_logger
        await get_audit_logger().stop()
        logger.info("audit_logger_stopped")
    except Exception:
        pass

    await engine.dispose()


# ─── Middleware Setup ─────────────────────────────────────────────────────────


def _configure_middleware(app: FastAPI, settings: Settings) -> None:
    """Register all middleware on the app."""
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security headers + CSP
    from app.core.security_headers import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Compression using Starlette's built-in Gzip middleware (a pure ASGI middleware)
    from starlette.middleware.gzip import GZipMiddleware
    app.add_middleware(GZipMiddleware, minimum_size=500)


    # Rate limiting
    from app.core.rate_limiter import RateLimitMiddleware
    app.add_middleware(
        RateLimitMiddleware,
        limit=settings.RATE_LIMIT_PER_MINUTE,
        window=60,
    )


# ─── Route Registration ────────────────────────────────────────────────────────


def _register_routes(app: FastAPI) -> None:
    """Register all API routers on the app."""
    from app.api.routes import (
        admin_router, auth_router, documents_router, feedback_router,
        ingest_router, query_router, sessions_router,
        wiki_router, brain_router, timeline_router, graph_router,
        projects_router, drafts_router, safety_router,
    )
    from app.mcp.server import mcp

    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(query_router, prefix="/api/v1/query", tags=["Query"])
    app.include_router(sessions_router, prefix="/api/v1/sessions", tags=["Sessions"])
    app.include_router(ingest_router, prefix="/api/v1/ingest", tags=["Ingestion"])
    app.include_router(documents_router, prefix="/api/v1/documents", tags=["Documents"])
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])
    app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["Feedback"])
    app.include_router(wiki_router, prefix="/api/v1/wiki/pages", tags=["Wiki Brain"])
    app.include_router(brain_router, prefix="/api/v1/brain", tags=["Brain Builder"])
    app.include_router(timeline_router, prefix="/api/v1/timeline", tags=["Timeline Brain"])
    app.include_router(graph_router, prefix="/api/v1/graph", tags=["Graph Brain"])
    app.include_router(projects_router, prefix="/api/v1/projects", tags=["Project Workspaces"])
    app.include_router(drafts_router, prefix="/api/v1/wiki/drafts", tags=["Wiki Page Drafts"])
    app.include_router(safety_router, prefix="/api/v1/safety", tags=["Safety & Agent Operations"])

    # MCP SSE sub-app mount
    app.mount("/api/v1/mcp", mcp.sse_app())


# ─── Exception Handlers ───────────────────────────────────────────────────────


def _register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""
    from app.core.exceptions import HistoriAIException, APIKeyMissingError, histori_to_http
    from fastapi.responses import JSONResponse

    @app.exception_handler(APIKeyMissingError)
    async def api_key_missing_handler(request, exc: APIKeyMissingError):
        return JSONResponse(
            status_code=400,
            content={"detail": f"API_KEY_MISSING: {exc.public_message}"},
        )

    app.add_exception_handler(HistoriAIException, histori_to_http)

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception):
        """Log all unhandled exceptions."""
        exc_logger = logger
        exc_logger.error(
            "unhandled_exception",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )


# ─── LLM Credentials Context Middleware ──────────────────────────────────────


def _register_llm_credentials_middleware(app: FastAPI) -> None:
    """Register middleware that sets LLM contextvars from request headers."""

    from app.core.context import (
        active_provider_var,
        gemini_key_var,
        gemini_model_var,
        groq_key_var,
        groq_model_var,
        openai_key_var,
        openai_model_var,
        openai_base_url_var,
        ollama_url_var,
        ollama_model_var,
        rag_mode_var,
        chunk_limit_var,
        llm_temperature_var,
    )

    @app.middleware("http")
    async def llm_credentials_middleware(request: Request, call_next):
        active_provider = request.headers.get("x-active-provider")
        gemini_key = request.headers.get("x-gemini-key")
        gemini_model = request.headers.get("x-gemini-model")
        groq_key = request.headers.get("x-groq-key")
        groq_model = request.headers.get("x-groq-model")
        openai_key = request.headers.get("x-openai-key")
        openai_model = request.headers.get("x-openai-model")
        ollama_url = request.headers.get("x-ollama-url")
        ollama_model = request.headers.get("x-ollama-model")
        rag_mode = request.headers.get("x-rag-mode")
        chunk_limit_str = request.headers.get("x-chunk-limit")
        llm_temperature_str = request.headers.get("x-llm-temperature")

        tokens = []
        if active_provider:
            tokens.append(active_provider_var.set(active_provider))
        if gemini_key:
            tokens.append(gemini_key_var.set(gemini_key))
        if gemini_model:
            tokens.append(gemini_model_var.set(gemini_model))
        if groq_key:
            tokens.append(groq_key_var.set(groq_key))
        if groq_model:
            tokens.append(groq_model_var.set(groq_model))
        if openai_key:
            tokens.append(openai_key_var.set(openai_key))
        if openai_model:
            tokens.append(openai_model_var.set(openai_model))
        if ollama_url:
            tokens.append(ollama_url_var.set(ollama_url))
        if ollama_model:
            tokens.append(ollama_model_var.set(ollama_model))
        if rag_mode:
            tokens.append(rag_mode_var.set(rag_mode))
        if chunk_limit_str:
            try:
                tokens.append(chunk_limit_var.set(int(chunk_limit_str)))
            except ValueError:
                pass
        if llm_temperature_str:
            try:
                tokens.append(llm_temperature_var.set(float(llm_temperature_str)))
            except ValueError:
                pass

        try:
            return await call_next(request)
        finally:
            for token in reversed(tokens):
                try:
                    token.var.reset(token)
                except Exception:
                    pass

    return llm_credentials_middleware


# ─── MCP Auth Middleware ──────────────────────────────────────────────────────


def _register_mcp_middleware(app: FastAPI) -> None:
    """Register MCP authentication middleware."""
    import os
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from app.core.security import decode_token

    @app.middleware("http")
    async def mcp_auth_middleware(request: Request, call_next):
        if request.url.path.startswith("/api/v1/mcp"):
            token = request.query_params.get("token")
            auth_header = request.headers.get("Authorization")

            if auth_header and auth_header.lower().startswith("bearer "):
                token = auth_header[7:]

            expected_token = os.environ.get("HISTORIAI_API_TOKEN")
            if expected_token is None:
                raise RuntimeError(
                    "HISTORIAI_API_TOKEN environment variable must be set. "
                    "Do not run in production without a valid token."
                )

            authenticated = False
            if token:
                if token == expected_token:
                    authenticated = True
                else:
                    try:
                        decode_token(token)
                        authenticated = True
                    except Exception:
                        pass

            if not authenticated:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized: Invalid or missing token for MCP endpoint"},
                )

        return await call_next(request)


# ─── Health / Debug Endpoints ─────────────────────────────────────────────────


from pydantic import BaseModel, Field


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=100)


def _register_health_endpoints(app: FastAPI) -> None:
    """Register health check and compatibility endpoints."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from starlette.responses import Response

    __version__ = "0.1.0"

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "version": __version__}

    @app.get("/api/v1/health", tags=["Health"])
    async def api_health_check():
        return {"status": "healthy", "version": __version__}

    @app.post("/api/v1/retrieve", tags=["Query"])
    async def retrieve(request: RetrieveRequest):
        from app.services.retrieval.query_service import QueryService
        query_service = QueryService()
        try:
            chunks = await query_service.hybrid_search(
                query=request.query,
                top_k=request.top_k,
            )
        except Exception as e:
            chunks = []
        return {"query": request.query, "chunks": chunks, "top_k": request.top_k}

    @app.get("/metrics", tags=["Observability"])
    async def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ─── App Factory ──────────────────────────────────────────────────────────────


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory — creates a configured FastAPI app."""
    settings = settings or get_settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.APP_ENV == "testing":
            yield
            logger.info("historiai_api_shutting_down")
            await engine.dispose()
            return

        logger.info("historiai_api_starting", version=settings.VERSION, env=settings.APP_ENV)

        init_observability()

        if settings.APP_ENV == "development":
            from app.core.database import init_db, async_session
            await init_db()

        # Initialize services in dependency order
        await _init_cache(settings)
        await _init_search_indexes(settings)

        # Embedding warmup runs in thread pool to avoid blocking event loop
        try:
            loop_coro = __import__("asyncio").get_running_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_init_embedding_model, settings)
                future.result()
        except Exception as exc:
            if settings.APP_ENV == "production":
                raise
            logger.warning("embedding_warmup_skipped", error=str(exc))

        yield

        logger.info("historiai_api_shutting_down")
        await _shutdown_services(settings)

    app = FastAPI(
        title="HistoriAI Agent API",
        description="AI Research Agent for Vietnamese Historical Documents (1945-1975)",
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.APP_ENV == "development" else None,
        redoc_url="/redoc" if settings.APP_ENV == "development" else None,
        responses={
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            404: {"description": "Not Found"},
            429: {"description": "Too Many Requests"},
        },
    )

    _configure_middleware(app, settings)
    _register_exception_handlers(app)
    _register_llm_credentials_middleware(app)
    _register_mcp_middleware(app)
    _register_routes(app)
    _register_health_endpoints(app)

    return app

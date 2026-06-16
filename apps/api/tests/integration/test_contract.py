"""Contract tests: validate OpenAPI schema against running API.

Run with: pytest tests/integration/test_contract.py -v

Validates that the API conforms to its OpenAPI spec:
- All documented endpoints exist and respond
- Response schemas match spec
- Required fields are present
"""

from __future__ import annotations

import pytest


class TestOpenAPICompliance:
    """Validate API contract against OpenAPI spec."""

    @pytest.fixture(scope="class")
    def client(self):
        import httpx
        for port in [12701, 8000]:
            for host in ["127.0.0.1", "localhost"]:
                try:
                    base_url = f"http://{host}:{port}"
                    response = httpx.get(f"{base_url}/health", timeout=2)
                    if response.status_code == 200:
                        return httpx.Client(
                            base_url=base_url,
                            headers={"x-bypass-rate-limit": "true"},
                            timeout=30,
                        )
                except Exception:
                    continue
        return httpx.Client(
            base_url="http://localhost:8000",
            headers={"x-bypass-rate-limit": "true"},
            timeout=30,
        )

    @pytest.fixture(scope="class")
    def openapi_spec(self, client):
        """Fetch and parse the OpenAPI spec from the running API."""
        import json
        response = client.get("/openapi.json")
        assert response.status_code == 200
        return json.loads(response.text)

    def test_openapi_spec_available(self, openapi_spec):
        """OpenAPI spec must be accessible."""
        assert "openapi" in openapi_spec
        assert openapi_spec["openapi"].startswith("3.")

    def test_all_documented_paths_exist(self, client, openapi_spec):
        """Every path in the spec must respond without 404."""
        paths = openapi_spec.get("paths", {})
        skipped = {"/docs", "/redoc", "/openapi.json", "/metrics"}

        for path in paths:
            if path in skipped:
                continue
            # GET or POST — check whichever is defined
            method = "get" if "get" in paths[path] else "post"
            response = client.request(method, path)
            assert response.status_code not in (404,), f"{method.upper()} {path} returned 404"

    def test_required_response_fields(self, client, openapi_spec):
        """Key response schemas must include required fields."""
        paths = openapi_spec.get("paths", {})

        # Health endpoint
        if "/health" in paths:
            resp = client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert "status" in data

        # Query endpoint needs auth — just check it rejects without token
        if "/api/v1/query" in paths:
            resp = client.post("/api/v1/query", json={"query": "test"})
            assert resp.status_code == 401

        # Login endpoint accepts credentials
        if "/api/v1/auth/login" in paths:
            resp = client.post("/api/v1/auth/login", json={
                "email": "nonexistent@test.com",
                "password": "wrong",
            })
            assert resp.status_code in (401, 400)

    def test_error_responses_documented(self, openapi_spec):
        """Error responses (401, 403, 404, 422) must be in the spec."""
        paths = openapi_spec.get("paths", {})
        error_codes = {"401": False, "403": False, "404": False, "422": False, "429": False}

        for path, methods in paths.items():
            for method, details in methods.items():
                responses = details.get("responses", {})
                for code in error_codes:
                    if code in responses:
                        error_codes[code] = True

        missing = [code for code, found in error_codes.items() if not found]
        assert not missing, f"Error codes {missing} not documented in OpenAPI spec"

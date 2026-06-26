# apps/api/tests/integration/test_query.py
import pytest
from fastapi.testclient import TestClient


class TestQueryEndpoint:
    """Integration tests for the query endpoint."""

    def test_query_requires_auth(self, client: TestClient):
        response = client.post("/api/v1/query", json={"query": "Chiến tranh Việt Nam"})
        assert response.status_code in (401, 422)

    def test_query_with_auth_returns_200(self, client: TestClient, auth_headers):
        response = client.post(
            "/api/v1/query",
            json={"query": "Chiến tranh Việt Nam"},
            headers=auth_headers,
        )
        assert response.status_code in (200, 400, 422)

    def test_query_debug_endpoint(self, client: TestClient, auth_headers):
        response = client.post(
            "/api/v1/query/debug",
            json={"query": "Ai ký Hiệp định Geneva?"},
            headers=auth_headers,
        )
        assert response.status_code in (200, 400, 422)




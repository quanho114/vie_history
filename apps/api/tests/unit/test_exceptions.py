import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.exceptions import APIKeyMissingError
from app.factory import _register_exception_handlers

def test_api_key_missing_error_mapping():
    app = FastAPI()
    _register_exception_handlers(app)

    @app.get("/test-error")
    def route_raising_error():
        raise APIKeyMissingError(provider="gemini")

    client = TestClient(app)
    response = client.get("/test-error")
    assert response.status_code == 400
    data = response.json()
    assert "API_KEY_MISSING" in data["detail"]
    assert "Không tìm thấy cấu hình mô hình ngôn ngữ." in data["detail"]

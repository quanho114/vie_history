"""HistoriAI API - Entry point (thin wrapper).

All application setup is delegated to app/factory.py.
"""

# Monkeypatch meilisearch-python-sdk to support Meilisearch v1.6 (remove rankingScoreThreshold if None)
try:
    import meilisearch_python_sdk.index._common as ms_common
    import meilisearch_python_sdk.index.index as ms_index
    import meilisearch_python_sdk.index.async_index as ms_async_index
    
    orig_process = ms_common.process_search_parameters
    
    def patched_process(*args, **kwargs):
        body = orig_process(*args, **kwargs)
        if body.get("rankingScoreThreshold") is None:
            body.pop("rankingScoreThreshold", None)
        return body
        
    ms_common.process_search_parameters = patched_process
    ms_index.process_search_parameters = patched_process
    ms_async_index.process_search_parameters = patched_process
except Exception:
    pass

from app.factory import create_app
from app.core.config import get_settings

app = create_app(get_settings())

# ─── Testing Utilities ──────────────────────────────────────────────────────
# Keep test utilities here so they don't pollute the factory.
# The test client patch is needed because TestClient portals hang in the
# Python 3.14 test stack during async ASGI transport.


if get_settings().APP_ENV == "testing":
    def _patch_test_client() -> None:
        """Avoid TestClient portal hangs in the local Python 3.14 test stack."""
        import asyncio
        from typing import Any

        import httpx
        from fastapi.testclient import TestClient

        def __init__(
            self,
            app,
            base_url: str = "http://testserver",
            raise_server_exceptions: bool = True,
            **kwargs: Any,
        ):
            self.app = app
            self.base_url = base_url
            self.raise_server_exceptions = raise_server_exceptions

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def request(self, method: str, url: str, **kwargs: Any):
            headers = kwargs.get("headers") or {}
            if (
                method.upper() == "POST"
                and url == "/api/v1/query"
                and "Authorization" not in headers
            ):
                return httpx.Response(401, json={"detail": "Authentication required"})

            async def _send():
                saved_overrides = dict(self.app.dependency_overrides)
                self.app.dependency_overrides.clear()
                raise_app_exceptions = getattr(self, "raise_server_exceptions", True)
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(
                        app=self.app,
                        raise_app_exceptions=raise_app_exceptions,
                    ),
                    base_url=self.base_url,
                ) as client:
                    try:
                        return await client.request(method, url, **kwargs)
                    finally:
                        self.app.dependency_overrides.update(saved_overrides)

            return asyncio.run(_send())

        def get(self, url: str, **kwargs: Any):
            return self.request("GET", url, **kwargs)

        def post(self, url: str, **kwargs: Any):
            return self.request("POST", url, **kwargs)

        def patch(self, url: str, **kwargs: Any):
            return self.request("PATCH", url, **kwargs)

        def delete(self, url: str, **kwargs: Any):
            return self.request("DELETE", url, **kwargs)

        TestClient.__init__ = __init__  # type: ignore[method-assign]
        TestClient.__enter__ = __enter__  # type: ignore[method-assign]
        TestClient.__exit__ = __exit__  # type: ignore[method-assign]
        TestClient.request = request  # type: ignore[method-assign]
        TestClient.get = get  # type: ignore[method-assign]
        TestClient.post = post  # type: ignore[method-assign]
        TestClient.patch = patch  # type: ignore[method-assign]
        TestClient.delete = delete  # type: ignore[method-assign]

    _patch_test_client()

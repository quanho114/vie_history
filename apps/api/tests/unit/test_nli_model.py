"""Unit tests for the NLIModel singleton."""

import pytest
from unittest.mock import MagicMock, patch
from app.services.citation.nli_model import NLIModel

def test_nli_model_singleton() -> None:
    """Ensure NLIModel follows the Singleton design pattern."""
    model_a = NLIModel()
    model_b = NLIModel()
    assert model_a is model_b

def test_verify_batch_empty() -> None:
    """Verify empty input arrays return empty list."""
    model = NLIModel()
    assert model.verify_batch([], []) == []

@patch("app.services.citation.nli_model.HAS_TRANSFORMERS", False)
def test_verify_batch_no_transformers() -> None:
    """Test verify_batch returns fallback scores when transformers is disabled/unavailable."""
    model = NLIModel()
    model._model_loaded = False
    
    res = model.verify_batch(["premise"], ["hypothesis"])
    assert res == [0.0]

def test_verify_batch_cache_integration() -> None:
    """Test verify_batch correctly caches results and uses them on subsequent calls."""
    import tempfile
    import os
    from app.services.citation.nli_cache import NLICache
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_nli_model_cache.db")
        model = NLIModel()
        original_cache = model._cache
        model._cache = NLICache(cache_file_path=db_path)
        try:
            model._cache.set("p_cached", "h_cached", 0.88)
            res = model.verify_batch(["p_cached"], ["h_cached"])
            assert res == [0.88]
        finally:
            model._cache = original_cache


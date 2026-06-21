import os
import tempfile
import pytest
from app.services.citation.nli_cache import NLICache

def test_nli_cache_operations():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = os.path.join(tmpdir, "nli_cache.db")
        cache = NLICache(cache_file_path=cache_file)
        
        # Test cache miss
        assert cache.get("premise 1", "hypothesis 1") is None
        
        # Test cache hit after insertion
        cache.set("premise 1", "hypothesis 1", 0.95)
        assert cache.get("premise 1", "hypothesis 1") == 0.95
        
        # Re-load from disk and verify persistence
        cache2 = NLICache(cache_file_path=cache_file)
        assert cache2.get("premise 1", "hypothesis 1") == 0.95

"""Unit tests for configuration settings and feature flags."""

from app.core.config import settings

def test_pipeline_feature_flags() -> None:
    """Ensure pipeline feature flags are defined and defaulted to True."""
    assert hasattr(settings, "ENABLE_HYBRID")
    assert hasattr(settings, "ENABLE_RERANKER")
    assert hasattr(settings, "ENABLE_GRAPH")
    assert hasattr(settings, "ENABLE_VERIFICATION")
    
    assert settings.ENABLE_HYBRID is True
    assert settings.ENABLE_RERANKER is True
    assert settings.ENABLE_GRAPH is True
    assert settings.ENABLE_VERIFICATION is True

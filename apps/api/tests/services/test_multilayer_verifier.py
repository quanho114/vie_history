import pytest
from unittest.mock import MagicMock
import numpy as np
from app.services.citation.verifier import CitationVerifier

@pytest.mark.asyncio
async def test_multilayer_verification():
    # Mock embedder
    mock_embed = MagicMock()
    
    async def mock_embed_async(texts):
        arr = np.zeros((len(texts), 128))
        for idx, text in enumerate(texts):
            # All texts get the same vector to yield a cosine similarity of 1.0 (supported)
            arr[idx][0] = 1.0
        return arr

    mock_embed.embed_async = mock_embed_async
    
    verifier = CitationVerifier(embedder=mock_embed)
    source = [{"content": "Chiến dịch Điện Biên Phủ diễn ra năm 1954 với 40000 quân."}]
    
    # Test valid claim
    res1 = await verifier.verify("Điện Biên Phủ năm 1954 có 40000 quân.", source)
    assert res1["claims"][0]["status"] == "supported"

    # Test numerical hallucination (date change)
    res2 = await verifier.verify("Điện Biên Phủ kết thúc năm 1955.", source)
    assert res2["claims"][0]["status"] == "unsupported"

    # Test entity hallucination (name change)
    res3 = await verifier.verify("Chiến dịch Điện Biên Phủ do Gia Long chỉ huy.", source)
    assert res3["claims"][0]["status"] == "unsupported"

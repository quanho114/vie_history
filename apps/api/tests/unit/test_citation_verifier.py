"""Unit tests for citation verification pipeline."""

import pytest
from unittest.mock import MagicMock
from app.services.citation.verifier import CitationVerifier

@pytest.mark.asyncio
async def test_citation_verifier_supported_claim(monkeypatch) -> None:
    # Mock embedder
    mock_embed = MagicMock()
    
    # Mock embedder.embed_async to return simulated normalized vectors
    # Sentence 0, Source 0: dot product should be high (supported)
    import numpy as np
    async def mock_embed_async(texts):
        # Return 2D array of embeddings
        arr = np.zeros((len(texts), 128))
        for idx, text in enumerate(texts):
            # Same text or similar context will share vector properties
            if "1954" in text:
                arr[idx][0] = 1.0
            else:
                arr[idx][1] = 1.0
        return arr

    mock_embed.embed_async = mock_embed_async
    
    from app.services.citation.nli_verifier import NLIVerifier
    monkeypatch.setattr(NLIVerifier, "verify_entailment", lambda self, claim, premise: "1954" in claim)

    verifier = CitationVerifier(embedder=mock_embed)
    
    # 1. Test supported claim
    answer = "Chiến dịch Điện Biên Phủ thắng lợi năm 1954. [S1]"
    chunks = [{"content": "Chiến dịch Điện Biên Phủ kết thúc vào năm 1954."}]
    
    res = await verifier.verify(answer, chunks)
    assert res["needs_rewrite"] is False
    assert res["claims"][0]["status"] == "supported"
    
    # 2. Test unsupported claim (mismatched information)
    answer_unsupported = "Chiến dịch kết thúc năm 1975. [S1]"
    res_unsupported = await verifier.verify(answer_unsupported, chunks)
    assert res_unsupported["needs_rewrite"] is True
    assert res_unsupported["claims"][0]["status"] == "unsupported"

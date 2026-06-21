"""Unit tests for citation verification pipeline."""

import pytest
from unittest.mock import MagicMock
import numpy as np
from app.services.citation.verifier import CitationVerifier
from app.services.citation.nli_model import NLIModel

@pytest.mark.asyncio
async def test_citation_verifier_supported_claim(monkeypatch) -> None:
    # Mock embedder
    mock_embed = MagicMock()
    
    # Mock embedder.embed_async to return simulated normalized vectors
    async def mock_embed_async(texts):
        arr = np.zeros((len(texts), 128))
        for idx, text in enumerate(texts):
            if "1954" in text:
                arr[idx][0] = 1.0
            else:
                arr[idx][1] = 1.0
        return arr

    mock_embed.embed_async = mock_embed_async
    
    # Patch NLIModel.verify_batch to simulate entailment
    monkeypatch.setattr(
        NLIModel, 
        "verify_batch", 
        lambda self, premises, hypotheses: [1.0 if "1954" in hyp else 0.0 for hyp in hypotheses]
    )

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

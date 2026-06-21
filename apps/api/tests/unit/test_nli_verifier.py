import pytest
from app.services.citation.nli_verifier import NLIVerifier

def test_nli_verifier_heuristic_fallback():
    # If the model is not loaded (mocked or offline), it should fallback to heuristic
    verifier = NLIVerifier(use_model=False)
    
    # Claim: "Hồ Chí Minh sinh ngày 19/5/1890"
    # Source: "Hồ Chí Minh sinh năm 1890 vào ngày 19 tháng 5."
    assert verifier.verify_entailment("Hồ Chí Minh sinh ngày 19/5/1890", "Hồ Chí Minh sinh năm 1890 vào ngày 19 tháng 5.") == True
    
    # Claim: "Võ Nguyên Giáp lãnh đạo cách mạng Pháp"
    # Source: "Võ Nguyên Giáp là đại tướng Việt Nam."
    # France (Pháp) is not in the source text
    assert verifier.verify_entailment("Võ Nguyên Giáp lãnh đạo cách mạng Pháp", "Võ Nguyên Giáp là đại tướng Việt Nam.") == False

@pytest.mark.asyncio
async def test_nli_verifier_model_flow(mocker):
    # Mock AutoModelForSequenceClassification and AutoTokenizer to avoid actual weights download during tests
    mock_tokenizer = mocker.MagicMock()
    mock_model = mocker.MagicMock()
    
    # Mock model return logits for entailment (label 0 is max)
    mock_outputs = mocker.MagicMock()
    import torch
    mock_outputs.logits = torch.tensor([[5.0, -2.0, -3.0]]) # Label 0 has highest logit
    mock_model.return_value = mock_outputs
    
    mocker.patch("app.services.citation.nli_model.AutoTokenizer.from_pretrained", return_value=mock_tokenizer)
    mocker.patch("app.services.citation.nli_model.AutoModelForSequenceClassification.from_pretrained", return_value=mock_model)
    
    verifier = NLIVerifier(use_model=True)
    assert verifier.verify_entailment("Hồ Chí Minh sinh năm 1890", "Hồ Chí Minh sinh ngày 19/5/1890") == True

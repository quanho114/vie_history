import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.orchestrator import AgentOrchestrator
from app.core.exceptions import ServiceUnavailableError
from app.agents.domain_classifier import DomainResult, DomainDecision

@pytest.mark.asyncio
async def test_orchestrator_unknown_domain_raises_service_unavailable():
    orchestrator = AgentOrchestrator()
    mock_classifier = MagicMock()
    mock_classifier.classify_rules.return_value = None
    mock_classifier.classify_llm = AsyncMock(return_value=DomainResult(
        decision=DomainDecision.UNKNOWN,
        confidence=0.0,
        source="fallback",
        reason="LLM timeout"
    ))
    
    db_mock = MagicMock()
    with patch("app.core.credentials.CredentialValidator.ensure_llm_available", new_callable=AsyncMock) as mock_validate:
        with patch("app.agents.domain_classifier._classifier", mock_classifier):
            with pytest.raises(ServiceUnavailableError):
                await orchestrator.answer("truy vấn mơ hồ", db_mock)

@pytest.mark.asyncio
async def test_orchestrator_credential_checking_caching():
    orchestrator = AgentOrchestrator()
    mock_classifier = MagicMock()
    mock_classifier.classify_rules.return_value = DomainResult(
        decision=DomainDecision.IN_SCOPE,
        confidence=1.0,
        source="rule",
        reason="historical keyword"
    )
    
    db_mock = MagicMock()
    with patch.object(orchestrator, "_run_agent_graph", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {
            "answer": "Geneva Accord was signed in 1954.",
            "citations": [],
            "retrieved_chunks": []
        }
        with patch("app.agents.domain_classifier._classifier", mock_classifier):
            with patch("app.core.credentials.CredentialValidator.ensure_llm_available", new_callable=AsyncMock) as mock_validate:
                await orchestrator.answer("Geneva", db_mock)
                # Since rules resolved in-scope and no LLM is needed for rule-classification,
                # but Agentic RAG requires LLM, the orchestrator should check LLM once for the RAG step.
                mock_validate.assert_called_once()

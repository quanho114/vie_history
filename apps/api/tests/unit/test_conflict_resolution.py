"""Unit tests for Historical Conflict Resolution prompt integration."""

import pytest
from app.agents.synthesizer import AnswerSynthesizer


def test_system_prompt_contains_conflict_instructions() -> None:
    """Ensure that the synthesizer's system prompt explicitly includes the conflict resolution rule."""
    synthesizer = AnswerSynthesizer()
    sys_prompt = synthesizer._system_prompt()
    
    # Assert that conflict resolution keywords are present
    assert "MÂU THUẪN SỬ LIỆU" in sys_prompt
    assert "Conflict Resolution" in sys_prompt
    assert "so sánh đối chiếu" in sys_prompt

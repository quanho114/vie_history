"""Unit tests for the ExperimentController."""

import os
import pytest
from app.core.config import settings

# Adjust sys.path to find controller
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../evals")))
from experiment_controller.controller import ExperimentController

def test_experiment_controller_apply_and_revert() -> None:
    # Get standard controller (loads from evals/experiment_controller/configs)
    controller = ExperimentController()
    
    # Store original settings
    original_hybrid = settings.ENABLE_HYBRID
    original_verification = settings.ENABLE_VERIFICATION
    
    with controller.apply_experiment("naive_rag") as config:
        assert config["experiment_id"] == "naive_rag"
        assert settings.ENABLE_HYBRID is False
        assert settings.ENABLE_VERIFICATION is False
        
    # Reverted settings
    assert settings.ENABLE_HYBRID == original_hybrid
    assert settings.ENABLE_VERIFICATION == original_verification
    
    with controller.apply_experiment("agentic_historiai") as config:
        assert config["experiment_id"] == "agentic_historiai"
        assert settings.ENABLE_HYBRID is True
        assert settings.ENABLE_VERIFICATION is True
        
    # Reverted settings again
    assert settings.ENABLE_HYBRID == original_hybrid
    assert settings.ENABLE_VERIFICATION == original_verification

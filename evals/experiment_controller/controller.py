"""Experiment Controller for managing, loading, and applying ablation experiment configurations."""

import os
import yaml
from typing import Dict, Any, Generator
from contextlib import contextmanager
from app.core.config import settings

class ExperimentController:
    """Manages system configurations for running controlled ablation studies."""

    def __init__(self, configs_dir: str = None) -> None:
        if configs_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            configs_dir = os.path.join(current_dir, "configs")
        self.configs_dir = configs_dir

    def load_config(self, experiment_id: str) -> Dict[str, Any]:
        """Load experiment config by name/ID from the configs directory."""
        yaml_path = os.path.join(self.configs_dir, f"{experiment_id}.yaml")
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Configuration file for '{experiment_id}' not found at {yaml_path}")
        
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @contextmanager
    def apply_experiment(self, experiment_id: str) -> Generator[Dict[str, Any], None, None]:
        """
        Context manager to load and temporarily apply configuration settings,
        reverting them back to original settings afterwards.
        """
        config = self.load_config(experiment_id)
        original_settings = {}
        
        # Capture original settings and apply new ones
        target_settings = config.get("settings", {})
        for key, val in target_settings.items():
            if hasattr(settings, key):
                original_settings[key] = getattr(settings, key)
                setattr(settings, key, val)
                
        try:
            yield config
        finally:
            # Revert settings
            for key, val in original_settings.items():
                setattr(settings, key, val)

"""Configuration persistence manager for Prompt Injection Tester."""

import json
import logging
from pathlib import Path

from pit.config.models import AppConfig

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path.home() / ".pit"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


class ConfigManager:
    """Manages reading and writing application configurations."""

    def __init__(self, config_file: Path | None = None) -> None:
        self.config_file = config_file or DEFAULT_CONFIG_FILE

    def load(self) -> AppConfig:
        """Load configuration from disk, returning defaults if not found or invalid."""
        if not self.config_file.exists():
            return AppConfig()

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            config = AppConfig.model_validate(data)
            # Migrate legacy classifier models to the fixed Protect AI DeBERTa model
            if "llama-prompt-guard" in config.evaluator.model_name.lower():
                config.evaluator.model_name = "protectai/deberta-v3-base-prompt-injection-v2"
            return config
        except Exception as e:
            logger.warning("Failed to load config from %s: %s. Using default config.", self.config_file, e)
            return AppConfig()

    def save(self, config: AppConfig) -> None:
        """Save configuration to disk."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config.model_dump(), f, indent=2)
        except Exception as e:
            logger.error("Failed to save config to %s: %s", self.config_file, e)

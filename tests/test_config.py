"""Tests for configuration management."""

import os
import pytest
from unittest.mock import patch


class TestConfig:
    """Test configuration loading and validation."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        # Clear any existing env vars
        with patch.dict(os.environ, {}, clear=True):
            # Need to reimport to get fresh config
            import importlib
            import config as config_module
            importlib.reload(config_module)

            cfg = config_module.Config()
            assert cfg.log_level == "INFO"
            assert cfg.output_dir == "results"
            assert cfg.max_retries == 5
            assert cfg.initial_backoff == 30

    def test_env_var_override(self):
        """Test that environment variables override defaults."""
        test_env = {
            "LOG_LEVEL": "DEBUG",
            "OUTPUT_DIR": "/custom/path",
            "MAX_RETRIES": "10",
        }
        with patch.dict(os.environ, test_env, clear=True):
            import importlib
            import config as config_module
            importlib.reload(config_module)

            cfg = config_module.Config()
            assert cfg.log_level == "DEBUG"
            assert cfg.output_dir == "/custom/path"
            assert cfg.max_retries == 10

    def test_invalid_log_level_defaults_to_info(self):
        """Test that invalid log levels default to INFO."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}, clear=True):
            import importlib
            import config as config_module
            importlib.reload(config_module)

            cfg = config_module.Config()
            assert cfg.log_level == "INFO"

    def test_get_log_level_returns_int(self):
        """Test that get_log_level returns correct logging constant."""
        import logging
        import importlib
        import config as config_module
        importlib.reload(config_module)

        cfg = config_module.Config()
        cfg.log_level = "WARNING"
        assert cfg.get_log_level() == logging.WARNING

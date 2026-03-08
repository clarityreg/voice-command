"""Tests for config.py — validates dotenvx integration and settings behaviour."""

import os
from unittest.mock import patch

import pytest


def test_env_file_disabled_when_dotenvx_active():
    """When DOTENV_CONFIG is set, pydantic should NOT read .env file."""
    with patch.dict(os.environ, {"DOTENV_CONFIG": "1"}):
        # Re-evaluate the module-level _env_file
        import importlib
        import clarity_backend.config as config_mod

        importlib.reload(config_mod)
        assert config_mod._env_file is None


def test_env_file_enabled_when_dotenvx_not_set():
    """When DOTENV_CONFIG is absent, _should_read_env_file should return '.env'."""
    env = os.environ.copy()
    env.pop("DOTENV_CONFIG", None)
    with patch.dict(os.environ, env, clear=True):
        from clarity_backend.config import _should_read_env_file

        result = _should_read_env_file()
        assert result == ".env"


def test_settings_defaults():
    """Settings should have sensible defaults for all fields."""
    with patch.dict(os.environ, {"DOTENV_CONFIG": "1"}, clear=False):
        import importlib
        import clarity_backend.config as config_mod

        importlib.reload(config_mod)
        s = config_mod.Settings()

    assert s.DATABASE_URL == "sqlite+aiosqlite:///./clarity.db"
    assert s.CORS_ORIGINS == '["*"]'
    assert s.cors_origins_list == ["*"]
    assert s.GOOGLE_CLIENT_ID == ""
    assert s.PLANE_API_KEY == ""
    assert s.GOOGLE_REDIRECT_URI == "http://localhost:8070/auth/google/callback"


def test_settings_picks_up_env_vars():
    """Settings should read from env vars (the dotenvx path)."""
    test_env = {
        "DOTENV_CONFIG": "1",
        "GOOGLE_CLIENT_ID": "test-id-123",
        "CORS_ORIGINS": '["http://localhost:3070"]',
        "PLANE_API_KEY": "plane-key-test",
    }
    with patch.dict(os.environ, test_env, clear=False):
        import importlib
        import clarity_backend.config as config_mod

        importlib.reload(config_mod)
        s = config_mod.Settings()

    assert s.GOOGLE_CLIENT_ID == "test-id-123"
    assert s.cors_origins_list == ["http://localhost:3070"]
    assert s.PLANE_API_KEY == "plane-key-test"


def test_cors_origins_json_parsing():
    """CORS_ORIGINS must accept a JSON array string from env."""
    test_env = {
        "DOTENV_CONFIG": "1",
        "CORS_ORIGINS": '["http://localhost:3070","http://localhost:3080"]',
    }
    with patch.dict(os.environ, test_env, clear=False):
        import importlib
        import clarity_backend.config as config_mod

        importlib.reload(config_mod)
        s = config_mod.Settings()

    assert s.cors_origins_list == ["http://localhost:3070", "http://localhost:3080"]

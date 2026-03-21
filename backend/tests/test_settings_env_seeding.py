"""Tests for settings env seeding — verifies that config.py values
populate empty settings.json fields."""

from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def _clean_settings(tmp_path):
    """Override SETTINGS_FILE to a temp path so we don't touch real settings."""
    settings_file = tmp_path / "settings.json"
    with (
        patch("clarity_backend.settings.manager.SETTINGS_FILE", settings_file),
        patch("clarity_backend.settings.manager.SETTINGS_DIR", tmp_path),
    ):
        yield settings_file


def _make_mock_settings(**overrides):
    """Create a mock config.settings object with given attribute values."""
    defaults = {
        "PLANE_API_KEY": "",
        "PLANE_WORKSPACE_SLUG": "",
        "PLANE_PROJECT_ID": "",
        "OPENAI_API_KEY": "",
        "AIKIDO_WEBHOOK_SECRET": "",
        "POSTHOG_API_KEY": "",
        "POSTHOG_PROJECT_ID": "",
        "POSTHOG_HOST": "https://eu.posthog.com",
        "CLARITY_API_URL": "http://localhost:8000",
        "CLARITY_API_KEY": "",
        "CLARITY_WEBHOOK_SECRET": "",
        "OAUTH_REDIRECT_BASE": "http://localhost:3080",
    }
    defaults.update(overrides)
    mock = MagicMock()
    for key, value in defaults.items():
        setattr(mock, key, value)
    return mock


class TestEnvSeeding:
    """Test that _seed_from_env fills empty values from config.py."""

    def test_seeds_plane_api_key(self, _clean_settings):
        mock_settings = _make_mock_settings(PLANE_API_KEY="plane-key-from-env")
        with patch("clarity_backend.settings.manager.settings", mock_settings, create=True):
            with patch("clarity_backend.config.settings", mock_settings):
                from clarity_backend.settings.manager import _read_settings

                result = _read_settings()
        assert result["plane_api_key"] == "plane-key-from-env"

    def test_seeds_multiple_keys(self, _clean_settings):
        mock_settings = _make_mock_settings(
            POSTHOG_API_KEY="phk_test123",
            OPENAI_API_KEY="sk-test456",
        )
        with patch("clarity_backend.config.settings", mock_settings):
            from clarity_backend.settings.manager import _read_settings

            result = _read_settings()
        assert result["posthog_api_key"] == "phk_test123"
        assert result["openai_api_key"] == "sk-test456"

    def test_does_not_overwrite_saved_values(self, _clean_settings, tmp_path):
        import json

        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"plane_api_key": "user-saved-key"}))

        mock_settings = _make_mock_settings(PLANE_API_KEY="env-key-different")
        with patch("clarity_backend.config.settings", mock_settings):
            from clarity_backend.settings.manager import _read_settings

            result = _read_settings()
        # User-saved value should NOT be overwritten
        assert result["plane_api_key"] == "user-saved-key"

    def test_seeds_only_empty_strings(self, _clean_settings, tmp_path):
        import json

        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"posthog_api_key": "existing"}))

        mock_settings = _make_mock_settings(
            POSTHOG_API_KEY="env-posthog",
            CLARITY_API_KEY="env-clarity",
        )
        with patch("clarity_backend.config.settings", mock_settings):
            from clarity_backend.settings.manager import _read_settings

            result = _read_settings()
        # Existing value preserved
        assert result["posthog_api_key"] == "existing"
        # Empty value seeded from env
        assert result["clarity_api_key"] == "env-clarity"

    def test_graceful_when_config_unavailable(self, _clean_settings):
        with patch(
            "clarity_backend.settings.manager._seed_from_env",
            side_effect=lambda m: m,
        ):
            from clarity_backend.settings.manager import _read_settings

            result = _read_settings()
        # Should return defaults without crashing
        assert result["stt_backend"] == "web-speech"

    def test_voice_shortcut_has_default(self, _clean_settings):
        mock_settings = _make_mock_settings()
        with patch("clarity_backend.config.settings", mock_settings):
            from clarity_backend.settings.manager import _read_settings

            result = _read_settings()
        assert result["voice_shortcut"] == "Cmd+Shift+Space"

    def test_oauth_redirect_base_has_default(self, _clean_settings):
        mock_settings = _make_mock_settings()
        with patch("clarity_backend.config.settings", mock_settings):
            from clarity_backend.settings.manager import _read_settings

            result = _read_settings()
        assert result["oauth_redirect_base"] == "http://localhost:3080"

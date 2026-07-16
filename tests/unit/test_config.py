"""Tests for the 12-factor Settings object.

All tests construct ``Settings(_env_file=None)`` so they read only the
monkeypatched process environment and never touch the repository's real
``.env`` file.
"""

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


def test_defaults_match_the_original_hardcoded_values(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "real-key")
    settings = Settings(_env_file=None)

    assert settings.supervisor_model == "gemini-1.5-flash"
    assert settings.researcher_model == "gemini-1.5-flash"
    assert settings.writer_model == "gemini-1.5-pro"
    assert settings.writer_temperature == 0.7
    assert settings.search_max_results == 3
    assert settings.recursion_limit == 20
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000


def test_missing_api_key_fails_fast(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_placeholder_api_key_is_rejected(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "your_api_key_here")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_app_settings_are_overridable_via_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "real-key")
    monkeypatch.setenv("WRITER_TEMPERATURE", "0.1")
    monkeypatch.setenv("SEARCH_MAX_RESULTS", "1")
    monkeypatch.setenv("API_PORT", "9001")

    settings = Settings(_env_file=None)

    assert settings.writer_temperature == 0.1
    assert settings.search_max_results == 1
    assert settings.api_port == 9001


def test_secret_key_is_masked_but_retrievable(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "super-secret-value")
    settings = Settings(_env_file=None)

    assert "super-secret-value" not in repr(settings)
    assert settings.google_api_key.get_secret_value() == "super-secret-value"


def test_get_settings_is_cached(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "real-key")
    get_settings.cache_clear()

    assert get_settings() is get_settings()

    get_settings.cache_clear()

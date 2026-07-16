"""Tests for logging configuration."""

import logging

from app.logging_config import configure_logging


def test_configure_logging_sets_level_and_single_handler(settings, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    from app.config import Settings

    configure_logging(Settings(_env_file=None))

    root = logging.getLogger()
    assert root.level == logging.DEBUG
    # Idempotent: configuring again does not stack duplicate handlers.
    handler_count = len(root.handlers)
    configure_logging(Settings(_env_file=None))
    assert len(root.handlers) == handler_count

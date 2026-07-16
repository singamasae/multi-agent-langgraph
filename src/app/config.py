"""Application configuration (12-factor: all config lives in the environment).

A single :class:`Settings` object holds every tunable that used to be hardcoded
across the codebase (model names, temperatures, search width, recursion limit,
API host/port, logging). The secret ``GOOGLE_API_KEY`` is read from its
conventional unprefixed name; every other setting is namespaced under ``AAAS_``.

Factories never call :func:`get_settings` themselves — the composition root and
the interface entry points read settings once and pass concrete values down,
keeping the domain pure and the whole graph testable without the environment.
"""

import functools

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The literal shipped in ``.env.example``; treated as "unset" so a user who
# forgot to fill it in gets a clear failure instead of a confusing API error.
PLACEHOLDER_API_KEY = "your_api_key_here"


class Settings(BaseSettings):
    """Typed, validated, environment-driven configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Every field maps to its uppercased name in the environment, e.g.
    # writer_model -> WRITER_MODEL, log_level -> LOG_LEVEL.
    google_api_key: SecretStr = Field(
        validation_alias=AliasChoices("GOOGLE_API_KEY"),
    )

    # Per-role model selection.
    supervisor_model: str = "gemini-1.5-flash"
    researcher_model: str = "gemini-1.5-flash"
    writer_model: str = "gemini-1.5-pro"

    # Per-role sampling temperature.
    supervisor_temperature: float = 0.0
    researcher_temperature: float = 0.0
    writer_temperature: float = 0.7

    # Researcher search width.
    search_max_results: int = 3

    # Safety bound on the supervisor/worker loop.
    recursion_limit: int = 20

    # HTTP server bind address.
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Logging.
    log_level: str = "INFO"
    log_format: str = "text"  # "text" for local dev, "json" for structured logs.

    @field_validator("google_api_key")
    @classmethod
    def _reject_missing_or_placeholder_key(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value().strip()
        if not raw or raw == PLACEHOLDER_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY is not set. Provide a real Gemini API key in the "
                "environment or the .env file (see .env.example)."
            )
        return value


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide Settings, constructed once and cached.

    Call ``get_settings.cache_clear()`` in tests that need a fresh read.
    """
    return Settings()

"""Application configuration (12-factor: all config lives in the environment).

A single :class:`Settings` object holds every tunable that used to be hardcoded
across the codebase (per-role provider + model, temperatures, search width,
recursion limit, API host/port, logging). Each role can target Google Gemini or
OpenAI; the secrets ``GOOGLE_API_KEY`` / ``OPENAI_API_KEY`` are read from their
conventional unprefixed names, and a provider's key is only required when a role
actually uses it. Every other field maps to its uppercased name.

Factories never call :func:`get_settings` themselves — the composition root and
the interface entry points read settings once and pass concrete values down,
keeping the domain pure and the whole graph testable without the environment.
"""

import functools

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The literals shipped in ``.env.example``; treated as "unset" so a user who
# forgot to fill one in gets a clear failure instead of a confusing API error.
PLACEHOLDER_API_KEY = "your_api_key_here"
PLACEHOLDER_OPENAI_API_KEY = "your_openai_api_key_here"
_PLACEHOLDERS = {PLACEHOLDER_API_KEY, PLACEHOLDER_OPENAI_API_KEY}

# Providers a role may target. Each maps to a concrete client in ``llm.py``.
VALID_PROVIDERS = {"google", "openai"}


def _key_is_unset(secret: "SecretStr | None") -> bool:
    """True if a key is missing, blank, or still an ``.env.example`` placeholder."""
    if secret is None:
        return True
    raw = secret.get_secret_value().strip()
    return not raw or raw in _PLACEHOLDERS


class Settings(BaseSettings):
    """Typed, validated, environment-driven configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Provider API keys. Each is optional here and only *required* (fail-fast)
    # if a role actually targets that provider — see ``_validate_keys_in_use``.
    # Every field maps to its uppercased name in the environment, e.g.
    # writer_model -> WRITER_MODEL, log_level -> LOG_LEVEL.
    google_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_API_KEY"),
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY"),
    )
    # Optional override for OpenAI-compatible endpoints (Azure, local, proxies).
    openai_base_url: str | None = None

    # Per-role provider selection ("google" or "openai"). Defaults to Gemini
    # everywhere so existing deployments keep working unchanged.
    supervisor_provider: str = "google"
    researcher_provider: str = "google"
    writer_provider: str = "google"

    # Per-role model selection. Defaults are Gemini; when a role's provider is
    # "openai", set the matching *_MODEL to an OpenAI model (e.g. gpt-4o-mini).
    supervisor_model: str = "gemini-flash-lite-latest"
    researcher_model: str = "gemini-flash-lite-latest"
    writer_model: str = "gemini-flash-lite-latest"

    # Per-role sampling temperature.
    supervisor_temperature: float = 0.0
    researcher_temperature: float = 0.0
    writer_temperature: float = 0.7

    # Gemini "thinking" budget (tokens). 0 disables thinking so the model
    # returns a normal text answer; thinking-enabled models (e.g. *-flash-lite)
    # can otherwise return reasoning-only content with no answer text. Use -1
    # for the model's dynamic default if you want thinking on.
    thinking_budget: int = 0

    # Researcher search width.
    search_max_results: int = 3

    # Safety bound on the supervisor/worker loop.
    recursion_limit: int = 50

    # Directory the CLI writes -o/--output Markdown files into. Only the
    # basename of the -o value is used; the file always lands here.
    output_dir: str = "download"

    # HTTP server bind address.
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Comma-separated browser origins allowed to call the API cross-origin
    # (CORS). Empty (default) disables the CORS middleware — fine when the
    # front-end is served same-origin (e.g. the built-in /ui demo). Set e.g.
    # "http://localhost:3000" when a separate front-end origin calls the API.
    cors_allow_origins: str = ""

    # Logging.
    log_level: str = "INFO"
    log_format: str = "text"  # "text" for local dev, "json" for structured logs.

    @property
    def cors_origins_list(self) -> list[str]:
        """`cors_allow_origins` split into a clean list (empty when unset)."""
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _validate_providers(self) -> "Settings":
        """Reject unknown providers and fail fast on a missing key in use.

        A provider's API key is only required when at least one role targets
        that provider, so a Gemini-only or OpenAI-only deployment need not
        supply the other's key.
        """
        role_providers = {
            "SUPERVISOR_PROVIDER": self.supervisor_provider,
            "RESEARCHER_PROVIDER": self.researcher_provider,
            "WRITER_PROVIDER": self.writer_provider,
        }
        for name, provider in role_providers.items():
            if provider not in VALID_PROVIDERS:
                raise ValueError(
                    f"{name}={provider!r} is invalid; expected one of "
                    f"{sorted(VALID_PROVIDERS)}."
                )

        providers_in_use = set(role_providers.values())
        if "google" in providers_in_use and _key_is_unset(self.google_api_key):
            raise ValueError(
                "GOOGLE_API_KEY is not set. Provide a real Gemini API key in the "
                "environment or the .env file (see .env.example)."
            )
        if "openai" in providers_in_use and _key_is_unset(self.openai_api_key):
            raise ValueError(
                "OPENAI_API_KEY is not set but a role targets the 'openai' "
                "provider. Provide a real OpenAI API key (see .env.example)."
            )
        return self


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide Settings, constructed once and cached.

    Call ``get_settings.cache_clear()`` in tests that need a fresh read.
    """
    return Settings()

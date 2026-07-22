"""Chat-model factory — the single place a provider client is constructed.

Keeping construction here means every agent receives an already-built model by
injection, so nothing downstream depends on ``ChatGoogleGenerativeAI`` or
``ChatOpenAI`` directly and the graph is testable with fakes. Each role picks
its provider ("google" or "openai") via Settings, so the roster can mix Gemini
and OpenAI models freely.
"""

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from .config import Settings

# Maps a role to the (provider, model, temperature) Settings attributes it uses.
_ROLE_TO_SETTINGS = {
    "supervisor": ("supervisor_provider", "supervisor_model", "supervisor_temperature"),
    "researcher": ("researcher_provider", "researcher_model", "researcher_temperature"),
    "writer": ("writer_provider", "writer_model", "writer_temperature"),
}


def build_chat_model(role: str, settings: Settings) -> BaseChatModel:
    """Build the chat model configured for ``role``.

    The provider (``google`` or ``openai``) and model name come from the
    role's ``*_provider`` / ``*_model`` Settings fields.

    Args:
        role: One of ``"supervisor"``, ``"researcher"``, ``"writer"``.
        settings: Application settings supplying provider, model and temperature.

    Raises:
        ValueError: If ``role`` is not a known agent role.
    """
    try:
        provider_attr, model_attr, temperature_attr = _ROLE_TO_SETTINGS[role]
    except KeyError:
        raise ValueError(
            f"Unknown LLM role {role!r}; expected one of {sorted(_ROLE_TO_SETTINGS)}."
        ) from None

    provider = getattr(settings, provider_attr)
    model = getattr(settings, model_attr)
    temperature = getattr(settings, temperature_attr)

    if provider == "google":
        # Settings validation guarantees the key is set when a role is google;
        # guard anyway so the type is narrowed and misuse fails loudly.
        if settings.google_api_key is None:
            raise ValueError("GOOGLE_API_KEY is required for a 'google' role.")
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=settings.google_api_key.get_secret_value(),
            # Disable "thinking" by default so the model emits answer text rather
            # than reasoning-only content (see Settings.thinking_budget).
            thinking_budget=settings.thinking_budget,
        )

    if provider == "openai":
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            # Pass the SecretStr straight through so it stays masked in reprs;
            # Settings validation guarantees it is set when this role is openai.
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

    # Settings validation should have rejected any other provider already.
    raise ValueError(
        f"Unsupported provider {provider!r} for role {role!r}; "
        "expected 'google' or 'openai'."
    )

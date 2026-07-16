"""Chat-model factory — the single place a Gemini client is constructed.

Keeping construction here means every agent receives an already-built model by
injection, so nothing downstream depends on ``ChatGoogleGenerativeAI`` directly
and the graph is testable with fakes.
"""

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from .config import Settings

# Maps a role to the (model, temperature) Settings attributes it should use.
_ROLE_TO_SETTINGS = {
    "supervisor": ("supervisor_model", "supervisor_temperature"),
    "researcher": ("researcher_model", "researcher_temperature"),
    "writer": ("writer_model", "writer_temperature"),
}


def build_chat_model(role: str, settings: Settings) -> BaseChatModel:
    """Build the Gemini chat model configured for ``role``.

    Args:
        role: One of ``"supervisor"``, ``"researcher"``, ``"writer"``.
        settings: Application settings supplying model names and temperatures.

    Raises:
        ValueError: If ``role`` is not a known agent role.
    """
    try:
        model_attr, temperature_attr = _ROLE_TO_SETTINGS[role]
    except KeyError:
        raise ValueError(
            f"Unknown LLM role {role!r}; expected one of {sorted(_ROLE_TO_SETTINGS)}."
        ) from None

    return ChatGoogleGenerativeAI(
        model=getattr(settings, model_attr),
        temperature=getattr(settings, temperature_attr),
        google_api_key=settings.google_api_key.get_secret_value(),
    )

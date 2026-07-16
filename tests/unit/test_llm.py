"""Tests for the chat-model factory (no real Gemini client is constructed)."""

import pytest

from app.llm import build_chat_model


@pytest.mark.parametrize(
    "role, expected_model_attr, expected_temp_attr",
    [
        ("supervisor", "supervisor_model", "supervisor_temperature"),
        ("researcher", "researcher_model", "researcher_temperature"),
        ("writer", "writer_model", "writer_temperature"),
    ],
)
def test_build_chat_model_maps_role_to_settings(
    mocker, settings, role, expected_model_attr, expected_temp_attr
):
    fake_ctor = mocker.patch("app.llm.ChatGoogleGenerativeAI")

    build_chat_model(role, settings)

    _, kwargs = fake_ctor.call_args
    assert kwargs["model"] == getattr(settings, expected_model_attr)
    assert kwargs["temperature"] == getattr(settings, expected_temp_attr)
    # The secret is unwrapped exactly once, at construction.
    assert kwargs["google_api_key"] == settings.google_api_key.get_secret_value()
    # Thinking budget is threaded through so answers aren't reasoning-only.
    assert kwargs["thinking_budget"] == settings.thinking_budget


def test_build_chat_model_rejects_unknown_role(mocker, settings):
    mocker.patch("app.llm.ChatGoogleGenerativeAI")
    with pytest.raises(ValueError, match="Unknown LLM role"):
        build_chat_model("nonexistent", settings)

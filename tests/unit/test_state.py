"""Tests for the AgentState message reducer."""

import typing

from langchain_core.messages import AIMessage, HumanMessage

from app.state import AgentState


def test_messages_reducer_appends_rather_than_replaces():
    # The reducer is carried in the Annotated metadata of the `messages` field.
    hints = typing.get_type_hints(AgentState, include_extras=True)
    reducer = hints["messages"].__metadata__[0]

    existing = [HumanMessage(content="question")]
    incoming = [AIMessage(content="answer")]

    combined = reducer(existing, incoming)

    assert [message.content for message in combined] == ["question", "answer"]

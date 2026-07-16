"""Tests for the supervisor node and its routing schema."""

from typing import get_args

from langchain_core.messages import AIMessage

from app.agents.supervisor import RouteResponse, make_supervisor_node
from app.constants import ROUTE_OPTIONS
from tests.fakes import ScriptedSupervisor


def test_supervisor_node_returns_next_and_adds_no_messages():
    node = make_supervisor_node(ScriptedSupervisor(["Researcher"]))

    result = node({"messages": [], "next": ""})

    assert result == {"next": "Researcher"}
    assert "messages" not in result


def test_premature_finish_is_redirected_to_writer():
    # LLM says FINISH but the Writer has not produced the final answer yet.
    node = make_supervisor_node(ScriptedSupervisor(["FINISH"]))

    result = node(
        {"messages": [AIMessage(content="facts", name="Researcher")], "next": ""}
    )

    assert result == {"next": "Writer"}


def test_finish_is_allowed_once_the_writer_has_answered():
    node = make_supervisor_node(ScriptedSupervisor(["FINISH"]))

    result = node(
        {"messages": [AIMessage(content="final answer", name="Writer")], "next": ""}
    )

    assert result == {"next": "FINISH"}


def test_route_response_literal_matches_roster():
    # Guards the third copy of the roster: the structured-output Literal must
    # agree with the constants-derived ROUTE_OPTIONS.
    literal_values = list(get_args(RouteResponse.model_fields["next"].annotation))
    assert literal_values == ROUTE_OPTIONS

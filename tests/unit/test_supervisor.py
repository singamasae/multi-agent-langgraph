"""Tests for the supervisor node and its routing schema."""

from typing import get_args

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.supervisor import RouteResponse, make_supervisor_node
from app.constants import ROUTE_OPTIONS
from tests.fakes import ScriptedSupervisor


def test_supervisor_node_returns_next_and_adds_no_messages():
    node = make_supervisor_node(ScriptedSupervisor(["Researcher"]))

    result = node({"messages": [], "next": ""})

    assert result == {"next": "Researcher"}
    assert "messages" not in result


def test_research_is_forced_first_regardless_of_llm_choice():
    # No research yet: even if the LLM jumps to Writer/FINISH, route to Researcher
    # so the Writer never runs on an empty context.
    for llm_choice in ("Writer", "FINISH"):
        node = make_supervisor_node(ScriptedSupervisor([llm_choice]))
        result = node({"messages": [HumanMessage(content="q", name="User")], "next": ""})
        assert result == {"next": "Researcher"}


def test_premature_finish_is_redirected_to_writer():
    # Research done, but LLM says FINISH before the Writer produced the answer.
    node = make_supervisor_node(ScriptedSupervisor(["FINISH"]))

    result = node(
        {"messages": [AIMessage(content="facts", name="Researcher")], "next": ""}
    )

    assert result == {"next": "Writer"}


def test_finish_is_allowed_after_research_and_writing():
    node = make_supervisor_node(ScriptedSupervisor(["FINISH"]))

    result = node(
        {
            "messages": [
                AIMessage(content="facts", name="Researcher"),
                AIMessage(content="final answer", name="Writer"),
            ],
            "next": "",
        }
    )

    assert result == {"next": "FINISH"}


def test_route_response_literal_matches_roster():
    # Guards the third copy of the roster: the structured-output Literal must
    # agree with the constants-derived ROUTE_OPTIONS.
    literal_values = list(get_args(RouteResponse.model_fields["next"].annotation))
    assert literal_values == ROUTE_OPTIONS

"""Tests for the supervisor node and its routing schema."""

from typing import get_args

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.supervisor import RouteResponse, make_supervisor_node
from app.constants import DEFAULT_RESEARCHER, ROUTE_OPTIONS
from tests.fakes import ScriptedSupervisor


def test_supervisor_node_returns_next_and_adds_no_messages():
    node = make_supervisor_node(ScriptedSupervisor(["ScienceResearcher"]))

    result = node({"messages": [], "next": ""})

    assert result == {"next": "ScienceResearcher"}
    assert "messages" not in result


def test_specialist_choice_is_honoured_when_no_research_yet():
    # No research yet, but the router picked a specialist: honour the topic.
    node = make_supervisor_node(ScriptedSupervisor(["TechnologyResearcher"]))
    result = node(
        {"messages": [HumanMessage(content="q", name="User")], "next": ""}
    )
    assert result == {"next": "TechnologyResearcher"}


def test_skipping_research_falls_back_to_default_specialist():
    # No research yet: if the router jumps to Writer/FINISH, force the default
    # specialist so the Writer never runs on an empty context.
    for llm_choice in ("Writer", "FINISH"):
        node = make_supervisor_node(ScriptedSupervisor([llm_choice]))
        result = node({"messages": [HumanMessage(content="q", name="User")], "next": ""})
        assert result == {"next": DEFAULT_RESEARCHER}


def test_premature_finish_is_redirected_to_writer():
    # Research done, but LLM says FINISH before the Writer produced the answer.
    node = make_supervisor_node(ScriptedSupervisor(["FINISH"]))

    result = node(
        {"messages": [AIMessage(content="facts", name="ScienceResearcher")], "next": ""}
    )

    assert result == {"next": "Writer"}


def test_finish_is_allowed_after_research_and_writing():
    node = make_supervisor_node(ScriptedSupervisor(["FINISH"]))

    result = node(
        {
            "messages": [
                AIMessage(content="facts", name="ScienceResearcher"),
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

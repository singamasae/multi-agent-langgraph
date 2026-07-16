"""Tests for the agent-roster single source of truth."""

from app.constants import FINISH, MEMBERS, ROUTE_OPTIONS, AgentName


def test_members_are_derived_from_the_enum():
    # MEMBERS must stay in lock-step with the AgentName enum so the roster
    # has exactly one source of truth.
    assert MEMBERS == [member.value for member in AgentName]
    assert MEMBERS == ["Researcher", "Writer"]


def test_route_options_prepend_finish_to_members():
    assert ROUTE_OPTIONS == [FINISH, *MEMBERS]
    assert ROUTE_OPTIONS == ["FINISH", "Researcher", "Writer"]


def test_agent_name_behaves_as_a_string():
    # Because AgentName subclasses str, values compare/serialize as plain
    # strings, which is what LangGraph node keys and message names expect.
    assert AgentName.RESEARCHER == "Researcher"
    assert f"{AgentName.WRITER}" == "Writer" or AgentName.WRITER.value == "Writer"

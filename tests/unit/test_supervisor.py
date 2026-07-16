"""Tests for the supervisor node and its routing schema."""

from typing import get_args

from app.agents.supervisor import RouteResponse, make_supervisor_node
from app.constants import ROUTE_OPTIONS
from tests.fakes import ScriptedSupervisor


def test_supervisor_node_returns_next_and_adds_no_messages():
    node = make_supervisor_node(ScriptedSupervisor(["Researcher"]))

    result = node({"messages": [], "next": ""})

    assert result == {"next": "Researcher"}
    assert "messages" not in result


def test_route_response_literal_matches_roster():
    # Guards the third copy of the roster: the structured-output Literal must
    # agree with the constants-derived ROUTE_OPTIONS.
    literal_values = list(get_args(RouteResponse.model_fields["next"].annotation))
    assert literal_values == ROUTE_OPTIONS

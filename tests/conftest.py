"""Shared pytest fixtures."""

import pytest

from tests.fakes import FakeReactAgent, FakeWriterAgent, ScriptedSupervisor


@pytest.fixture
def settings(monkeypatch):
    """A hermetic Settings instance backed only by monkeypatched env vars.

    Uses a small recursion limit so loop-termination tests stay fast.
    """
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("RECURSION_LIMIT", "8")
    from app.config import Settings

    return Settings(_env_file=None)


@pytest.fixture
def fake_deps():
    """Factory building GraphDependencies wired entirely from test doubles.

    Call with a routing script and canned agent outputs to drive an exact path
    through the compiled graph without any real model or network access.
    """
    from app.constants import RESEARCHER_MEMBERS
    from app.graph.dependencies import GraphDependencies

    def _build(
        route_sequence=("ScienceResearcher", "Writer", "FINISH"),
        researcher_messages=None,
        writer_content="Final written answer.",
    ) -> GraphDependencies:
        from langchain_core.messages import AIMessage

        if researcher_messages is None:
            researcher_messages = [
                AIMessage(content="intermediate tool chatter"),
                AIMessage(content="- fact one\n- fact two"),
            ]
        # Every topic specialist gets its own fake ReAct agent; they all return
        # the same canned research so tests can drive an exact routing path.
        researchers = {
            name: FakeReactAgent(researcher_messages) for name in RESEARCHER_MEMBERS
        }
        return GraphDependencies(
            supervisor=ScriptedSupervisor(route_sequence),
            researchers=researchers,
            writer_agent=FakeWriterAgent(writer_content),
        )

    return _build

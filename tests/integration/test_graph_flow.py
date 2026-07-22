"""End-to-end flow through the compiled graph, driven entirely by fakes."""

import pytest
from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError

from app.graph.builder import build_graph


def test_full_route_researcher_then_writer_then_finish(fake_deps):
    graph = build_graph(
        fake_deps(
            route_sequence=("TechnologyResearcher", "Writer", "FINISH"),
            writer_content="# Final answer",
        )
    )

    final_state = graph.invoke(
        {"messages": [HumanMessage(content="research question")], "next": ""},
        {"recursion_limit": 8},
    )

    names = [getattr(m, "name", None) for m in final_state["messages"]]
    # The human prompt, then a specialist message, then the Writer's answer.
    assert "TechnologyResearcher" in names
    assert names[-1] == "Writer"
    assert final_state["messages"][-1].content == "# Final answer"


def test_supervisor_that_never_finishes_trips_the_recursion_cap(fake_deps):
    graph = build_graph(fake_deps(route_sequence=("ScienceResearcher",) * 100))

    with pytest.raises(GraphRecursionError):
        graph.invoke(
            {"messages": [HumanMessage(content="loop")], "next": ""},
            {"recursion_limit": 6},
        )

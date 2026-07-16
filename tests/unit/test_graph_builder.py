"""Tests for dependency assembly and graph topology."""

from app.graph.builder import SUPERVISOR, build_graph
from app.graph.dependencies import build_dependencies


def test_build_dependencies_wires_every_part(mocker, settings):
    # Patch the leaf builders so no real model/tool is constructed; assert the
    # composition root reads settings per role and packs the results.
    mocker.patch(
        "app.graph.dependencies.build_chat_model",
        side_effect=lambda role, _settings: f"llm:{role}",
    )
    mocker.patch("app.graph.dependencies.build_search_tool", return_value="search")
    mocker.patch("app.graph.dependencies.build_supervisor_runnable", return_value="SUP")
    mocker.patch("app.graph.dependencies.build_researcher_agent", return_value="RES")
    mocker.patch("app.graph.dependencies.build_writer_agent", return_value="WRI")

    deps = build_dependencies(settings)

    assert (deps.supervisor, deps.researcher_agent, deps.writer_agent) == (
        "SUP",
        "RES",
        "WRI",
    )


def test_graph_topology(fake_deps):
    graph = build_graph(fake_deps()).get_graph()

    node_ids = set(graph.nodes.keys())
    assert {SUPERVISOR, "Researcher", "Writer"} <= node_ids

    edges = {(edge.source, edge.target) for edge in graph.edges}
    # Workers return to the supervisor.
    assert ("Researcher", SUPERVISOR) in edges
    assert ("Writer", SUPERVISOR) in edges
    # Entry point and the two conditional routes to workers + END.
    assert ("__start__", SUPERVISOR) in edges
    assert (SUPERVISOR, "Researcher") in edges
    assert (SUPERVISOR, "Writer") in edges
    assert (SUPERVISOR, "__end__") in edges

"""Tests for dependency assembly and graph topology."""

from app.constants import RESEARCHER_MEMBERS
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
    mocker.patch(
        "app.graph.dependencies.build_researcher_agent",
        side_effect=lambda _llm, _tools, prompt: f"RES:{prompt[:20]}",
    )
    mocker.patch("app.graph.dependencies.build_writer_agent", return_value="WRI")

    deps = build_dependencies(settings)

    assert deps.supervisor == "SUP"
    assert deps.writer_agent == "WRI"
    # One specialist agent per topic in the roster.
    assert set(deps.researchers) == set(RESEARCHER_MEMBERS)
    assert all(str(agent).startswith("RES:") for agent in deps.researchers.values())


def test_graph_topology(fake_deps):
    graph = build_graph(fake_deps()).get_graph()

    node_ids = set(graph.nodes.keys())
    assert {SUPERVISOR, "Writer", *RESEARCHER_MEMBERS} <= node_ids

    edges = {(edge.source, edge.target) for edge in graph.edges}
    # Entry point and the Writer's return + conditional routes.
    assert ("__start__", SUPERVISOR) in edges
    assert ("Writer", SUPERVISOR) in edges
    assert (SUPERVISOR, "Writer") in edges
    assert (SUPERVISOR, "__end__") in edges
    # Every specialist returns to the supervisor and is a conditional target.
    for name in RESEARCHER_MEMBERS:
        assert (name, SUPERVISOR) in edges
        assert (SUPERVISOR, name) in edges

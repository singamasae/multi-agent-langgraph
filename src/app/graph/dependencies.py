"""Composition root: turn Settings into the concrete runnables the graph needs.

This is the single place that wires real models, tools, and agents together.
``build_graph`` consumes a :class:`GraphDependencies`, so tests can hand it a
bag of fakes instead — nothing else in the graph knows how deps were built.
"""

from dataclasses import dataclass

from langchain_core.runnables import Runnable

from ..agents.researcher import build_researcher_agent
from ..agents.supervisor import build_supervisor_runnable
from ..agents.writer import build_writer_agent
from ..config import Settings
from ..llm import build_chat_model
from ..tools.search import build_search_tool


@dataclass
class GraphDependencies:
    """The runnables the graph nodes delegate to."""

    supervisor: Runnable
    researcher_agent: Runnable
    writer_agent: Runnable


def build_dependencies(settings: Settings) -> GraphDependencies:
    """Construct every agent/tool once from ``settings``."""
    supervisor_llm = build_chat_model("supervisor", settings)
    researcher_llm = build_chat_model("researcher", settings)
    writer_llm = build_chat_model("writer", settings)
    search_tool = build_search_tool(settings)

    return GraphDependencies(
        supervisor=build_supervisor_runnable(supervisor_llm),
        researcher_agent=build_researcher_agent(researcher_llm, [search_tool]),
        writer_agent=build_writer_agent(writer_llm),
    )

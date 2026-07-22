"""Composition root: turn Settings into the concrete runnables the graph needs.

This is the single place that wires real models, tools, and agents together.
``build_graph`` consumes a :class:`GraphDependencies`, so tests can hand it a
bag of fakes instead — nothing else in the graph knows how deps were built.
"""

from dataclasses import dataclass

from langchain_core.runnables import Runnable

from ..agents.researcher import build_researcher_agent, build_topic_system_prompt
from ..agents.supervisor import build_supervisor_runnable
from ..agents.writer import build_writer_agent
from ..config import Settings
from ..constants import RESEARCH_TOPICS
from ..llm import build_chat_model
from ..tools.search import build_search_tool


@dataclass
class GraphDependencies:
    """The runnables the graph nodes delegate to.

    ``researchers`` maps each topic specialist's name (an
    :class:`~app.constants.AgentName` value) to its ReAct agent.
    """

    supervisor: Runnable
    researchers: dict[str, Runnable]
    writer_agent: Runnable


def build_dependencies(settings: Settings) -> GraphDependencies:
    """Construct every agent/tool once from ``settings``.

    All topic specialists share one researcher model and one search tool (they
    differ only by their topic-focused prompt), so a single ``RESEARCHER_*``
    configuration drives the whole research roster.
    """
    supervisor_llm = build_chat_model("supervisor", settings)
    researcher_llm = build_chat_model("researcher", settings)
    writer_llm = build_chat_model("writer", settings)
    search_tool = build_search_tool(settings)

    researchers = {
        name: build_researcher_agent(
            researcher_llm,
            [search_tool],
            prompt=build_topic_system_prompt(topic),
        )
        for name, topic in RESEARCH_TOPICS.items()
    }

    return GraphDependencies(
        supervisor=build_supervisor_runnable(supervisor_llm),
        researchers=researchers,
        writer_agent=build_writer_agent(writer_llm),
    )

"""Researcher agent: a ReAct agent with web search.

The roster is a set of *topic specialists* (see :data:`app.constants.RESEARCH_TOPICS`).
They share this one implementation and differ only by their system prompt: the
composition root builds one agent per topic, passing a topic-focused prompt from
:func:`build_topic_system_prompt`, and tags each node's output with the
specialist's name.
"""

import logging
from typing import Callable, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent

from ..state import AgentState

logger = logging.getLogger(__name__)

# Generic researcher instruction, kept as the default so a plain
# build_researcher_agent(llm, tools) call still works.
_SYSTEM_PROMPT = (
    "You are an expert researcher. Use the search tool to find the most "
    "up-to-date and relevant information regarding the user's query. Provide a "
    "clear, bulleted summary of facts found."
)


def build_topic_system_prompt(topic_description: str) -> str:
    """Build a topic-specialized researcher system prompt.

    ``topic_description`` is one of the focus strings from
    :data:`app.constants.RESEARCH_TOPICS`.
    """
    return (
        f"You are an expert researcher specializing in {topic_description}. "
        "Use the search tool to find the most up-to-date and relevant "
        "information regarding the user's query within your area of expertise. "
        "Provide a clear, bulleted summary of facts found."
    )


def build_researcher_agent(
    llm: BaseChatModel,
    tools: Sequence[BaseTool],
    *,
    prompt: str = _SYSTEM_PROMPT,
) -> Runnable:
    """Build a ReAct agent that can call the given tools.

    Pass ``prompt`` to specialize the agent for a topic (see
    :func:`build_topic_system_prompt`); it defaults to the generic researcher
    instruction. Uses the ``prompt`` argument (the current langgraph API; the
    old ``state_modifier`` name was removed).
    """
    return create_react_agent(llm, list(tools), prompt=prompt)


def make_researcher_node(agent: Runnable, name: str) -> Callable[[AgentState], dict]:
    """Adapt the ReAct agent into a node tagged with the specialist ``name``.

    Surfaces only the agent's *final* message, tagged with ``name`` (the
    specialist's :class:`~app.constants.AgentName` value), dropping the
    intermediate tool-call chatter from the shared history.
    """

    def researcher_node(state: AgentState) -> dict:
        logger.info("Researcher node running: name=%s", name)
        result = agent.invoke({"messages": state["messages"]})
        last_message = result["messages"][-1]

        text = str(last_message.text)
        finish_reason = (getattr(last_message, "response_metadata", {}) or {}).get(
            "finish_reason"
        )
        logger.debug(
            "Researcher %s output: finish_reason=%s, content=%r",
            name,
            finish_reason,
            last_message.content,
        )
        if not text.strip():
            logger.warning(
                "Researcher %s produced no text (finish_reason=%s). Raw content=%r",
                name,
                finish_reason,
                last_message.content,
            )

        return {"messages": [AIMessage(content=text, name=name)]}

    return researcher_node

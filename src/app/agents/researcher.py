"""Researcher agent: a ReAct agent with web search."""

import logging
from typing import Callable, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent

from ..constants import AgentName
from ..state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert researcher. Use the search tool to find the most "
    "up-to-date and relevant information regarding the user's query. Provide a "
    "clear, bulleted summary of facts found."
)


def build_researcher_agent(llm: BaseChatModel, tools: Sequence[BaseTool]) -> Runnable:
    """Build a ReAct agent that can call the given tools.

    Uses the ``prompt`` argument (the current langgraph API; the old
    ``state_modifier`` name was removed).
    """
    return create_react_agent(llm, list(tools), prompt=_SYSTEM_PROMPT)


def make_researcher_node(agent: Runnable) -> Callable[[AgentState], dict]:
    """Adapt the ReAct agent into a node.

    Surfaces only the agent's *final* message, tagged with the Researcher name,
    dropping the intermediate tool-call chatter from the shared history.
    """

    def researcher_node(state: AgentState) -> dict:
        logger.info("Researcher node running")
        result = agent.invoke({"messages": state["messages"]})
        last_message = result["messages"][-1]
        return {
            "messages": [
                AIMessage(content=last_message.content, name=AgentName.RESEARCHER.value)
            ]
        }

    return researcher_node

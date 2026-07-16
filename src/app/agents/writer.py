"""Writer agent: a toolless chain that synthesizes the final answer."""

import logging
from typing import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable

from ..constants import AgentName
from ..state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert technical writer. Write a comprehensive, well-structured, "
    "and engaging response based ONLY on the research provided by the Researcher. "
    "Do not add made-up facts or hallucinate. Format your output in clean Markdown. "
    "If there is no research provided, ask the Researcher to provide information."
)


def build_writer_agent(llm: BaseChatModel) -> Runnable:
    """Compose the writer prompt with ``llm`` (no tools)."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    return prompt | llm


def make_writer_node(agent: Runnable) -> Callable[[AgentState], dict]:
    """Adapt the writer chain into a node, tagging output with the Writer name."""

    def writer_node(state: AgentState) -> dict:
        logger.info("Writer node running")
        result = agent.invoke({"messages": state["messages"]})
        return {
            "messages": [AIMessage(content=result.content, name=AgentName.WRITER.value)]
        }

    return writer_node

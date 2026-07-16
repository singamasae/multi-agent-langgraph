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

# Trailing human turn. Without it the message history ends with the Researcher's
# AI message, and Gemini returns an empty completion (nothing to respond to).
_WRITE_INSTRUCTION = (
    "Using the research above, write the final comprehensive answer to the user's "
    "request now, formatted in clean Markdown."
)


def build_writer_agent(llm: BaseChatModel) -> Runnable:
    """Compose the writer prompt with ``llm`` (no tools)."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            ("human", _WRITE_INSTRUCTION),
        ]
    )
    return prompt | llm


def make_writer_node(agent: Runnable) -> Callable[[AgentState], dict]:
    """Adapt the writer chain into a node, tagging output with the Writer name."""

    def writer_node(state: AgentState) -> dict:
        logger.info("Writer node running")
        result = agent.invoke({"messages": state["messages"]})

        # Normalise to plain text (Gemini may return list/thinking content) and
        # surface *why* the answer is empty when it is.
        text = str(result.text)
        finish_reason = (getattr(result, "response_metadata", {}) or {}).get(
            "finish_reason"
        )
        logger.debug(
            "Writer output: finish_reason=%s, content=%r", finish_reason, result.content
        )
        if not text.strip():
            logger.warning(
                "Writer produced no text (finish_reason=%s). Raw content=%r. "
                "If MAX_TOKENS, raise the output limit; if SAFETY/RECITATION, the "
                "model blocked the response; otherwise try a different WRITER_MODEL.",
                finish_reason,
                result.content,
            )

        return {"messages": [AIMessage(content=text, name=AgentName.WRITER.value)]}

    return writer_node

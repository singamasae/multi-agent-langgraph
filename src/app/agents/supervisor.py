"""Supervisor agent: a lightweight LLM router over the worker roster."""

import logging
from typing import Callable, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from ..constants import FINISH, MEMBERS, ROUTE_OPTIONS, AgentName
from ..state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a supervisor coordinating these workers: {members}.\n"
    "- Researcher: searches the web and gathers factual information for the request.\n"
    "- Writer: composes the final, well-structured answer for the user from the "
    "research gathered so far.\n\n"
    "Follow this workflow: first route to the Researcher to gather information, then "
    "route to the Writer to compose the final answer. The Writer must always produce "
    "the final answer before the task is complete. Respond with the single worker to "
    "act next, or FINISH only after the Writer has delivered the final answer."
)

_ROUTING_QUESTION = (
    "Given the conversation above, who should act next? "
    "Or should we FINISH? Select one of: {options}"
)


class RouteResponse(BaseModel):
    """Structured routing decision the supervisor is forced to return.

    The Literal is kept in sync with the AgentName roster by
    test_supervisor.test_route_response_literal_matches_roster.
    """

    next: Literal["FINISH", "Researcher", "Writer"]


def build_supervisor_runnable(llm: BaseChatModel) -> Runnable:
    """Compose the routing prompt with structured-output routing over ``llm``."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            ("system", _ROUTING_QUESTION),
        ]
    ).partial(options=str(ROUTE_OPTIONS), members=", ".join(MEMBERS))

    return prompt | llm.with_structured_output(RouteResponse)


def _has_message_from(state: AgentState, agent_name: str) -> bool:
    """True if ``agent_name`` has already produced a message in the history."""
    return any(
        getattr(message, "name", None) == agent_name for message in state["messages"]
    )


def make_supervisor_node(supervisor: Runnable) -> Callable[[AgentState], dict]:
    """Adapt the supervisor runnable into a LangGraph node.

    Writes only ``next`` — the supervisor never adds messages to the history.

    A lightweight LLM router cannot be trusted to follow the pipeline, so this
    enforces it deterministically: gather research first, then compose the
    answer, and only FINISH after the Writer has delivered it. The router still
    controls when to loop back for more research.
    """

    def supervisor_node(state: AgentState) -> dict:
        decision = supervisor.invoke(state)
        next_node = decision.next

        has_research = _has_message_from(state, AgentName.RESEARCHER.value)
        has_answer = _has_message_from(state, AgentName.WRITER.value)

        if not has_research:
            # Nothing to write from yet — research must happen first.
            if next_node != AgentName.RESEARCHER.value:
                logger.info("No research yet; overriding %s -> Researcher", next_node)
            next_node = AgentName.RESEARCHER.value
        elif next_node == FINISH and not has_answer:
            logger.info("Supervisor chose FINISH before the Writer ran; routing to Writer")
            next_node = AgentName.WRITER.value

        logger.info("Supervisor routing decision: next=%s", next_node)
        return {"next": next_node}

    return supervisor_node

"""Supervisor agent: a lightweight LLM router over the worker roster."""

import logging
from typing import Callable, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from ..constants import MEMBERS, ROUTE_OPTIONS
from ..state import AgentState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a supervisor tasked with managing a conversation between the"
    " following workers: {members}. Given the following user request,"
    " respond with the worker to act next. Each worker will perform a"
    " task and respond with their results and status. When finished,"
    " respond with FINISH."
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


def make_supervisor_node(supervisor: Runnable) -> Callable[[AgentState], dict]:
    """Adapt the supervisor runnable into a LangGraph node.

    Writes only ``next`` — the supervisor never adds messages to the history.
    """

    def supervisor_node(state: AgentState) -> dict:
        decision = supervisor.invoke(state)
        logger.info("Supervisor routing decision: next=%s", decision.next)
        return {"next": decision.next}

    return supervisor_node

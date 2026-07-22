"""Supervisor agent: a lightweight LLM router over the worker roster.

The researcher roster is a set of topic specialists (see
:data:`app.constants.RESEARCH_TOPICS`). The supervisor's job is to analyse the
request and route to the best-fit specialist(s) before the Writer composes the
answer.
"""

import logging
from typing import Callable, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from ..constants import (
    DEFAULT_RESEARCHER,
    FINISH,
    MEMBERS,
    RESEARCH_TOPICS,
    RESEARCHER_MEMBERS,
    ROUTE_OPTIONS,
    AgentName,
)
from ..state import AgentState

logger = logging.getLogger(__name__)

# One "- Name: focus" line per topic specialist, generated from the registry so
# the routing prompt always matches the roster.
_SPECIALIST_LINES = "\n".join(
    f"- {name}: researches {topic}." for name, topic in RESEARCH_TOPICS.items()
)

_SYSTEM_PROMPT = (
    "You are a supervisor coordinating a team of topic-specialist researchers and "
    "a writer: {members}.\n\n"
    "Research specialists (route to the one whose expertise best fits the "
    "request):\n"
    f"{_SPECIALIST_LINES}\n"
    "- Writer: composes the final, well-structured answer for the user from the "
    "research gathered so far.\n\n"
    "Analyse the user's request and route to the single most relevant specialist "
    "first. For a request that spans several fields, consult the additional "
    "relevant specialists one at a time before writing. Once enough research has "
    "been gathered, route to the Writer to compose the final answer. The Writer "
    "must always produce the final answer before the task is complete. Respond "
    "with the single worker to act next, or FINISH only after the Writer has "
    "delivered the final answer."
)

_ROUTING_QUESTION = (
    "Given the conversation above, who should act next? "
    "Or should we FINISH? Select one of: {options}"
)

# Set of specialist names for the "has any research happened?" check.
_RESEARCHER_NAMES = set(RESEARCHER_MEMBERS)


class RouteResponse(BaseModel):
    """Structured routing decision the supervisor is forced to return.

    The Literal is kept in sync with the AgentName roster by
    test_supervisor.test_route_response_literal_matches_roster (it must equal
    ``ROUTE_OPTIONS`` element-for-element, in order).
    """

    next: Literal[
        "FINISH",
        "ScienceResearcher",
        "FoodBeverageResearcher",
        "TechnologyResearcher",
        "AutomotiveResearcher",
        "ArtCultureResearcher",
        "EnvironmentSocialResearcher",
        "Writer",
    ]


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


def _has_message_from_any(state: AgentState, names: set[str]) -> bool:
    """True if any of ``names`` has already produced a message in the history."""
    return any(getattr(message, "name", None) in names for message in state["messages"])


def _has_message_from(state: AgentState, agent_name: str) -> bool:
    """True if ``agent_name`` has already produced a message in the history."""
    return any(
        getattr(message, "name", None) == agent_name for message in state["messages"]
    )


def make_supervisor_node(supervisor: Runnable) -> Callable[[AgentState], dict]:
    """Adapt the supervisor runnable into a LangGraph node.

    Writes only ``next`` — the supervisor never adds messages to the history.

    A lightweight LLM router cannot be trusted to follow the pipeline, so this
    enforces it deterministically: some specialist must research first, then the
    Writer composes the answer, and only FINISH after the Writer has delivered
    it. When the router picks a specialist it is honoured (that is the topic
    choice); only when it tries to skip research entirely do we fall back to the
    default specialist. The router still controls which and how many specialists
    to consult and when to loop back for more research.
    """

    def supervisor_node(state: AgentState) -> dict:
        decision = supervisor.invoke(state)
        next_node = decision.next

        has_research = _has_message_from_any(state, _RESEARCHER_NAMES)
        has_answer = _has_message_from(state, AgentName.WRITER.value)

        if not has_research and next_node not in _RESEARCHER_NAMES:
            # No research yet and the router tried to skip to the Writer/FINISH:
            # force research first, defaulting to the fallback specialist since
            # the router did not pick a topic.
            logger.info(
                "No research yet; overriding %s -> %s", next_node, DEFAULT_RESEARCHER
            )
            next_node = DEFAULT_RESEARCHER
        elif next_node == FINISH and not has_answer:
            logger.info("Supervisor chose FINISH before the Writer ran; routing to Writer")
            next_node = AgentName.WRITER.value

        logger.info("Supervisor routing decision: next=%s", next_node)
        return {"next": next_node}

    return supervisor_node

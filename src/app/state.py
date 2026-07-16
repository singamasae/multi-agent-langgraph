"""Shared state for the AaaS multi-agent graph."""

import operator
from typing import Annotated, Sequence

from langchain_core.messages import BaseMessage

# pydantic (used by LangServe to derive the API schema) requires
# typing_extensions.TypedDict rather than typing.TypedDict on Python < 3.12.
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State passed between nodes of the supervisor/worker graph.

    Attributes:
        messages: Conversation history. Annotated with ``operator.add`` so a
            node returning ``{"messages": [msg]}`` *appends* to the history
            rather than replacing it. Every worker must return its output as a
            list to append.
        next: The name of the agent the supervisor selected to run next, or
            ``"FINISH"`` when the workflow is complete.
    """

    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str

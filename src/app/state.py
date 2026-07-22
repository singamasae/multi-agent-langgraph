"""Shared state for the AaaS multi-agent graph."""

from typing import Annotated, Sequence

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

# pydantic (used by LangServe to derive the API schema) requires
# typing_extensions.TypedDict rather than typing.TypedDict on Python < 3.12.
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State passed between nodes of the supervisor/worker graph.

    Attributes:
        messages: Conversation history. Typed as ``AnyMessage`` (a
            discriminated union of the concrete ``BaseMessage`` subclasses,
            keyed on the ``type`` field) rather than the generic
            ``BaseMessage`` — required for LangServe's auto-derived Pydantic
            schema to resolve an incoming JSON message like
            ``{"type": "human", ...}`` into a real ``HumanMessage`` instead of
            a bare ``BaseMessage`` that the Gemini client can't serialize.
            Annotated with ``add_messages`` (LangGraph's own reducer, the same
            one used by ``langgraph.graph.MessagesState``) so a node returning
            ``{"messages": [msg]}`` *appends* to the history rather than
            replacing it.
        next: The name of the agent the supervisor selected to run next, or
            ``"FINISH"`` when the workflow is complete.
    """

    messages: Annotated[Sequence[AnyMessage], add_messages]
    next: str

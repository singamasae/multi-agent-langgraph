"""Test doubles that stand in for the two external boundaries (Gemini LLM and
DuckDuckGo search) and for the composed agent runnables.

Everything here is injected via ``GraphDependencies`` so that no test constructs
a real model, makes a network call, or needs a valid API key.
"""

from types import SimpleNamespace
from typing import Any, Optional, Sequence

from langchain_core.messages import AIMessage, BaseMessage


class ScriptedSupervisor:
    """Yields a preset sequence of routing decisions, then FINISH forever.

    Mimics the real supervisor runnable's contract: ``.invoke(state)`` returns
    an object exposing a ``.next`` attribute. Falling back to FINISH once the
    script is exhausted guarantees the graph loop always terminates.
    """

    def __init__(self, route_sequence: Sequence[str]):
        self._routes = list(route_sequence)
        self._index = 0

    def invoke(self, _state: Any, _config: Optional[dict] = None) -> SimpleNamespace:
        if self._index < len(self._routes):
            decision = self._routes[self._index]
            self._index += 1
        else:
            decision = "FINISH"
        return SimpleNamespace(next=decision)


class FakeReactAgent:
    """Stands in for a create_react_agent result.

    ``.invoke`` returns a ``{"messages": [...]}`` dict whose *last* message is
    what the researcher node is expected to surface (dropping the rest).
    """

    def __init__(self, messages: Sequence[BaseMessage]):
        self._messages = list(messages)

    def invoke(self, _input: Any, _config: Optional[dict] = None) -> dict:
        return {"messages": self._messages}


class FakeWriterAgent:
    """Stands in for the writer chain (prompt | llm): ``.invoke`` -> a message."""

    def __init__(self, content: str):
        self._content = content

    def invoke(self, _input: Any, _config: Optional[dict] = None) -> AIMessage:
        return AIMessage(content=self._content)

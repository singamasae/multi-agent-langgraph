import operator
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    State for the AaaS Multi-Agent graph.
    
    Attributes:
        messages: The history of messages between user and agents.
                  Annotated with operator.add so that new messages are appended
                  rather than replacing the existing list.
        next: The name of the next agent to execute, as determined by the Supervisor.
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str

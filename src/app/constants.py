"""Single source of truth for the agent roster.

Everything that needs to know "which workers exist" — the supervisor's routing
prompt, the structured-output schema, and the graph's conditional edges — derives
from :class:`AgentName` here. Adding a worker is a one-line change in this file
(plus the worker module and its graph registration).
"""

from enum import Enum


class AgentName(str, Enum):
    """Names of the worker agents managed by the supervisor.

    Subclasses ``str`` (rather than ``enum.StrEnum``, which is 3.11+) so the
    values are usable directly as LangGraph node keys and message ``name`` tags.
    """

    RESEARCHER = "Researcher"
    WRITER = "Writer"


# Sentinel the supervisor returns when the workflow is complete.
FINISH = "FINISH"

# Worker roster in declaration order — the canonical list of members.
MEMBERS: list[str] = [member.value for member in AgentName]

# Every value the supervisor is allowed to route to (workers + FINISH).
ROUTE_OPTIONS: list[str] = [FINISH, *MEMBERS]

"""Assemble the supervisor/worker StateGraph from injected dependencies."""

from typing import Hashable

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ..agents.researcher import make_researcher_node
from ..agents.supervisor import make_supervisor_node
from ..agents.writer import make_writer_node
from ..constants import FINISH, MEMBERS, AgentName
from ..state import AgentState
from .dependencies import GraphDependencies

# Node key for the supervisor (not a worker, so it lives outside the roster).
SUPERVISOR = "Supervisor"


def build_graph(deps: GraphDependencies) -> CompiledStateGraph:
    """Build and compile the workflow.

    Topology: START -> Supervisor; Supervisor routes (conditionally) to a worker
    or to END on FINISH; every worker edges back to the Supervisor.
    """
    workflow = StateGraph(AgentState)

    # add_node's overloads don't infer a plain (state) -> dict node callable,
    # so these are annotated for the reader and silenced for the type checker.
    workflow.add_node(SUPERVISOR, make_supervisor_node(deps.supervisor))  # type: ignore[call-overload]
    workflow.add_node(AgentName.RESEARCHER.value, make_researcher_node(deps.researcher_agent))  # type: ignore[call-overload]
    workflow.add_node(AgentName.WRITER.value, make_writer_node(deps.writer_agent))  # type: ignore[call-overload]

    # Workers always return control to the supervisor.
    for member in MEMBERS:
        workflow.add_edge(member, SUPERVISOR)

    # The supervisor routes on state["next"]: to a worker, or END when FINISH.
    conditional_map: dict[Hashable, str] = {member: member for member in MEMBERS}
    conditional_map[FINISH] = END
    workflow.add_conditional_edges(SUPERVISOR, lambda state: state["next"], conditional_map)

    workflow.add_edge(START, SUPERVISOR)

    return workflow.compile()

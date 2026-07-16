from langgraph.graph import StateGraph, START, END
from .state import AgentState
from .agents.supervisor import get_supervisor_agent
from .agents.researcher import researcher_node
from .agents.writer import writer_node

def create_graph():
    """
    Creates and compiles the LangGraph StateGraph for the AaaS MVP.
    """
    # 1. Initialize the StateGraph with our custom AgentState
    workflow = StateGraph(AgentState)
    
    # 2. Add nodes
    def supervisor_node(state):
        supervisor = get_supervisor_agent()
        result = supervisor.invoke(state)
        return {"next": result.next}
        
    workflow.add_node("Supervisor", supervisor_node)
    workflow.add_node("Researcher", researcher_node)
    workflow.add_node("Writer", writer_node)
    
    # 3. Define edges
    # Workers always return to the supervisor
    workflow.add_edge("Researcher", "Supervisor")
    workflow.add_edge("Writer", "Supervisor")
    
    # The supervisor uses conditional edges to route to the next worker or FINISH
    members = ["Researcher", "Writer"]
    conditional_map = {member: member for member in members}
    conditional_map["FINISH"] = END
    
    workflow.add_conditional_edges(
        "Supervisor",
        lambda x: x["next"],
        conditional_map
    )
    
    # 4. Set the entry point
    workflow.add_edge(START, "Supervisor")
    
    # 5. Compile the graph
    graph = workflow.compile()
    
    return graph

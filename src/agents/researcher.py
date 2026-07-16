from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from ..tools.search import get_search_tool

def get_researcher_agent():
    """
    Creates the Researcher Agent with access to the Search tool.
    Uses create_react_agent which natively supports function calling.
    """
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    tools = [get_search_tool()]
    
    system_prompt = (
        "You are an expert researcher. Use the search tool to find the most up-to-date and relevant "
        "information regarding the user's query. Provide a clear, bulleted summary of facts found."
    )
    
    return create_react_agent(llm, tools, state_modifier=system_prompt)

def researcher_node(state, config):
    """
    Node function for LangGraph to execute the Researcher agent.
    """
    agent = get_researcher_agent()
    # Invoke the agent with the current messages
    result = agent.invoke({"messages": state["messages"]})
    
    # We extract the last message (the final response from the agent after tool calls)
    last_message = result["messages"][-1]
    
    # Return it as an AIMessage with the name "Researcher" so the supervisor knows who wrote it
    return {
        "messages": [
            AIMessage(content=last_message.content, name="Researcher")
        ]
    }

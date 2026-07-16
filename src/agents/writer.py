from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

def get_writer_agent():
    """
    Creates the Writer Agent. It is a standard LLM chain without tools,
    tasked with synthesizing research into a final response.
    """
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.7)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert technical writer. Write a comprehensive, well-structured, "
                   "and engaging response based ONLY on the research provided by the Researcher. "
                   "Do not add made-up facts or hallucinate. Format your output in clean Markdown. "
                   "If there is no research provided, ask the Researcher to provide information."),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    return prompt | llm

def writer_node(state, config):
    """
    Node function for LangGraph to execute the Writer agent.
    """
    agent = get_writer_agent()
    result = agent.invoke({"messages": state["messages"]})
    
    return {
        "messages": [
            AIMessage(content=result.content, name="Writer")
        ]
    }

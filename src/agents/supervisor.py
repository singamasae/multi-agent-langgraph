from typing import Literal
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

members = ["Researcher", "Writer"]
# Options for routing: the agent names + "FINISH"
options = ["FINISH"] + members

class RouteResponse(BaseModel):
    next: Literal["FINISH", "Researcher", "Writer"] # type: ignore

def get_supervisor_agent():
    """
    Creates and returns the Supervisor Agent.
    The supervisor is a lightweight LLM router that decides which agent
    should act next based on the conversation history.
    """
    # Using Gemini 1.5 Flash for fast routing
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    
    system_prompt = (
        "You are a supervisor tasked with managing a conversation between the"
        " following workers: {members}. Given the following user request,"
        " respond with the worker to act next. Each worker will perform a"
        " task and respond with their results and status. When finished,"
        " respond with FINISH."
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("system", "Given the conversation above, who should act next? Or should we FINISH? Select one of: {options}"),
    ]).partial(options=str(options), members=", ".join(members))
    
    # We use structured output to strictly force the LLM to choose one of the options
    return prompt | llm.with_structured_output(RouteResponse)

import os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langserve import add_routes
from dotenv import load_dotenv

# Import the LangGraph workflow we created
from src.graph import create_graph

# Load environment variables (like GOOGLE_API_KEY)
load_dotenv()

# Initialize FastAPI application
app = FastAPI(
    title="AaaS Research API",
    version="1.0",
    description="A multi-agent research and writing API built with LangGraph and LangServe",
)

@app.get("/")
async def redirect_root_to_docs():
    # Redirect root to Swagger UI docs
    return RedirectResponse("/docs")

# Create the LangGraph agent
agent_graph = create_graph()

# Magic of LangServe: Add API routes and Playground automatically
add_routes(
    app,
    agent_graph,
    path="/research",
)

if __name__ == "__main__":
    import uvicorn
    
    # Check if API Key is configured before starting the server
    if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your_api_key_here":
        print("Error: GOOGLE_API_KEY is not set. Please set it in the .env file.")
    else:
        print("Starting LangServe API at http://localhost:8000")
        print("Access the interactive Playground at http://localhost:8000/research/playground")
        uvicorn.run(app, host="localhost", port=8000)

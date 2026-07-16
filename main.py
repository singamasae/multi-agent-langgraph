import os
import sys
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from src.graph import create_graph

# Load environment variables (API keys)
load_dotenv()

if __name__ == "__main__":
    if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your_api_key_here":
        print("Error: GOOGLE_API_KEY is not set. Please set it in the .env file.")
        sys.exit(1)
        
    if len(sys.argv) < 2:
        print('Usage: python main.py "Your prompt here"')
        sys.exit(1)
        
    user_input = sys.argv[1]
    
    graph = create_graph()
    initial_state = {"messages": [HumanMessage(content=user_input, name="User")]}
    
    print(f"Memproses permintaan: '{user_input}'...\n")
    
    # Execute the workflow
    try:
        final_state = graph.invoke(initial_state, {"recursion_limit": 20})
        
        print("--- Riwayat Eksekusi Multi-Agent ---")
        for msg in final_state["messages"]:
            name = getattr(msg, 'name', "Unknown")
            if not name:
                name = "Unknown"
            print(f"\n[{name}]:")
            
            content = str(msg.content)
            # Print full content only for User and Writer, truncate intermediate Researcher steps
            if len(content) > 500 and name not in ["User", "Writer"]:
                print(content[:500] + "...\n[TRUNCATED FOR READABILITY]")
            else:
                print(content)
                
        print("\n================ HASIL AKHIR ================\n")
        print(final_state["messages"][-1].content)
        
    except Exception as e:
        print(f"Terjadi kesalahan saat eksekusi: {e}")

from langchain_community.tools import DuckDuckGoSearchResults

def get_search_tool():
    """
    Returns an instance of the DuckDuckGo search tool.
    This tool allows agents to search the internet for the latest information.
    """
    # DuckDuckGoSearchResults returns search results as a string
    # with titles, links, and snippets.
    search_tool = DuckDuckGoSearchResults(max_results=3)
    return search_tool

"""Web search tool for the Researcher agent (DuckDuckGo, no API key required).

The search width comes from settings. We configure it on an explicit
``DuckDuckGoSearchAPIWrapper`` (rather than passing ``max_results`` straight to
the tool, which binds ambiguously) so the value is deterministic and testable.
"""

from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_core.tools import BaseTool

from ..config import Settings


def build_search_tool(settings: Settings) -> BaseTool:
    """Build a DuckDuckGo results tool limited to ``search_max_results`` hits."""
    api_wrapper = DuckDuckGoSearchAPIWrapper(max_results=settings.search_max_results)
    return DuckDuckGoSearchResults(api_wrapper=api_wrapper)

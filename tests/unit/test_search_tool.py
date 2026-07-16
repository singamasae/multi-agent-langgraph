"""Tests for the search tool factory (constructs the tool, makes no network call)."""

from langchain_core.tools import BaseTool

from app.tools.search import build_search_tool


def test_build_search_tool_applies_configured_max_results(settings):
    tool = build_search_tool(settings)

    assert isinstance(tool, BaseTool)
    assert tool.api_wrapper.max_results == settings.search_max_results


def test_build_search_tool_reflects_overridden_width(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("SEARCH_MAX_RESULTS", "1")
    from app.config import Settings

    tool = build_search_tool(Settings(_env_file=None))

    assert tool.api_wrapper.max_results == 1

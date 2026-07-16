"""Worker and supervisor agents.

Each module exposes a ``build_*`` factory (pure: takes injected collaborators,
returns a runnable) and a ``make_*_node`` adapter (wraps the runnable as a
LangGraph node function). This split is what lets the graph be assembled from
fakes in tests without constructing a real model.
"""

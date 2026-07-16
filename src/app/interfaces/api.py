"""HTTP API: expose the graph via FastAPI + LangServe."""

import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langserve import add_routes

from ..config import Settings, get_settings
from ..graph.builder import build_graph
from ..graph.dependencies import build_dependencies
from ..logging_config import configure_logging

logger = logging.getLogger(__name__)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Build the FastAPI application serving the research graph.

    Args:
        settings: Injected settings (tests pass a hermetic instance); falls back
            to the cached process settings when omitted.
    """
    if settings is None:
        settings = get_settings()

    configure_logging(settings)

    app = FastAPI(
        title="AaaS Research API",
        version="1.0",
        description="A multi-agent research and writing API built with "
        "LangGraph and LangServe.",
    )

    @app.get("/")
    async def redirect_root_to_docs() -> RedirectResponse:
        return RedirectResponse("/docs")

    graph = build_graph(build_dependencies(settings))
    add_routes(app, graph, path="/research")

    logger.info("Research API initialised")
    return app

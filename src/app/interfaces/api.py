"""HTTP API: expose the graph via FastAPI + LangServe."""

import json
import logging
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from langchain_core.messages import HumanMessage
from langserve import add_routes
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..config import Settings, get_settings
from ..constants import RESEARCHER_MEMBERS, AgentName
from ..graph.builder import SUPERVISOR, build_graph
from ..graph.dependencies import build_dependencies
from ..logging_config import configure_logging
from ..output import derive_filename, final_answer_text, write_markdown

logger = logging.getLogger(__name__)

# Static assets served by the API (the /ui status demo).
_STATIC_DIR = Path(__file__).parent / "static"


class RunRequest(BaseModel):
    """Body for POST /run — a single research prompt from the front-end."""

    prompt: str


def _sse(event: str, payload: dict) -> dict:
    """Build one Server-Sent Event (data is JSON-encoded ourselves)."""
    return {"event": event, "data": json.dumps(payload)}


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
        "LangGraph and LangServe. Live agent status demo at /ui.",
    )

    # Enable cross-origin requests only when explicitly configured, so a
    # separate front-end origin can call the API. The built-in /ui demo is
    # served same-origin and needs none of this.
    origins = settings.cors_origins_list
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/")
    async def redirect_root_to_docs() -> RedirectResponse:
        return RedirectResponse("/docs")

    @app.get("/ui")
    async def status_demo() -> FileResponse:
        """Minimal demo page: trigger the agent and watch its live status."""
        return FileResponse(_STATIC_DIR / "index.html")

    graph = build_graph(build_dependencies(settings))

    @app.post("/run")
    async def run_agent(request: RunRequest) -> EventSourceResponse:
        """Run one request, streaming per-agent status as SSE.

        Emits ``status`` events (started → routing to a named researcher →
        writing → each agent done), then a ``result`` event carrying the final
        answer and the path of the Markdown file written into ``OUTPUT_DIR``,
        then ``end``. Any failure (or an empty answer) becomes an ``error``
        event. See ``static/index.html`` for the consuming front-end.
        """
        prompt = request.prompt.strip()

        async def event_stream() -> AsyncIterator[dict]:
            if not prompt:
                yield _sse("error", {"message": "The prompt is empty."})
                return

            initial_state = {
                "messages": [HumanMessage(content=prompt, name="User")],
                "next": "",
            }
            collected: list = []
            try:
                yield _sse("status", {"phase": "started"})
                async for chunk in graph.astream(
                    initial_state,
                    {"recursion_limit": settings.recursion_limit},
                    stream_mode="updates",
                ):
                    for node, update in chunk.items():
                        if node == SUPERVISOR:
                            nxt = (update or {}).get("next")
                            if nxt in RESEARCHER_MEMBERS:
                                yield _sse(
                                    "status", {"phase": "researching", "agent": nxt}
                                )
                            elif nxt == AgentName.WRITER.value:
                                yield _sse("status", {"phase": "writing"})
                            # FINISH: the Writer has already produced the answer.
                        else:
                            collected.extend((update or {}).get("messages", []))
                            yield _sse("status", {"phase": "agent_done", "agent": node})

                answer = final_answer_text(collected)
                if not answer.strip():
                    logger.warning("Run produced no answer text")
                    yield _sse(
                        "error",
                        {"message": "The workflow produced an empty answer."},
                    )
                    return

                path = write_markdown(
                    answer, derive_filename(prompt), settings.output_dir
                )
                logger.info("Run answer written to %s", path)
                yield _sse("result", {"answer": answer, "path": path})
                yield _sse("end", {})
            except Exception as exc:  # noqa: BLE001 — surfaced to the client as SSE
                logger.exception("Run failed")
                yield _sse("error", {"message": str(exc)})

        return EventSourceResponse(event_stream(), sep="\n")

    add_routes(app, graph, path="/research")

    logger.info("Research API initialised")
    return app

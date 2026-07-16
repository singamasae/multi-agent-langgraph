"""Command-line interface: run one research request and print the answer."""

import argparse
import logging
import sys
from typing import Optional, Sequence

from langchain_core.messages import HumanMessage
from pydantic import ValidationError

from ..config import Settings
from ..graph.builder import build_graph
from ..graph.dependencies import build_dependencies
from ..logging_config import configure_logging

logger = logging.getLogger(__name__)


def _load_settings() -> Settings:
    """Load settings (seam so tests can inject or force failure)."""
    return Settings()


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="app",
        description="Run the multi-agent researcher/writer workflow on a prompt.",
    )
    parser.add_argument("prompt", help="The research/writing request.")
    args = parser.parse_args(argv)

    try:
        settings = _load_settings()
    except ValidationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    configure_logging(settings)

    graph = build_graph(build_dependencies(settings))

    logger.info("Processing request: %s", args.prompt)
    initial_state = {
        "messages": [HumanMessage(content=args.prompt, name="User")],
        "next": "",
    }
    final_state = graph.invoke(
        initial_state, {"recursion_limit": settings.recursion_limit}
    )

    # Diagnostics go through the logger; stdout carries only the final answer.
    print(final_state["messages"][-1].content)
    return 0

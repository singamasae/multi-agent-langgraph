"""Command-line interface: run one research request and print the answer."""

import argparse
import logging
import os
import sys
from typing import Optional, Sequence

from langchain_core.messages import HumanMessage
from pydantic import ValidationError

from ..config import Settings
from ..constants import AgentName
from ..graph.builder import build_graph
from ..graph.dependencies import build_dependencies
from ..logging_config import configure_logging

logger = logging.getLogger(__name__)


def _final_answer_text(messages) -> str:
    """Return the Writer's answer as plain text.

    Prefers the most recent Writer-authored message (the supervisor may route
    elsewhere after the Writer), falling back to the last message. `.text`
    normalises str/list content to a string (and is empty when the model
    returned no text — e.g. reasoning-only or blocked output).
    """
    for message in reversed(messages):
        if getattr(message, "name", None) == AgentName.WRITER.value:
            return str(message.text)
    return str(messages[-1].text) if messages else ""


def _load_settings() -> Settings:
    """Load settings (seam so tests can inject or force failure)."""
    return Settings()


def _write_markdown(content: str, path: str) -> str:
    """Write ``content`` to a Markdown file, returning the path actually used.

    Ensures a ``.md`` extension and creates parent directories as needed.
    """
    target = path if path.lower().endswith(".md") else f"{path}.md"
    directory = os.path.dirname(target)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(content if content.endswith("\n") else content + "\n")
    return target


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="app",
        description="Run the multi-agent researcher/writer workflow on a prompt.",
    )
    parser.add_argument("prompt", help="The research/writing request.")
    parser.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        help="Write the final answer to a Markdown file (a .md extension is "
        "added if missing) instead of printing it to stdout.",
    )
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

    # Diagnostics go through the logger. The final answer either goes to a
    # Markdown file (with a confirmation on stdout) or straight to stdout.
    final_answer = _final_answer_text(final_state["messages"])

    if not final_answer.strip():
        # Don't silently write an empty file — the model returned no text
        # (empty, blocked, or reasoning-only completion).
        logger.warning("Final message contained no text content")
        print(
            "Error: the workflow produced an empty answer (the model returned no "
            "text). Nothing was written. Try re-running or a stronger WRITER_MODEL.",
            file=sys.stderr,
        )
        return 1

    if args.output:
        written_path = _write_markdown(final_answer, args.output)
        print(f"Final answer written to {written_path}")
    else:
        print(final_answer)
    return 0

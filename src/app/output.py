"""Shared output helpers for the interfaces (CLI and API).

Both interfaces need to turn the graph's final state into a plain-text answer
and persist it as a Markdown file in the configured output directory. This
module owns that logic so the interfaces don't import each other.
"""

import os
import re

from .constants import AgentName


def final_answer_text(messages) -> str:
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


def write_markdown(content: str, path: str, output_dir: str) -> str:
    """Write ``content`` to a Markdown file inside ``output_dir``.

    Only the basename of ``path`` is used, so the file always lands in
    ``output_dir`` regardless of any directories the caller passed. Ensures a
    ``.md`` extension and creates the directory. Raises ``ValueError`` if the
    basename is empty (e.g. a trailing-slash path like ``"foo/"``).
    """
    filename = os.path.basename(path)
    if not filename:
        raise ValueError(f"--output value {path!r} has no filename component.")
    if not filename.lower().endswith(".md"):
        filename = f"{filename}.md"
    os.makedirs(output_dir, exist_ok=True)
    target = os.path.join(output_dir, filename)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(content if content.endswith("\n") else content + "\n")
    return target


def derive_filename(prompt: str) -> str:
    """Slugify a prompt into a safe Markdown basename (no extension).

    Lowercases, collapses runs of non-alphanumerics into single hyphens, trims
    hyphens, and caps the length. Falls back to ``"answer"`` when the prompt
    has no usable characters. ``write_markdown`` adds the ``.md`` extension.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower()).strip("-")
    slug = slug[:60].strip("-")
    return slug or "answer"

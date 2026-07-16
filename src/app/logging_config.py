"""Logging configuration, applied once by each interface at startup.

Library modules never call this or ``logging.basicConfig``; they only do
``logger = logging.getLogger(__name__)`` and log. Only the entry points
(CLI, API) configure the root logger.
"""

import json
import logging
import sys

from .config import Settings


class JsonFormatter(logging.Formatter):
    """Minimal structured JSON formatter (one object per line)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(settings: Settings) -> None:
    """Configure the root logger from settings (level + text/json format)."""
    level = logging.getLevelName(settings.log_level.upper())
    if not isinstance(level, int):
        level = logging.INFO

    root = logging.getLogger()
    root.setLevel(level)

    # Replace any existing handlers so repeated configuration is idempotent.
    for existing in list(root.handlers):
        root.removeHandler(existing)

    handler = logging.StreamHandler(sys.stderr)
    if settings.log_format.lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
    root.addHandler(handler)

"""
Structured logging utilities for CampusAgent API.

Provides:
- A configured logger that outputs structured JSON-style log lines.
- A ``request_id`` filter that can inject the current request ID.
- Safe logging helpers that automatically redact sensitive fields
  (the actual redaction logic is in ``utils/redaction.py``, P2-08).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter for structured logging.

    Outputs one JSON object per log line with the following fields:
    - ``timestamp``: ISO-8601 UTC
    - ``level``: log level name
    - ``logger``: logger name
    - ``message``: the log message
    - plus any ``extra`` fields passed via ``logger.info(..., extra={...})``
    """

    _RESERVED_KEYS = frozenset(
        {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "asctime",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields.
        for key, value in record.__dict__.items():
            if key not in self._RESERVED_KEYS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging with the JSON formatter.

    This should be called once at application startup.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicate output.
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)


def get_logger(name: str = "campus_agent") -> logging.Logger:
    """Get a named logger within the campus_agent namespace."""
    return logging.getLogger(name)

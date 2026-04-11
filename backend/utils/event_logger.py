"""Structured JSONL event logger — appends one JSON object per line."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from ..api.config import BASE_DIR

_LOG_DIR = BASE_DIR / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_EVENT_LOG = _LOG_DIR / "events.jsonl"

_logger = logging.getLogger(__name__)


def log_event(event: str, level: str = "info", **kwargs) -> None:
    """Append a structured event to events.jsonl."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "level": level,
        **kwargs,
    }
    try:
        with _EVENT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        _logger.warning(f"event_logger: failed to write event: {e}")

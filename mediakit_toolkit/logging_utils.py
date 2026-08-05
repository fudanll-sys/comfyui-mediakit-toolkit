"""Structured, redacted logging shared by MediaKit task orchestration."""

from __future__ import annotations

import json
import logging
from typing import Any

from .redaction import redact_text


LOGGER = logging.getLogger("comfyui.mediakit")


def log_event(event: str, **details: Any) -> None:
    """Emit one safe JSON log line for ComfyUI diagnostics."""
    payload = {"event": event, **details}
    message = json.dumps(payload, ensure_ascii=False, default=str)
    LOGGER.info("MediaKit %s", redact_text(message))

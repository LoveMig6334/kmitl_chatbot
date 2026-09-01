"""Structured (JSON lines) request logging.  Message content is opt-in."""

from __future__ import annotations

import json
import logging
import time

log = logging.getLogger("api.request")


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(handler)
    root.setLevel(level)


def log_request(**fields: object) -> None:
    payload = {"ts": round(time.time(), 3), "event": "chat", **{k: v for k, v in fields.items() if v is not None}}
    log.info(json.dumps(payload, ensure_ascii=False, default=str))

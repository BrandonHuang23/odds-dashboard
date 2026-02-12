"""
BoltOdds WebSocket utilities.

BoltOdds sends messages in two formats over WebSocket frames:
  - A single JSON object (dict) - one message per frame
  - A JSON array (list) of objects - batched messages per frame

This is especially common during the initial subscription burst, where the
server dumps 100+ messages rapidly. A single frame can be tens of MiB.

EDUCATIONAL: Message batching is a common WebSocket optimization. Instead of
sending N small frames (each with TCP overhead), the server batches them into
one large frame. Our job is to normalize both formats into a consistent list.
"""

from __future__ import annotations

import json
from typing import Any


# BoltOdds may batch very large payloads (tens of MiB) into a single WebSocket
# frame. The `websockets` library defaults to 1 MiB max, which would disconnect
# with code 1009 ("message too big"). Set to None to disable the limit.
DEFAULT_BOLTODDS_WS_MAX_SIZE = None


def parse_boltodds_ws_payload(payload: str) -> list[dict[str, Any]]:
    """
    Parse a BoltOdds WebSocket payload and return a list of message dicts.

    Handles both single-object and batched-array payloads.
    Any non-dict elements in a batch are silently ignored.
    """
    msg = json.loads(payload)

    if isinstance(msg, dict):
        return [msg]
    if isinstance(msg, list):
        return [m for m in msg if isinstance(m, dict)]
    return []

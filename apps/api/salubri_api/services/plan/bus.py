# SPDX-License-Identifier: AGPL-3.0-or-later
"""In-process event bus feeding the SSE endpoint with pipeline progress."""

import threading
from typing import Any

_lock = threading.Lock()
_events: dict[str, list[dict[str, Any]]] = {}


def publish(plan_id: str, event: str, data: dict[str, Any]) -> None:
    with _lock:
        _events.setdefault(plan_id, []).append({"event": event, "data": data})
        if len(_events) > 200:  # forget the oldest plans
            for k in list(_events)[:50]:
                _events.pop(k, None)


def read_from(plan_id: str, offset: int) -> list[dict[str, Any]]:
    with _lock:
        return list(_events.get(plan_id, [])[offset:])

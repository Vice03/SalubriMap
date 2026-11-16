# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tâches de fond suivies (recalculs, réplications) : on peut attendre leur fin (tests, arrêt propre).

Un vrai worker persistant (table de jobs + verrou consultatif PostgreSQL) est prévu après la finale ;
ce registre évite déjà les threads « tirés et oubliés » qui bloquaient le TRUNCATE des tests.
"""

import threading
from collections.abc import Callable
from typing import Any

_threads: set[threading.Thread] = set()
_lock = threading.Lock()


def spawn(target: Callable[..., Any], *args: Any, name: str = "salubri-bg") -> threading.Thread:
    def run() -> None:
        try:
            target(*args)
        finally:
            with _lock:
                _threads.discard(threading.current_thread())

    t = threading.Thread(target=run, name=name, daemon=True)
    with _lock:
        _threads.add(t)
    t.start()
    return t


def drain(timeout: float = 60.0) -> bool:
    """Attend la fin de toutes les tâches en cours ; renvoie False si le délai est dépassé."""
    import time

    end = time.monotonic() + timeout
    while True:
        with _lock:
            alive = [t for t in _threads if t.is_alive()]
        if not alive:
            return True
        left = end - time.monotonic()
        if left <= 0:
            return False
        alive[0].join(min(left, 1.0))

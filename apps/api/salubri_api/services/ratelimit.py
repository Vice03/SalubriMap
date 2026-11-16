# SPDX-License-Identifier: AGPL-3.0-or-later
"""Limites anti-force brute et anti-pourriel, en mémoire du processus API.

Hypothèse (docs/HYPOTHESES.md, lot A3) : l'API tourne en un seul processus uvicorn ; un redémarrage
remet les compteurs à zéro. nginx ajoute une limite par adresse IP en amont (services/nginx/nginx.conf).
"""

import threading
import time
from collections import defaultdict, deque

LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_S = 15 * 60


class SlidingWindow:
    """Compte des évènements par clé sur une fenêtre glissante."""

    def __init__(self, window_s: float) -> None:
        self.window_s = window_s
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._events[key]
        while q and now - q[0] >= self.window_s:
            q.popleft()
        return q

    def count(self, key: str, now: float | None = None) -> int:
        now = time.monotonic() if now is None else now
        with self._lock:
            return len(self._prune(key, now))

    def retry_after(self, key: str, now: float | None = None) -> int:
        """Secondes avant que le plus ancien évènement sorte de la fenêtre."""
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._prune(key, now)
            return max(1, int(self.window_s - (now - q[0])) + 1) if q else 0

    def add(self, key: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            self._prune(key, now).append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


login_failures = SlidingWindow(LOGIN_WINDOW_S)


def login_blocked(login: str, ip: str) -> int:
    """0 si la tentative est permise, sinon le délai d'attente en secondes."""
    waits = [
        login_failures.retry_after(k)
        for k in (f"login:{login}", f"ip:{ip}")
        if login_failures.count(k) >= LOGIN_MAX_FAILURES
    ]
    return max(waits, default=0)


def record_login_failure(login: str, ip: str) -> None:
    login_failures.add(f"login:{login}")
    login_failures.add(f"ip:{ip}")


def record_login_success(login: str) -> None:
    login_failures.clear(f"login:{login}")


def client_ip(headers: dict[str, str] | object, fallback: str | None) -> str:
    """Adresse du client : en-tête X-Real-IP posé par nginx, sinon l'adresse de la connexion."""
    real = getattr(headers, "get", lambda _k: None)("x-real-ip")
    return (real or fallback or "inconnue").strip()[:64]

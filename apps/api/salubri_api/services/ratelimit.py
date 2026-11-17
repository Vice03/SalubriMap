# SPDX-License-Identifier: AGPL-3.0-or-later
"""Limites anti-force brute et anti-pourriel, en mémoire du processus API.

Connexion : échecs en base (table login_failures), partagés avec la console. Pourriel de signalements :
en mémoire ; hypothèse (docs/HYPOTHESES.md, lot A3) : l'API tourne en un seul processus uvicorn, un redémarrage
remet ces compteurs à zéro. nginx ajoute une limite par adresse IP en amont (services/nginx/nginx.conf).
"""

import threading
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

# Connexion (lot 1.1) : un attaquant ne doit pas pouvoir bloquer le compte d'un autre.
LOGIN_MAX_FAILURES = 5  # par (login, adresse) : blocage dur
IP_MAX_FAILURES = 20  # par adresse, tous logins confondus : blocage dur
LOGIN_SLOW_AFTER = 20  # par login, toutes adresses : pas de blocage, un délai croissant sur les échecs
LOGIN_SLOW_MAX_S = 8.0
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


login_failures = SlidingWindow(LOGIN_WINDOW_S)  # gardé pour la remise à zéro des tests ; la connexion compte en base


def _since() -> datetime:
    return datetime.now(UTC) - timedelta(seconds=LOGIN_WINDOW_S)


def _retry(s: Session, where: str, params: dict[str, str], limit: int) -> int:
    rows = s.execute(
        text(f"SELECT at FROM login_failures WHERE {where} AND at > :since ORDER BY at DESC LIMIT :n"),
        {**params, "since": _since(), "n": limit},
    ).all()
    if len(rows) < limit:
        return 0
    oldest = rows[-1].at  # le limit-ième échec le plus récent : quand il sort de la fenêtre, on repasse sous le seuil
    return max(1, int(LOGIN_WINDOW_S - (datetime.now(UTC) - oldest).total_seconds()) + 1)


def login_blocked(s: Session, login: str, ip: str) -> int:
    """0 si la tentative est permise, sinon le délai d'attente en secondes. Blocage dur seulement par
    (login, adresse) après 5 échecs et par adresse après 20 : un échec venu d'ailleurs ne bloque jamais le titulaire."""
    return max(
        _retry(s, "login = :login AND ip = :ip", {"login": login, "ip": ip}, LOGIN_MAX_FAILURES),
        _retry(s, "ip = :ip", {"ip": ip}, IP_MAX_FAILURES),
    )


def failure_delay_s(s: Session, login: str) -> float:
    """Délai à appliquer à un échec quand le login a déjà subi plus de 20 échecs (toutes adresses) : 1, 2, 4, 8 s.
    Il ne s'applique qu'aux échecs : le bon mot de passe passe tout de suite, d'où qu'il vienne."""
    n = s.execute(
        text("SELECT count(*) FROM login_failures WHERE login = :l AND at > :since"), {"l": login, "since": _since()}
    ).scalar_one()
    if n < LOGIN_SLOW_AFTER:
        return 0.0
    return float(min(LOGIN_SLOW_MAX_S, 2 ** (n - LOGIN_SLOW_AFTER)))


def record_login_failure(s: Session, login: str, ip: str) -> None:
    s.execute(text("INSERT INTO login_failures (login, ip, at) VALUES (:l, :ip, now())"), {"l": login, "ip": ip})


def record_login_success(s: Session, login: str, ip: str) -> None:
    s.execute(text("DELETE FROM login_failures WHERE login = :l AND ip = :ip"), {"l": login, "ip": ip})


def unlock(s: Session, login: str) -> int:
    """Efface les échecs d'un login (toutes adresses) ; renvoie leur nombre."""
    return int(s.execute(text("DELETE FROM login_failures WHERE login = :l"), {"l": login}).rowcount or 0)


def client_ip(headers: dict[str, str] | object, fallback: str | None) -> str:
    """Adresse du client : en-tête X-Real-IP posé par nginx, sinon l'adresse de la connexion."""
    real = getattr(headers, "get", lambda _k: None)("x-real-ip")
    return (real or fallback or "inconnue").strip()[:64]

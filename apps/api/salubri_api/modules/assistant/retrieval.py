# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ancrage : passages des documents du dépôt, découpés par section, cherchés par BM25 (Okapi, k1 = 1,5, b = 0,75).

Pas de base vectorielle ni de modèle d'embeddings : la recherche tourne partout, sans téléchargement."""

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from salubri_api.modules.assistant.interface import DOCS_DIR
from salubri_api.modules.assistant.models import AssistantPassage

DOCS = ["HYPOTHESES.md", "RULES.md", "PARAMETRES.md", "SIMULATION_ODD.md", "SIMULATION_CALIBRATION.md",
        "SIMULATION_SENSIBILITE.md", "RAPPORT_TECHNIQUE.md"]  # fmt: skip
PLAN_GLOB = "PLAN_ARRONDISSEMENT_*.md"
MAX_CHARS = 1400
STOP = set(
    "le la les un une des de du d l et ou en au aux a à est sont pour par sur dans que qui quoi ce cet cette ces "
    "il elle ils elles on se sa son ses leur leurs plus moins ne pas n y avec sans comme mais si donc car "
    "the of and to in is".split()
)  # fmt: skip


def tokens(text: str) -> list[str]:
    t = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    out = []
    for w in re.findall(r"[a-z0-9_]+", t):
        if w in STOP or len(w) < 2:
            continue
        out.append(w[:-1] if len(w) > 4 and w.endswith("s") else w)  # pluriel simple
    return out


def split_doc(name: str, text: str) -> list[tuple[str, str]]:
    """(section, texte) : une section par titre ## ou ###, coupée en morceaux de ~1 400 caractères."""
    parts: list[tuple[str, str]] = []
    title, buf = name, []
    for line in text.splitlines():
        if line.startswith(("## ", "### ")):
            if buf:
                parts.append((title, "\n".join(buf)))
            title, buf = line.lstrip("# ").strip(), []
        elif not line.startswith("<!--"):
            buf.append(line)
    if buf:
        parts.append((title, "\n".join(buf)))
    out = []
    for sec, body in parts:
        body = body.strip()
        while body:
            out.append((sec, body[:MAX_CHARS]))
            body = body[MAX_CHARS:]
    return out


def build_index(s: Session, docs_dir: Path = DOCS_DIR) -> int:
    """Reconstruit la table des passages depuis les documents (appelé au démarrage quand le module est allumé)."""
    s.query(AssistantPassage).delete()
    n = 0
    files = [docs_dir / d for d in DOCS] + sorted(docs_dir.glob(PLAN_GLOB))
    for f in files:
        if not f.exists():
            continue
        for sec, body in split_doc(f.name, f.read_text(encoding="utf-8")):
            s.add(AssistantPassage(doc=f.name, section=sec[:300], text=body, tokens=" ".join(tokens(sec + " " + body))))
            n += 1
    s.commit()
    return n


@dataclass
class Hit:
    doc: str
    section: str
    text: str
    score: float

    @property
    def cite(self) -> str:
        return f"{self.doc} § {self.section}"


def search(s: Session, query: str, k: int = 4, k1: float = 1.5, b: float = 0.75) -> list[Hit]:
    rows = s.query(AssistantPassage).all()
    if not rows:
        return []
    docs = [r.tokens.split() for r in rows]
    avg = sum(len(d) for d in docs) / len(docs)
    df: Counter[str] = Counter()
    for d in docs:
        df.update(set(d))
    q = tokens(query)
    scored = []
    for r, d in zip(rows, docs, strict=True):
        tf = Counter(d)
        sc = 0.0
        for t in q:
            if t not in tf:
                continue
            idf = math.log(1 + (len(docs) - df[t] + 0.5) / (df[t] + 0.5))
            sc += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(d) / avg))
        if sc > 0:
            scored.append(Hit(r.doc, r.section, r.text, round(sc, 3)))
    return sorted(scored, key=lambda h: -h.score)[:k]

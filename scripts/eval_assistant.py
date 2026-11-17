#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Évaluation du module « Assistant » contre un vrai modèle local (questions de
apps/api/salubri_api/modules/assistant/evaluation.json, faits attendus) :

    SALUBRI_ADMIN_TOKEN=... python scripts/eval_assistant.py --api http://localhost --sortie docs/assistant_eval.json

Pile lancée avec SALUBRI_ASSISTANT_ENABLED=true et un modèle local joignable. Pour chaque question : « correct »
si tous les faits attendus sont dans la réponse (casse et accents ignorés), « je ne sais pas » si le modèle le dit,
« faux » sinon ; taux de citation (une source citée entre crochets ou ajoutée) et durée. Ne télécharge rien."""

import argparse
import json
import os
import sys
import time
import unicodedata
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "apps/api/salubri_api/modules/assistant/evaluation.json"


def norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost")
    ap.add_argument("--sortie", default="")
    a = ap.parse_args()
    tok = os.environ.get("SALUBRI_ADMIN_TOKEN", "ouaga2026")
    c = httpx.Client(base_url=a.api, headers={"X-Salubri-Token": tok}, timeout=300)
    st = c.get("/api/assistant/status")
    if st.status_code != 200 or not st.json().get("disponible"):
        print("Assistant indisponible (module éteint ou aucun modèle local) : évaluation non lancée.")
        return 2
    rows, counts = [], {"correct": 0, "faux": 0, "je ne sais pas": 0}
    cited = 0
    for item in json.loads(QUESTIONS.read_text(encoding="utf-8")):
        t0 = time.perf_counter()
        r = c.post("/api/assistant/ask", json={"question": item["q"]})
        dt = time.perf_counter() - t0
        ev = [json.loads(x) for x in r.text.splitlines() if x.strip()] if r.status_code == 200 else []
        ans = "".join(e.get("texte", "") for e in ev if e.get("type") == "texte")
        if "je ne sais pas" in norm(ans):
            verdict = "je ne sais pas"
        elif all(norm(f) in norm(ans) for f in item["faits"]):
            verdict = "correct"
        else:
            verdict = "faux"
        counts[verdict] += 1
        has_cite = "[" in ans or "Sources :" in ans
        cited += has_cite
        rows.append({"question": item["q"], "verdict": verdict, "cite": has_cite, "duree_s": round(dt, 1),
                     "reponse": ans[:400]})  # fmt: skip
        print(f"{verdict:15} {dt:5.1f} s  {item['q']}")
        time.sleep(11)  # limite de 6 questions par minute et par utilisateur
    n = len(rows)
    lat = sorted(r["duree_s"] for r in rows)
    res = {"modele": st.json().get("modele"), "questions": n, **counts, "taux_citation": round(cited / n, 3),
           "latence_mediane_s": lat[n // 2], "latence_max_s": lat[-1], "detail": rows}  # fmt: skip
    print(json.dumps({k: v for k, v in res.items() if k != "detail"}, ensure_ascii=False))
    if a.sortie:
        Path(a.sortie).write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

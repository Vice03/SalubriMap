#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Figures du rapport technique, tracées en SVG (sans dépendance) depuis les résultats des vrais calculs :

- docs/figures/plan_arr<N>.json      (scripts/plan_arrondissement.py)   → scenarios_arr<N>.svg
- docs/sensibilite.json              (scripts/sensibilite.py)           → sensibilite.svg
- docs/figures/masquage_controle.json (scripts/eval_masquage.py --json) → masquage.svg

    python scripts/figures_rapport.py --arrondissement 9
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs/figures"
INK, MUTED, GRID = "#222", "#666", "#ddd"
COLORS = ["#1d4e3f", "#c0392b", "#2471a3", "#b9770e"]


def fr(x: float, d: int = 0) -> str:
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


def intervals(data: dict, key: str, title: str, unit: str) -> str:  # type: ignore[type-arg]
    """Une ligne par scénario : point = médiane, trait = intervalle à 90 %."""
    names = list(data)
    vals = [data[k]["sim"][key] for k in names]
    hi = max(v["p95"] for v in vals) * 1.1
    w, left, row = 700, 200, 34
    h = 50 + row * len(names) + 30
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="sans-serif" font-size="12">',
           f'<text x="10" y="20" font-size="14" fill="{INK}">{title}</text>']  # fmt: skip
    sx = lambda v: left + v / hi * (w - left - 70)  # noqa: E731
    for t in range(0, 5):
        v = hi * t / 4
        out.append(f'<line x1="{sx(v):.0f}" y1="35" x2="{sx(v):.0f}" y2="{h - 25}" stroke="{GRID}"/>')
        out.append(f'<text x="{sx(v):.0f}" y="{h - 10}" text-anchor="middle" fill="{MUTED}">{fr(v)}</text>')
    for i, (nm, v) in enumerate(zip(names, vals, strict=True)):
        y = 50 + i * row
        out.append(f'<text x="{left - 8}" y="{y + 4}" text-anchor="end" fill="{INK}">{nm}</text>')
        out.append(f'<line x1="{sx(v["p5"]):.1f}" y1="{y}" x2="{sx(v["p95"]):.1f}" y2="{y}" stroke="{COLORS[i % 4]}" stroke-width="3"/>')  # fmt: skip
        out.append(f'<circle cx="{sx(v["median"]):.1f}" cy="{y}" r="5" fill="{COLORS[i % 4]}"/>')
        out.append(f'<text x="{sx(v["p95"]) + 6:.1f}" y="{y + 4}" fill="{MUTED}">{fr(v["median"])} {unit}</text>')
    out.append("</svg>")
    return "\n".join(out)


def bars(labels: list[str], values: list[float], title: str, fmt: str = "{:.2f}", vmax: float | None = None) -> str:
    w, left, row = 640, 230, 30
    h = 45 + row * len(labels)
    vmax = vmax or max(values) or 1
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="sans-serif" font-size="12">',
           f'<text x="10" y="20" font-size="14" fill="{INK}">{title}</text>']  # fmt: skip
    for i, (lab, v) in enumerate(zip(labels, values, strict=True)):
        y = 35 + i * row
        bw = max(1.0, v / vmax * (w - left - 70))
        out.append(f'<text x="{left - 8}" y="{y + 14}" text-anchor="end" fill="{INK}">{lab}</text>')
        out.append(f'<rect x="{left}" y="{y + 2}" width="{bw:.1f}" height="18" rx="3" fill="{COLORS[0]}"/>')
        out.append(
            f'<text x="{left + bw + 6:.1f}" y="{y + 15}" fill="{MUTED}">{fmt.format(v).replace(".", ",")}</text>'
        )
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arrondissement", type=int, default=9)
    a = ap.parse_args()
    arr = json.loads((FIG / f"plan_arr{a.arrondissement}.json").read_text(encoding="utf-8"))
    (FIG / f"scenarios_arr{a.arrondissement}.svg").write_text(
        intervals(arr, "wild_dump_t", f"Arrondissement {a.arrondissement} — tonnes en dépôt sauvage sur 90 jours "
                  "(médiane, intervalle à 90 %)", "t"), encoding="utf-8")  # fmt: skip
    s = json.loads((ROOT / "docs/sensibilite.json").read_text(encoding="utf-8"))
    lib = {f["nom"]: f["libelle"] for f in s["facteurs"]}
    st = s["sobol"]["wild_dump_t"]["ST"]
    (FIG / "sensibilite.svg").write_text(
        bars([lib[k] for k in s["sobol_facteurs"]], st, "Indice de Sobol total — dépôts sauvages", vmax=1.0),
        encoding="utf-8",
    )
    m = json.loads((FIG / "masquage_controle.json").read_text(encoding="utf-8"))["par_type"]
    (FIG / "masquage.svg").write_text(
        bars(
            ["Visages — rappel", "Visages — précision", "Plaques — rappel", "Plaques — précision"],
            [m["visage"]["rappel"], m["visage"]["precision"], m["plaque"]["rappel"], m["plaque"]["precision"]],
            "Masquage sur le jeu public de contrôle (cibles : 0,95 visages, 0,90 plaques)",
            vmax=1.0,
        ),
        encoding="utf-8",
    )
    print("figures écrites dans docs/figures/")


if __name__ == "__main__":
    main()

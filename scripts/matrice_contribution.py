#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Régénère la partie automatique de docs/MATRICE_CONTRIBUTION.md (briques réutilisées et licences) depuis
apps/api/pyproject.toml (licences lues dans les paquets installés), pnpm-lock.yaml (versions de apps/go et
apps/web ; licences lues dans node_modules), les Dockerfile et docker-compose.yml. La partie manuelle (équipe) est conservée.

    python scripts/matrice_contribution.py
"""

import json
import re
import tomllib
from importlib import metadata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/MATRICE_CONTRIBUTION.md"
BEGIN, END = "<!-- debut-genere -->", "<!-- fin-genere -->"
LAYER_API = {
    "ortools": "optimisation", "scikit-learn": "optimisation", "numpy": "simulation, optimisation",
    "onnxruntime": "API (masquage)", "osmium": "données", "shapely": "données", "pyproj": "données",
    "geoalchemy2": "API", "imagehash": "API (validation)", "pillow": "API (validation)",
}  # fmt: skip
LAYER_JS = {"onnxruntime-web": "app mobile (masquage)", "exifr": "app mobile", "maplibre-gl": "web"}


def py_licence(name: str) -> str:
    try:
        md = metadata.metadata(name)
    except metadata.PackageNotFoundError:
        return "non installé ici"
    lic = md.get("License-Expression") or ""
    if len(lic) > 40:  # expressions composées (numpy) : la licence principale suffit ici
        lic = lic.split(" AND ")[0] + " (et licences des composants)"
    if not lic:
        cls = [c.split("::")[-1].strip() for c in md.get_all("Classifier") or [] if c.startswith("License ::")]
        lic = ", ".join(cls) or (md.get("License") or "?")[:40]
    return lic.replace("\n", " ")


def rows() -> list[str]:
    out = ["| Brique | Version | Licence | Couche | Source de l'information |", "|---|---|---|---|---|"]
    py = tomllib.loads((ROOT / "apps/api/pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
    for dep in py:
        name = re.split(r"[\[<>=]", dep)[0]
        try:
            ver = metadata.version(name)
        except metadata.PackageNotFoundError:
            ver = "?"
        out.append(f"| {name} | {ver} | {py_licence(name)} | {LAYER_API.get(name, 'API')} | pyproject.toml |")
    lock = yaml.safe_load((ROOT / "pnpm-lock.yaml").read_text(encoding="utf-8"))["importers"]
    for app, layer in (("go", "app mobile"), ("web", "web")):
        for name, d in (lock.get(f"apps/{app}", {}).get("dependencies") or {}).items():
            ver = str(d.get("version", "?")).split("(")[0]
            pj = next((p for p in (ROOT / f"apps/{app}/node_modules/{name}/package.json",
                                   ROOT / f"node_modules/{name}/package.json") if p.exists()), None)  # fmt: skip
            lic = json.loads(pj.read_text(encoding="utf-8")).get("license", "?") if pj else "?"
            out.append(f"| {name} | {ver} | {lic} | {LAYER_JS.get(name, layer)} | pnpm-lock.yaml |")
    images = set()
    for f in [ROOT / "docker-compose.yml", *ROOT.glob("services/*/Dockerfile"), *ROOT.glob("apps/*/Dockerfile")]:
        images |= set(re.findall(r"(?:FROM|image:)\s+([\w./:-]+)", f.read_text(encoding="utf-8")))
    lic_img = {"postgis": "GPL-2.0 (PostGIS), PostgreSQL License", "osrm": "BSD-2-Clause", "nginx": "BSD-2-Clause",
               "python": "PSF-2.0", "node": "MIT"}  # fmt: skip
    for img in sorted(images):
        lic = next((v for k, v in lic_img.items() if k in img), "?")
        out.append(f"| {img} | image | {lic} | infrastructure | Dockerfile / docker-compose.yml |")
    return out


def main() -> None:
    text = DOC.read_text(encoding="utf-8")
    block = "\n".join([BEGIN, *rows(), END])
    DOC.write_text(re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), block, text, flags=re.S), encoding="utf-8")
    print(f"{DOC} mis à jour")


if __name__ == "__main__":
    main()

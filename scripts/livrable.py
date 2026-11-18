#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Assemble le dossier livrable/ : les six livrables du défi 01, copiés depuis leurs sources.

    python scripts/livrable.py              écrit livrable/ (à relancer après une modification des sources)
    python scripts/livrable.py --verifier   échoue si livrable/ n'est plus à jour (utilisé par la CI)

Les sources restent là où elles vivent (apps/, data/, docs/) ; livrable/ n'est qu'une vitrine lisible par le jury.
Aucun fichier n'y est écrit à la main : tout vient de ce script, donc rien ne dérive.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "livrable"
COMMUNE = "data/communes/ouagadougou"

# dossier → [(source, nom dans le dossier)] ; source = fichier ou dossier du dépôt
COPIES: dict[str, list[tuple[str, str]]] = {
    "": [("docs/GUIDE_JURY.pdf", "GUIDE_JURY.pdf")],
    "2_moteur_et_simulateur": [
        (f"{COMMUNE}/params_default.json", "params_default.json"),
        (f"{COMMUNE}/params_schema.json", "params_schema.json"),
        ("docs/PARAMETRES.md", "PARAMETRES.md"),
        ("docs/SIMULATION_ODD.md", "SIMULATION_ODD.md"),
        ("docs/SIMULATION_SENSIBILITE.md", "SIMULATION_SENSIBILITE.md"),
        ("docs/SIMULATION_CALIBRATION.md", "SIMULATION_CALIBRATION.md"),
        ("docs/BENCHMARK_TOURNEES.md", "BENCHMARK_TOURNEES.md"),
        ("docs/HYPOTHESES.md", "HYPOTHESES.md"),
    ],
    "3_tableau_de_bord": [
        ("docs/guide/01_tableau_de_bord.jpg", "captures/01_tableau_de_bord.jpg"),
        ("docs/guide/02_carte.jpg", "captures/02_carte.jpg"),
        ("docs/guide/04_scenario.jpg", "captures/04_scenario.jpg"),
        ("docs/guide/05_comparer.jpg", "captures/05_comparer.jpg"),
        ("docs/PLAN_ARRONDISSEMENT_9.pdf", "PLAN_ARRONDISSEMENT_9.pdf"),
        ("docs/figures/plan_arr9_carte.svg", "figures/plan_arr9_carte.svg"),
        ("docs/figures/scenarios_arr9.svg", "figures/scenarios_arr9.svg"),
    ],
    "4_signalements_geojson": [
        (f"{COMMUNE}/reports_demo.geojson", "signalements_demo.geojson"),
        (f"{COMMUNE}/sdgd2020.geojson", "decharges_sdgd2020.geojson"),
        ("docs/COLLECTE_TERRAIN.md", "COLLECTE_TERRAIN.md"),
        (f"{COMMUNE}/LICENCE_signalements_equipe.md", "LICENCE_signalements_equipe.md"),
    ],
    "5_rapport": [
        ("docs/RAPPORT_TECHNIQUE.pdf", "RAPPORT_TECHNIQUE.pdf"),
        ("docs/RAPPORT_TECHNIQUE.md", "RAPPORT_TECHNIQUE.md"),
        ("docs/PLAN_ARRONDISSEMENT_9.md", "PLAN_ARRONDISSEMENT_9.md"),
        ("docs/PLAN_ARRONDISSEMENT_9.pdf", "PLAN_ARRONDISSEMENT_9.pdf"),
        ("docs/MATRICE_CONTRIBUTION.md", "MATRICE_CONTRIBUTION.md"),
        ("docs/CHECKLIST_FINALE.md", "CHECKLIST_FINALE.md"),
        ("docs/figures", "figures"),
    ],
    "6_video": [("docs/VIDEO_SCRIPT.md", "VIDEO_SCRIPT.md")],
}

LICENCE_DEMO = """<!-- SPDX-License-Identifier: CC0-1.0 -->
# Licence de `signalements_demo.geojson`

Jeu de signalements **simulés** (générés par `scripts/gen_demo_reports.py` à partir du SDGD 2020) : aucun n'est un
vrai signalement de citoyen. Mis dans le domaine public sous **CC0 1.0** : https://creativecommons.org/publicdomain/zero/1.0/
"""

README = {
    "": """<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Livrables — défi 01 « Assainissement de Ouaga »

Équipe Salubri, Hackathon des universités 2026. Ce dossier réunit les six livrables de la fiche du défi ; chaque
sous-dossier a son `README.md` (ce que c'est, comment l'ouvrir ou le lancer, ce qui reste à faire).
Il est **généré** par `python scripts/livrable.py` : les sources restent dans `apps/`, `data/` et `docs/`.

| # | Livrable de la fiche | Dossier | Statut |
|---|---|---|---|
| 1 | Application de signalement hors connexion, masquage automatique des visages et plaques | [`1_application_signalement/`](1_application_signalement/README.md) | fait (code `apps/go`, APK : voir le README) |
| 2 | Moteur d'optimisation et simulateur multi-agents, paramètres dans un fichier documenté | [`2_moteur_et_simulateur/`](2_moteur_et_simulateur/README.md) | fait |
| 3 | Tableau de bord des scénarios et plan de gestion d'un arrondissement | [`3_tableau_de_bord/`](3_tableau_de_bord/README.md) | fait (arrondissement 9, quartiers de démonstration) |
| 4 | Jeu de signalements en GeoJSON, sous licence ouverte | [`4_signalements_geojson/`](4_signalements_geojson/README.md) | jeu de démonstration fourni (CC0) ; jeu de terrain de l'équipe à ajouter |
| 5 | Rapport : démarche, paramètres, scénarios simulés, résultats, plan de gestion | [`5_rapport/`](5_rapport/README.md) | fait (PDF + sources) |
| 6 | Vidéo de démonstration (3 min) | [`6_video/`](6_video/README.md) | plan de tournage prêt ; vidéo à déposer |

**Pour essayer tout de suite** : Docker, puis double-clic sur `SALUBRI.bat` à la racine du dépôt (choix 1).
**Guide pas à pas** : [`GUIDE_JURY.pdf`](GUIDE_JURY.pdf). Code sous AGPL-3.0-or-later, données et documents sous licences ouvertes (détail au `README.md` racine).
""",
    "1_application_signalement": """<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# 1 — Application de signalement hors connexion (Salubri Go)

**Code** : [`apps/go`](../../apps/go) (React + TypeScript, PWA et application Android Capacitor). Notice : [`apps/go/README.md`](../../apps/go/README.md).

- **Hors connexion** : le signalement (photo, position, type, quantité) attend dans la file « Mes envois » et part
  seul au retour du réseau ; l'envoi est idempotent (aucun doublon). Toute l'application se charge sans réseau.
- **Masquage automatique** des visages et des plaques d'immatriculation **sur le téléphone, avant tout envoi**
  (YuNet + YOLOv9-t en ONNX, WebAssembly), avec seconde passe sur le serveur. Méthode et mesures :
  [`docs/MASQUAGE.md`](../../docs/MASQUAGE.md), [`docs/MASQUAGE_EVALUATION.md`](../../docs/MASQUAGE_EVALUATION.md).
- **Guide vocal pour les personnes qui ne lisent pas** : au lancement, une voix française puis une voix mooré
  proposent la langue (le bouton de la langue qui parle brille) ; le signalement se fait ensuite pas à pas, un grand
  bouton par étape : photo → quantité → type de déchet → localisation → remerciement. Les voix françaises sont
  fournies (`apps/go/public/audio/fr/`, générées par `scripts/go_audio_fr.py`). Les voix mooré sont
  enregistrées (`apps/go/public/audio/mos/`, découpées par `scripts/go_audio_mos_decoupe.py`) et **restent à faire valider
  par un locuteur** (22 fichiers, liste et textes dans [`docs/AUDIO_GO.md`](../../docs/AUDIO_GO.md)). « Continuer sans voix » ouvre le formulaire classique.

## L'essayer

- **Navigateur / téléphone** : lancer Salubri (`SALUBRI.bat`, choix 1), puis `http://localhost/go/` ou choix 4 du menu.
- **Android (APK)** : artefact `salubri-go-apk` du workflow GitHub « Android », ou construction locale
  (`apps/go/README.md`, section Android) ; résultat `apps/go/android/app/build/outputs/apk/debug/app-debug.apk`.
  Au premier lancement, saisir l'adresse du serveur affichée par `run/start` (même Wi-Fi).
- **Tests** : `pnpm --filter ./apps/go test` (masquage, file d'attente, guide vocal) et `tests/e2e/test_go_*.py`.
""",
    "2_moteur_et_simulateur": """<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# 2 — Moteur d'optimisation et simulateur multi-agents

**Code** : [`apps/api/salubri_api/services/`](../../apps/api/salubri_api/services) — `planning/` (îlots, demande, placement
des points de regroupement en CP-SAT, distances, tournées OR-Tools avec fenêtres horaires) et `simulation/abm/` (ménages,
pré-collecteurs, brigade Laabal, mairie ; 30 réplications avec intervalles).

**Paramètres, dans un fichier documenté** :
- [`params_default.json`](params_default.json) : les valeurs de départ ; chaque scénario en fait une copie modifiable.
- [`params_schema.json`](params_schema.json) : pour chaque paramètre, l'unité, l'intervalle plausible, la source et son
  statut (mairie, littérature, hypothèse) ; une valeur hors intervalle est refusée au chargement.
- [`PARAMETRES.md`](PARAMETRES.md) : la table lisible, générée depuis le schéma.
- Charger les valeurs de la mairie : `python -m salubri_api.params import mairie.json --simulation` (`--a-blanc` pour voir sans écrire).

**Méthode** : [`SIMULATION_ODD.md`](SIMULATION_ODD.md) (protocole ODD du modèle), [`SIMULATION_SENSIBILITE.md`](SIMULATION_SENSIBILITE.md)
(paramètres les plus influents), [`SIMULATION_CALIBRATION.md`](SIMULATION_CALIBRATION.md), [`BENCHMARK_TOURNEES.md`](BENCHMARK_TOURNEES.md)
(OR-Tools contre repli), [`HYPOTHESES.md`](HYPOTHESES.md) (ce qui est supposé et à remplacer par une donnée).

**Le lancer** : `SALUBRI.bat` → Salubri Sim, ou `run/rehearse` (rejoue l'épreuve du jury). Tests : `run/test`.
""",
    "3_tableau_de_bord": """<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# 3 — Tableau de bord des scénarios et plan de gestion d'un arrondissement

**Application** : Salubri Map et Salubri Sim ([`apps/web`](../../apps/web)), ouverts par `SALUBRI.bat` (choix 1 puis 3) sur `http://localhost/`.
On y crée un scénario, on change un paramètre (camions en panne, saison des pluies, budget, nouveau quartier) et le plan est
recalculé en environ une seconde, avec la cohérence avec la version précédente ; l'onglet « Comparer » met les scénarios côte à côte.

| Captures | |
|---|---|
| ![Tableau de bord](captures/01_tableau_de_bord.jpg) | ![Carte](captures/02_carte.jpg) |
| ![Scénario](captures/04_scenario.jpg) | ![Comparer](captures/05_comparer.jpg) |

**Plan de gestion de l'arrondissement 9** : [`PLAN_ARRONDISSEMENT_9.pdf`](PLAN_ARRONDISSEMENT_9.pdf) (points de regroupement,
tournées, coût, indicateurs simulés avec intervalles). Régénération : `python scripts/plan_arrondissement.py --arrondissement 9`.
Limite écrite : quartiers de démonstration (population réelle INSD 2019 : 336 483 hab.) tant que les limites des secteurs 37 à 40 ne sont pas chargées.
""",
    "4_signalements_geojson": """<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# 4 — Jeu de signalements en GeoJSON, sous licence ouverte

| Fichier | Contenu | Licence |
|---|---|---|
| [`signalements_demo.geojson`](signalements_demo.geojson) | signalements **simulés**, tirés autour des décharges et dépotoirs réels de l'étude SDGD 2020 (aucun n'est un vrai signalement de citoyen) | **CC0 1.0** ([`LICENCE_signalements_demo.md`](LICENCE_signalements_demo.md)) |
| [`decharges_sdgd2020.geojson`](decharges_sdgd2020.geojson) | les décharges et points de collecte de référence (SDGD Ouagadougou, rapport phase 2, mars 2020 ; enquête 2019), positions à environ 500 m | donnée de référence citée (source dans chaque point) |
| `signalements_equipe.geojson` | signalements **réels** collectés par l'équipe dans son secteur, vérifiés, photos masquées | **ODbL 1.0** ([`LICENCE_signalements_equipe.md`](LICENCE_signalements_equipe.md)) — **à ajouter après la sortie terrain** |

Champs de chaque point : `external_id`, `waste_type`, `volume_class`, `reported_at`, `accuracy`, `photo`. Jamais exporté pour les
signalements réels : identifiant d'appareil, commentaire libre, score détaillé.

**Produire le jeu de terrain** (protocole : [`COLLECTE_TERRAIN.md`](COLLECTE_TERRAIN.md)) :
`PYTHONPATH=apps/api python scripts/export_signalements_equipe.py --appareils data/communes/ouagadougou/equipe_appareils.txt`,
puis `python scripts/livrable.py` copie le fichier dans ce dossier.
**État honnête** : le jeu de terrain n'existe pas encore ; seul le jeu de démonstration est fourni.
""",
    "5_rapport": """<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# 5 — Rapport

- [`RAPPORT_TECHNIQUE.pdf`](RAPPORT_TECHNIQUE.pdf) (sources : [`RAPPORT_TECHNIQUE.md`](RAPPORT_TECHNIQUE.md)) : démarche, paramètres, scénarios simulés,
  résultats avec intervalles, sensibilité, masquage, limites. Les chiffres viennent de calculs relancés dans le dépôt.
- [`PLAN_ARRONDISSEMENT_9.pdf`](PLAN_ARRONDISSEMENT_9.pdf) : le plan de gestion de l'arrondissement.
- [`MATRICE_CONTRIBUTION.md`](MATRICE_CONTRIBUTION.md) : briques réutilisées et licences, contribution de chacun.
- [`CHECKLIST_FINALE.md`](CHECKLIST_FINALE.md) : chaque exigence de la fiche, où elle est satisfaite, comment le vérifier, ce qui reste à faire.

Régénération : `python scripts/figures_rapport.py` puis `scripts/md_pdf.sh docs/RAPPORT_TECHNIQUE.md`.
""",
    "6_video": """<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# 6 — Vidéo de démonstration (3 minutes)

Déposer ici la vidéo : **`demo_salubri.mp4`** (1080p, 3 min au plus). Elle suit la fiche : un signalement hors ligne avec masquage →
vérification → carte → plan → tournée du lendemain ; puis un changement de paramètres (2 camions en panne, saison des pluies) et le plan recalculé.

Plan de tournage minute par minute : [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md). Préparation des données : `python scripts/demo_video.py --api http://localhost --arrondissement 9`.
**État** : plan prêt, vidéo à tourner.
""",
}


def contenu() -> dict[Path, bytes]:
    """Tous les fichiers de livrable/ : chemin relatif → octets."""
    out: dict[Path, bytes] = {}
    for dossier, copies in COPIES.items():
        for src, nom in copies:
            p = ROOT / src
            if not p.exists():
                sys.exit(f"source manquante : {src}")
            fichiers = [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file())
            for f in fichiers:
                rel = Path(dossier) / nom / f.relative_to(p) if p.is_dir() else Path(dossier) / nom
                out[rel] = f.read_bytes()
    for dossier, texte in README.items():
        out[Path(dossier) / "README.md"] = texte.encode()
    out[Path("4_signalements_geojson/LICENCE_signalements_demo.md")] = LICENCE_DEMO.encode()
    equipe = ROOT / COMMUNE / "signalements_equipe.geojson"
    if equipe.exists():  # jeu de terrain, dès qu'il existe
        out[Path("4_signalements_geojson/signalements_equipe.geojson")] = equipe.read_bytes()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verifier", action="store_true", help="échoue si livrable/ n'est pas à jour")
    args = ap.parse_args()
    voulu = contenu()
    if args.verifier:
        manque = [str(p) for p, b in voulu.items() if not (OUT / p).is_file() or (OUT / p).read_bytes() != b]
        en_trop = (
            [str(f.relative_to(OUT)) for f in OUT.rglob("*") if f.is_file() and f.relative_to(OUT) not in voulu]
            if OUT.exists()
            else []
        )
        if manque or en_trop:
            print("livrable/ n'est plus à jour : relancer python scripts/livrable.py")
            for m in (manque + en_trop)[:10]:
                print("  -", m)
            return 1
        print(f"livrable/ à jour ({len(voulu)} fichiers)")
        return 0
    if OUT.exists():  # fichiers qui ne viennent plus des sources : retirés
        for f in sorted(OUT.rglob("*"), reverse=True):
            if f.is_file() and f.relative_to(OUT) not in voulu:
                try:
                    f.unlink()
                except PermissionError:
                    print(f"à supprimer à la main : {f.relative_to(ROOT)}")
    for rel, octets in voulu.items():
        dest = OUT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(octets)
    print(f"livrable/ écrit : {len(voulu)} fichiers")
    return 0


if __name__ == "__main__":
    sys.exit(main())

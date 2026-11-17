<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Liste de contrôle finale — fiche du défi 01

Chaque exigence de la fiche officielle (dans l'ordre de la revue « SalubriMap against the official Challenge 01
sheet »), où elle est satisfaite dans le dépôt (fichier, test ou commande), et son statut au 17 novembre 2026.
Statuts : **fait** · **fait, limite** (fait, avec une limite écrite) · **à faire par l'équipe** (seule l'équipe
peut le faire : terrain, tournage, envoi OSM, valeurs de la mairie).

| # | Exigence de la fiche | Où dans le dépôt | Vérification | Statut |
|---|---|---|---|---|
| 1 | Carte des dépotoirs et signalements vérifiés | règles R1–R12 (`docs/RULES.md`), consolidation, modération dans Salubri Map, exports GeoJSON/CSV/OSM | `apps/api/tests/test_rules*.py`, `test_export*.py` ; `run/rehearse` (54 pièges) | fait, limite : vérifié sur données de démonstration tant que la collecte (n° 9) n'est pas faite |
| 2 | Plan : placement des points de regroupement | CP-SAT avec objectif, couverture, capacité, stabilité, borne et écart (`services/planning/placement_opt.py`, `summary.placement`) | `tests/test_placement_opt.py` (optimum = énumération) | fait |
| 3 | Plan : tournées optimisées | VRP OR-Tools avec fenêtres, rotations, borne inférieure (`summary.vrp`) ; `docs/BENCHMARK_TOURNEES.md` | `tests/test_vrp_bound.py` ; `python scripts/benchmark_tournees.py` | fait, limite : flotte de démo insuffisante pour la ville entière |
| 4 | Simulation multi-agents : ménages, pré-collecteurs, brigade Laabal, mairie | `services/simulation/abm/`, `docs/SIMULATION_ODD.md`, 30 réplications et intervalles, `docs/SENSIBILITE.md` | `tests/test_abm.py` (cohérence ±10 % avec le modèle agrégé), `tests/test_sensitivity.py` ; `python scripts/sensibilite.py` | fait, limite : comportements non calés sur une enquête |
| 5 | Paramètres modifiables dans un fichier documenté, comparaison de scénarios | `params_default.json` + `params_schema.json`, `docs/PARAMETRES.md` (généré), Salubri Sim (comparer) | `tests/test_params_schema.py` ; `python -m salubri_api.params check` | fait |
| 6 | Valeurs de départ de la mairie | `python -m salubri_api.params import mairie.json --simulation` | `tests/test_params_schema.py::test_import_mairie_une_commande` | **à faire par l'équipe** : obtenir les valeurs (budget, flotte, kg/hab/j) et lancer la commande |
| 7 | Plan de gestion d'un arrondissement | `docs/PLAN_ARRONDISSEMENT_9.md` + PDF | `python scripts/plan_arrondissement.py --arrondissement 9` | fait, limite : quartiers et populations de démonstration ; **à faire par l'équipe** : charger les limites et populations INSD de l'arrondissement 9 et relancer |
| 8 | Test en direct : pièges, puis camions en panne, pluie, nouveau quartier ; plan cohérent | `scripts/rehearse.py`, `data/rehearsal/scenario_changes.yaml` (assertions de cohérence), mesures dans `docs/REHEARSAL_REPORT.md` | `run/rehearse` (vert) | fait |
| 9 | Application de signalement hors ligne | Salubri Go (file d'attente, envoi idempotent) | `tests/e2e/test_go_*.py` | fait |
| 10 | Masquage automatique des visages et des plaques | téléphone (avant l'envoi) et serveur (seconde passe, rattrapage), `docs/MASQUAGE.md` | `tests/test_masking*.py`, `tests/e2e/test_go_masking.py` ; `python scripts/eval_masquage.py` | fait, limite : rappel visages 0,928 sur le jeu public (cible 0,95 non atteinte) ; **à faire par l'équipe** : 60 photos de terrain annotées (`data/eval/masquage/README.md`) puis mesure |
| 11 | Signalements collectés par l'équipe dans son secteur, GeoJSON sous licence ouverte | protocole et fiche `docs/COLLECTE_TERRAIN.md`, `scripts/export_signalements_equipe.py`, licence ODbL | export testé sur la base de démo | **à faire par l'équipe** : sortie terrain (≥ 50 signalements, arrondissement 9), modération, export, commit du GeoJSON |
| 12 | Jeu de test caché du jury | import GeoJSON/CSV/ZIP avec correspondance des colonnes, systèmes de coordonnées, doublons, hors commune (`docs/IMPORT.md`) | `tests/test_import_inedit.py` (5 fichiers inédits) | fait |
| 13 | Première carte ouverte des dépotoirs de Ouaga dans OpenStreetMap | `docs/OSM_CONTRIBUTION.md` (étiquettes, message, compte dédié), `GET /api/export/osc`, essai `docs/osm/salubri_essai.osc` | `tests/test_export_osm.py` | **à faire par l'équipe** : message à la communauté, attendre l'accord, puis versement depuis le compte dédié |
| 14a | Rapport technique | `docs/RAPPORT_TECHNIQUE.md` + PDF, figures depuis les calculs | `python scripts/figures_rapport.py` ; `scripts/md_pdf.sh docs/RAPPORT_TECHNIQUE.md` | fait (à relire par l'équipe, à régénérer après la collecte) |
| 14b | Vidéo de 3 minutes | `docs/VIDEO_SCRIPT.md`, `scripts/demo_video.py` | `python scripts/demo_video.py --api http://localhost` | **à faire par l'équipe** : tournage et montage |
| 14c | Matrice de contribution avec briques réutilisées et licences | `docs/MATRICE_CONTRIBUTION.md` (généré pour les bibliothèques) | `python scripts/matrice_contribution.py` | **à faire par l'équipe** : noms et pourcentages |
| 15 | Dépôt public, licence libre, déploiement en une commande | AGPL-3.0 (`LICENSE`), `docker compose up` / `run/start`, CI (`.github/workflows/ci.yml`) | CI locale verte (tests, ruff, builds) | **à faire par l'équipe** : pousser et vérifier que la CI passe sur GitHub |

## Commandes de vérification avant la finale

```bash
cd apps/api && ruff check salubri_api tests ../../scripts && ruff format --check salubri_api tests ../../scripts && pytest -q
pnpm -r test && pnpm -r build
run/rehearse          # rapport vert, docs/REHEARSAL_REPORT.md
pytest -q tests/e2e   # pile lancée (SALUBRI_URL)
```

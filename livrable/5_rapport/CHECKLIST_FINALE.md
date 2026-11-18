<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Liste de contrôle finale — fiche du défi 01

Chaque exigence de la fiche officielle (dans l'ordre de la revue « SalubriMap against the official Challenge 01
sheet »), où elle est satisfaite dans le dépôt (fichier, test ou commande), et son statut au 17 novembre 2026 (version 0.4.0).
Statuts : **fait** · **fait, limite** (fait, avec une limite écrite) · **à faire par l'équipe** (seule l'équipe
peut le faire : terrain, tournage, envoi OSM, valeurs de la mairie).

| # | Exigence de la fiche | Où dans le dépôt | Vérification | Statut |
|---|---|---|---|---|
| 1 | Carte des dépotoirs et signalements vérifiés | règles R1–R12 (`docs/RULES.md`), consolidation, modération dans Salubri Map, exports GeoJSON/CSV/OSM | `apps/api/tests/test_rules*.py`, `test_export*.py` ; `run/rehearse` (54 pièges) | fait, limite : vérifié sur données de démonstration tant que la collecte (n° 9) n'est pas faite |
| 2 | Plan : placement des points de regroupement | CP-SAT avec objectif, couverture, capacité, stabilité, borne et écart (`services/planning/placement_opt.py`, `summary.placement`) | `tests/test_placement_opt.py` (optimum = énumération) | fait |
| 3 | Plan : tournées optimisées | VRP OR-Tools avec fenêtres, rotations, borne inférieure (`summary.vrp`) ; `docs/BENCHMARK_TOURNEES.md` | `tests/test_vrp_bound.py`, `tests/test_vrp.py`, `tests/test_detour.py` ; `python scripts/benchmark_tournees.py` (OR-Tools contre repli) | fait, limite : flotte de démo insuffisante pour la ville entière ; **à faire par l'équipe** : caler le facteur de détour et relancer le banc avec OSRM (`docs/DETOUR_CALIBRATION.md`) |
| 4 | Simulation multi-agents : ménages, pré-collecteurs, brigade Laabal, mairie | `services/simulation/abm/`, `docs/SIMULATION_ODD.md`, 30 réplications et intervalles, `docs/SIMULATION_SENSIBILITE.md`, `docs/SIMULATION_CALIBRATION.md`, comportements dans `params_default.json` | `tests/test_abm.py` (cohérence ±10 % avec le modèle agrégé), `tests/test_sensitivity.py` ; `python scripts/sensibilite.py` | fait, limite : comportements non calables sur la seule référence (SDGD 2020) ; **à faire par l'équipe** : obtenir de la mairie les tonnes de dépôts enlevées par mois |
| 5 | Paramètres modifiables dans un fichier documenté, comparaison de scénarios | `params_default.json` + `params_schema.json`, `docs/PARAMETRES.md` (généré), Salubri Sim (comparer) | `tests/test_params_schema.py` ; `python -m salubri_api.params check` | fait |
| 6 | Valeurs de départ de la mairie | `python -m salubri_api.params import mairie.json --simulation` | `tests/test_params_schema.py::test_import_mairie_une_commande` | **à faire par l'équipe** : obtenir les valeurs (budget, flotte, kg/hab/j) et lancer la commande |
| 7 | Plan de gestion d'un arrondissement | `docs/PLAN_ARRONDISSEMENT_9.md` + PDF | `python scripts/plan_arrondissement.py --arrondissement 9` | fait, limite : quartiers de démonstration (population réelle 336 483 hab., INSD 2019, citée dans le plan) ; **à faire par l'équipe** : obtenir les limites des secteurs 37 à 40 (pas en données ouvertes), les charger et relancer |
| 8 | Test en direct : pièges, puis camions en panne, pluie, nouveau quartier ; plan cohérent | `scripts/rehearse.py`, `data/rehearsal/scenario_changes.yaml` (assertions de cohérence, 10 changements tirés au hasard), mesures dans `docs/REHEARSAL_REPORT.md` | `run/rehearse` (vert) | fait |
| 9 | Application de signalement hors ligne | Salubri Go (file d'attente, envoi idempotent) | `tests/e2e/test_go_*.py` | fait |
| 10 | Masquage automatique des visages et des plaques | téléphone (avant l'envoi) et serveur (seconde passe, rattrapage), `docs/MASQUAGE.md` | `tests/test_masking*.py`, `tests/e2e/test_go_masking.py` ; `python scripts/eval_masquage.py` | fait, limite : rappel visages 0,933 (0,938 avec le serveur) sur le jeu public (cible 0,95 non atteinte) ; **à faire par l'équipe** : 60 photos de terrain annotées (`data/eval/masquage/README.md`) puis mesure |
| 11 | Signalements collectés par l'équipe dans son secteur, GeoJSON sous licence ouverte | protocole et fiche `docs/COLLECTE_TERRAIN.md`, `scripts/export_signalements_equipe.py`, licence ODbL | export testé sur la base de démo | **à faire par l'équipe** : sortie terrain (≥ 50 signalements, arrondissement 9), modération, export, commit du GeoJSON |
| 12 | Jeu de test caché du jury | import GeoJSON/CSV/ZIP avec correspondance des colonnes, systèmes de coordonnées, doublons, hors commune (`docs/IMPORT.md`) | `tests/test_import_inedit.py` (6 fichiers inédits, dont photos renommées ou manquantes) | fait |
| 12b | Carte publique : signalements vérifiés seulement, photos masquées, licence visible | API (`PUBLIC_STATUSES`, dossier privé jamais servi), ligne de licence sous la carte (`MapPage.tsx`) | `tests/test_privacy.py`, `tests/e2e/test_web_smoke.py::test_public_map_shows_licence_and_scope` | fait |
| 13 | Première carte ouverte des dépotoirs de Ouaga dans OpenStreetMap | `docs/OSM_CONTRIBUTION.md` (étiquettes, message, compte dédié), `GET /api/export/osc`, essai `docs/osm/salubri_essai.osc` | `tests/test_export_osm.py` | **à faire par l'équipe** : message à la communauté, attendre l'accord, puis versement depuis le compte dédié |
| 14a | Rapport technique | `docs/RAPPORT_TECHNIQUE.md` + PDF, figures depuis les calculs | `python scripts/figures_rapport.py` ; `scripts/md_pdf.sh docs/RAPPORT_TECHNIQUE.md` | fait (à relire par l'équipe, à régénérer après la collecte) |
| 14b | Vidéo de 3 minutes | `docs/VIDEO_SCRIPT.md`, `scripts/demo_video.py` | `python scripts/demo_video.py --api http://localhost` | **à faire par l'équipe** : tournage et montage |
| 14c | Matrice de contribution avec briques réutilisées et licences | `docs/MATRICE_CONTRIBUTION.md` (généré pour les bibliothèques) | `python scripts/matrice_contribution.py` | **à faire par l'équipe** : noms et pourcentages |
| 9b | Guide vocal de Salubri Go pour les non-lecteurs (hors fiche) | `apps/go/src/voice/`, voix françaises `apps/go/public/audio/fr/` (`scripts/go_audio_fr.py`), `docs/AUDIO_GO.md` | `apps/go/src/__tests__/voice.test.ts` (chaque phrase a son fichier) ; essai à l'écran sur téléphone à faire | fait pour le français ; **à faire par l'équipe** : enregistrer les 22 voix mooré (`apps/go/public/audio/mos/`) |
| 15a | Dossier des livrables | `livrable/` (un sous-dossier par livrable, README dans chacun), `scripts/livrable.py`, `run/livrable.bat`, choix G du lanceur | `python scripts/livrable.py --verifier` (étape de la CI) | fait ; vidéo et jeu de terrain à y déposer |
| 15 | Dépôt public, licence libre, déploiement en une commande | AGPL-3.0 (`LICENSE`), `docker compose up` / `run/start`, CI (`.github/workflows/ci.yml`) | CI locale verte (tests, ruff, builds) | **à faire par l'équipe** : pousser et vérifier que la CI passe sur GitHub |

## Modules optionnels (hors fiche, éteints par défaut)

Ils ne font partie d'aucun livrable exigé ; la démonstration se fait modules éteints. Détails : `docs/MODULES.md`.

| Module | Où | Vérification | Statut |
|---|---|---|---|
| Saisons : points et tournées selon l'état des routes | `apps/api/salubri_api/modules/seasons/`, panneau « Routes », onglet Go « Route » | 9 tests d'API, `tests/e2e/test_module_seasons.py`, répétition « Inondation secteur 12 » (module allumé) ; éteint : `scripts/baseline.py` → identique | fait, optionnel ; **à faire par l'équipe** : routes réellement coupées à l'hivernage |
| Assistant local en lecture seule | `apps/api/salubri_api/modules/assistant/`, `run/llm_detect.py`, bouton « Assistant » | 25 tests (modèle simulé), `tests/e2e/test_module_assistant.py` | fait, optionnel ; **à faire par l'équipe** : `scripts/eval_assistant.py` avec un vrai modèle local (30 questions) |

## Commandes de vérification avant la finale

```bash
cd apps/api && ruff check salubri_api tests ../../scripts && ruff format --check salubri_api tests ../../scripts && pytest -q
pnpm -r test && pnpm -r build
run/rehearse          # rapport vert, docs/REHEARSAL_REPORT.md
pytest -q tests/e2e   # pile lancée (SALUBRI_URL)
```

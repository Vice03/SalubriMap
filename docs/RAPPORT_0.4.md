<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Rapport de la version 0.4.0 — de la revue r6 vers la fiche du défi

Une ligne par exigence de la fiche officielle (ordre de la revue r6). « Avant » décrit l'état de la version 0.3,
« Après » l'état de la 0.4.0, « Preuve » le test, la commande ou le document qui l'établit. Pas de note : la
revue indépendante les donnera. Tout ce qui est écrit « mesuré » a été relancé pour cette version ; ce qui n'a
pas pu l'être est écrit « non mesuré » ou « à faire par l'équipe ».

| Exigence | Avant (0.3) | Après (0.4.0) | Preuve |
|---|---|---|---|
| 1. Sécurité, connexion, CI | verrouillage de connexion par compte : 10 essais sur `demo` bloquaient le vrai utilisateur ; outils de test non épinglés ; manifeste de Go servi avec le mauvais type | verrouillage sur le couple (compte, adresse) et par adresse, simple délai par compte, échecs gardés en base, commande `users unlock` ; pytest, ruff, pip-audit, playwright, uv, Node épinglés ; manifeste en `application/manifest+json` ; `make verify` rejoue la CI en local | `tests/test_ratelimit.py` ; `tests/e2e/test_go_citizen.py` ; `scripts/ci/*.sh` |
| 2. Carte des dépotoirs vérifiés | filtrage public en place | inchangé ; ligne visible sous la carte publique : périmètre (vérifiés, photos masquées) et licence ODbL / OSM | `tests/test_privacy.py` ; `tests/e2e/test_web_smoke.py::test_public_map_shows_licence_and_scope` |
| 3. Import face au jeu caché | 5 fichiers inédits | 6 : photos renommées (casse, extension, chemin Windows) retrouvées et nommées dans le rapport, photo absente signalée, aucun choix deviné en cas de doute | `tests/test_import_inedit.py` ; `data/rehearsal/jeu_inedit/LISEZMOI.md` |
| 4. Tournées optimisées | borne inférieure et écart dans le plan ; banc OR-Tools seul ; facteur de détour fixe sans OSRM | banc OR-Tools contre heuristique de repli, tonnes non desservies, option `--osrm` ; facteur de détour paramètre par saison et script de calage sur OSRM ; surcharge d'arrondi (8,001 t dans 8 t) corrigée | `docs/BENCHMARK_TOURNEES.md` ; `tests/test_vrp.py`, `tests/test_detour.py` ; **non mesuré** contre OSRM : `docs/DETOUR_CALIBRATION.md` (à faire par l'équipe) |
| 5. Placement des points | CP-SAT avec stabilité ; cohérence vérifiée sur les changements prévus | en plus : 10 changements de paramètres tirés au hasard, bornes écrites (≥ 70 % des points en place, ≤ 30 m de déplacement moyen sur tous les points, pas de perte de couverture), tout vert ; la borne de déplacement a été redéfinie après un premier passage (écrit dans le fichier) | `docs/REHEARSAL_REPORT.md` ; `data/rehearsal/scenario_changes.yaml` |
| 6. Paramètres documentés, scénarios, plan d'arrondissement | fichier documenté sans les comportements ; plan de l'arrondissement 9 avec 4 variantes et population de démonstration | 34 paramètres de comportement dans le fichier ; plan avec 6 variantes (budget −30 %, pluies + 2 pannes), tableau par point (position, quartier, capacité, jours), indicateurs de suivi ; population réelle citée (336 483 hab., INSD 2019) | `docs/PARAMETRES.md` ; `tests/test_params_schema.py` ; `docs/PLAN_ARRONDISSEMENT_9.md` et PDF ; limites des secteurs **à faire par l'équipe** |
| 7. Simulation multi-agents | modèle à agents, 30 réplications, Morris + Sobol sur 4 paramètres, comportements non calés | calage tenté contre le SDGD 2020 : **échec documenté** (aucune combinaison ne reproduit la référence ; analogue inadapté) ; 30 réplications avec médiane et intervalle pour chaque indicateur ; Sobol sur 8 paramètres avec figure | `docs/SIMULATION_CALIBRATION.md` ; `docs/SIMULATION_SENSIBILITE.md` ; référence de débit **à demander à la mairie** |
| 8. Masquage hors ligne | photo refusée (503) si le détecteur du serveur tombait ; pas de mode manuel encadré ; petits visages manqués | jamais de photo non masquée publiée : mode manuel avec zone ou confirmation, photo mise de côté « à vérifier » si le serveur échoue, rattrapage ; tuiles de 512 px : visages 0,933 → 0,938 avec le serveur, plaques 0,935, 2,2 s par photo (téléphone ralenti ×4) ; provenance des modèles vérifiée ; téléchargement 23,9 → ~11 Mo | `tests/test_masking.py`, `tests/e2e/test_go_masking.py` ; `docs/MASQUAGE_EVALUATION.md`, `docs/MASQUAGE_TELEPHONE.md` ; cible visages 0,95 **non atteinte** ; mesure à Ouaga **à faire par l'équipe** |
| 9. Données ouvertes et OSM | export, licence, plan de contribution | inchangé (hors périmètre de cette version) | `docs/OSM_CONTRIBUTION.md` ; collecte et versement **à faire par l'équipe** |
| 10. Livrables écrits | rapport, matrice, liste de contrôle de la 0.3 | rapport technique et PDF mis à jour (calage, sensibilité, tournées, masquage, 6 variantes), figures régénérées ; matrice avec une colonne « masquage » ; liste de contrôle mise à jour | `docs/RAPPORT_TECHNIQUE.md` ; `docs/MATRICE_CONTRIBUTION.md` ; `docs/CHECKLIST_FINALE.md` |

## Vérifications relancées pour cette version

- API : 213 tests, couverture 92 % (`scripts/ci/api.sh`) ; ruff 0.17.5 : aucune erreur, format conforme.
- Applications : typecheck, lint, 22 tests Vitest, builds (`scripts/ci/front.sh`).
- Répétition : verte, pièges, changements prévus et 10 changements au hasard (`docs/REHEARSAL_REPORT.md`).
- Navigateur : 20 tests e2e verts sur la pile locale (API + nginx).
- **Non relancé** : le job « stack » (`docker compose up --build` sur un clone neuf), bloqué ici par la limite de
  téléchargement de Docker Hub ; à vérifier sur GitHub après le `git push`.

## À faire par l'équipe (rien de cela ne peut se faire depuis le dépôt)

- Caler le facteur de détour et relancer le banc avec OSRM (`docs/DETOUR_CALIBRATION.md`, 3 commandes).
- Demander à la mairie : limites des secteurs 37 à 40, tonnes de dépôts sauvages enlevées par mois, valeurs de
  départ (budget, flotte, kg/hab/j) ; puis relancer le plan et le calage.
- Photos de terrain pour mesurer le masquage à Ouagadougou (60 photos, 40 plaques dont des motos).
- Collecte de terrain, vidéo, noms et parts dans la matrice, envoi OSM après accord de la communauté.

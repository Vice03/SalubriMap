<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Salubri — rapport technique

Hackathon des universités 2026 (finale, thème Open Source), défi 01 « Assainissement de Ouaga ». Rapport du
dépôt au 17 novembre 2026. Les chiffres viennent de calculs relancés dans le dépôt ; chaque section donne le
script ou le test qui les produit. Les figures sont tracées par `scripts/figures_rapport.py` et
`scripts/plan_arrondissement.py` depuis ces résultats.

## 1. Contexte

À Ouagadougou, une partie des déchets ménagers finit en dépotoirs sauvages : caniveaux, terrains vagues, abords
des barrages. La collecte repose sur trois acteurs : les ménages, les pré-collecteurs (charrettes, tricycles,
abonnement mensuel) qui vident dans des points de regroupement ou des centres de collecte et de transit (CCT),
et la mairie (camions vers la décharge, nettoyage des dépotoirs), appuyée par la brigade verte Laabal. Le défi
demande : repérer les dépotoirs avec les citoyens, placer les points de regroupement, organiser les tournées,
simuler la filière et ses aléas (pannes, saison des pluies), et livrer des données ouvertes.

## 2. Démarche

Une plateforme libre en trois applications qui partagent une API :

- **Salubri Go** (application web installable, hors ligne) : le citoyen signale un dépôt ; visages et plaques
  sont floutés **sur le téléphone avant l'envoi**, puis une seconde fois sur le serveur.
- **Salubri Map** : modération, carte des dépotoirs consolidés, exports (GeoJSON, CSV, OSM).
- **Salubri Sim** : scénarios (paramètres, flotte, quartiers actifs), plan recalculé en quelques secondes,
  différences avec la version précédente, simulation de la filière avec intervalles.

Principe : chaque changement (panne, saison, quartier, paramètre) crée une nouvelle version de plan, recalculée
seulement pour les étapes touchées, et mesurée contre la précédente (cohérence, § 6.3).

## 3. Architecture

FastAPI + PostgreSQL/PostGIS + OSRM (distances routières, profil saison sèche et saison des pluies), nginx,
deux applications React, Docker Compose (`docs/ARCHITECTURE.md`). Chaîne de calcul : E1 îlots (bâtiments
regroupés par ~30) → E2 demande → E3 points de regroupement → E4 matrice de distances → E5 tournées →
E6 simulation rapide → E7 différences et cohérence. Chaque étape a une clé de cache ; un changement ne recalcule
que l'aval de ce qu'il touche (`docs/REHEARSAL_REPORT.md` : étapes recalculées et en cache par événement).

## 4. Données

| Donnée | Source | Licence |
|---|---|---|
| Routes, cours d'eau, centres de santé | OpenStreetMap (extrait Geofabrik) | ODbL |
| Bâtiments | Google Open Buildings v3 (confiance ≥ 0,7) | CC BY 4.0 / ODbL |
| Quartiers et populations | jeu de **démonstration** (`quartiers.geojson`, `source: demo`) | — |
| CCT existants | SDGD 2020 (positions relevées) | à confirmer |
| Signalements | citoyens (Salubri Go), imports, collecte de l'équipe | ODbL (`COLLECTE_TERRAIN.md`) |

Limite principale : les limites et populations des quartiers sont des ordres de grandeur ; il faut les
remplacer par celles du recensement (INSD) — un seul fichier à changer (`docs/NOUVELLE_COMMUNE.md`).

## 5. Paramètres

Toutes les valeurs de départ sont dans `data/communes/ouagadougou/params_default.json`, décrites dans
`params_schema.json` (unité, intervalle plausible, source, modèles qui les utilisent) et dans
[`PARAMETRES.md`](PARAMETRES.md), généré. Une valeur hors intervalle est refusée au chargement. Les valeurs de
la mairie se chargent en une commande : `python -m salubri_api.params import mairie.json --simulation`, avec le
rapport des différences. La plupart des valeurs sont des **hypothèses** sourcées ; la sensibilité (§ 8.4) dit
lesquelles mesurer d'abord.

## 6. Modèles

### 6.1 Placement des points de regroupement

Problème d'optimisation résolu par CP-SAT (OR-Tools) : sites candidats sur les routes tous les ~50 m hors zones
d'exclusion (cours d'eau, bâtiments), points existants, centres d'un k-means pondéré (solution de départ et de
repli). On minimise la marche pondérée par la demande, avec pénalités pour un îlot au-delà de la distance de
marche (300 m), pour un point au-delà de sa capacité, un coût d'ouverture par point, et une **pénalité de
stabilité** : déplacer un point existant coûte comme faire marcher sa charge 300 m de plus. Objectif, borne et
écart sont rendus dans le plan (`summary.placement`). Tests : optimum égal à l'énumération sur de petites
instances (`tests/test_placement_opt.py`).

### 6.2 Tournées

VRP avec capacités, fenêtres horaires, deux rotations par camion et points abandonnables (OR-Tools, recherche
locale guidée). Chaque plan donne les km, une **borne inférieure garantie** et l'écart majorant
(`summary.vrp`). Banc d'essai ([`BENCHMARK_TOURNEES.md`](BENCHMARK_TOURNEES.md)) : sur la zone pilote, à 1 s,
0,7 % de la meilleure solution connue (9 exécutions) ; sur la ville entière, la flotte de démonstration
(8 camions) ne dessert que 74 points sur 1 034 : il manque des camions, pas du calcul.

### 6.3 Cohérence entre versions

Pour chaque nouvelle version : part des points inchangés, déplacement moyen et maximal, similarité de Jaccard
des paires (camion, point), écarts de coût et de km, couverture avant et après. La répétition vérifie qu'une
panne, la saison des pluies ou un nouveau quartier **ne déplacent aucun point existant** (100 % inchangés,
`docs/REHEARSAL_REPORT.md`). Limite constatée : après une panne, les tournées sont presque entièrement refaites
(Jaccard ≈ 0,1) car le VRP repart de zéro.

### 6.4 Simulation à agents (résumé ODD)

Protocole complet : [`SIMULATION_ODD.md`](SIMULATION_ODD.md).

- **Agents** : un par ménage (taille, revenu, distance au point, abonnement, habitude), pré-collecteurs
  (charrette, clients, comptes mensuels), brigade Laabal, mairie (tournées du plan, pannes, budget, nettoyage) ;
  points et dépotoirs passifs.
- **Pas d'un jour**, 90 jours : production → pré-collecte → choix des ménages (garder, porter, jeter : logit
  multinomial avec distance, point plein, pluie, crainte de l'amende, norme sociale de l'îlot, habitude) →
  camions → Laabal → nettoyage → fin de mois (abonnements, faillite ou extension des pré-collecteurs, budget).
- **Cohérence** : hétérogénéité coupée, la moyenne de 30 réplications reste à ±10 % du modèle agrégé
  (`tests/test_abm.py`). Construire le modèle à agents a révélé un biais du modèle agrégé (le pré-collecteur
  emportait des déchets de non-abonnés : 12 % de dépôts sauvages en moins), corrigé.
- **Vitesse** : 0,3 s pour 19 000 ménages, 5 s pour 357 000 (ville entière) sur 2 cœurs.
- **Incertitude** : 30 réplications par scénario, médiane et intervalle à 90 % (5ᵉ–95ᵉ centiles).

## 7. Scénarios simulés — Arrondissement 9

Plan complet, tables par point et par tournée, coûts, personnel, risques et consignes de saison des pluies :
[`PLAN_ARRONDISSEMENT_9.md`](PLAN_ARRONDISSEMENT_9.md) (et le PDF). Quatre variantes, 30 réplications chacune.

![Carte des points et tournées](figures/plan_arr9_carte.svg)

![Dépôts sauvages par scénario](figures/scenarios_arr9.svg)

Lecture : la saison des pluies et la perte de deux camions augmentent nettement les dépôts sauvages ; +20 %
d'abonnements ne change presque rien tant que la capacité des pré-collecteurs ne suit pas. Avec 8 camions, une
partie des points n'est pas desservie : le plan chiffre le nombre de camions nécessaire.

## 8. Validation

### 8.1 Tests

API : plus de 200 tests (pytest, base PostGIS réelle), couverture de code ≥ 91 % exigée en CI ; applications :
tests Vitest ; parcours complets dans un vrai navigateur (Playwright, `tests/e2e`, 17 tests dont le signalement
hors ligne avec masquage). CI : ruff épinglé, tests, builds, à chaque push.

### 8.2 Répétition du test en direct

`scripts/rehearse.py` rejoue les pièges anti-triche (photo réutilisée, GPS faux, hors commune, pourriel…) et les
changements de scénario du jury (pannes, pluie, budget, nouveau quartier) contre la pile lancée ; chaque
recalcul doit tenir en quelques secondes et respecter les invariants. Résultat et durées :
[`REHEARSAL_REPORT.md`](REHEARSAL_REPORT.md).

### 8.3 Masquage des visages et des plaques

![Masquage](figures/masquage.svg)

Sur un jeu public de contrôle (WIDER Face et plaques Roboflow, **pas Ouagadougou**) : rappel 0,928 sur les
visages (cible 0,95 **non atteinte**), 0,935 sur les plaques. Le jeu de terrain (≥ 60 photos de l'équipe) reste
à constituer (`data/eval/masquage/README.md`). Détails : [`MASQUAGE.md`](MASQUAGE.md).

### 8.4 Sensibilité

![Sensibilité](figures/sensibilite.svg)

Morris sur 8 paramètres puis Sobol sur les 4 plus influents : la quantité de déchets par habitant explique ~90 %
de la variance des dépôts sauvages ; les hypothèses de comportement pèsent peu dans leurs bornes.
[`SENSIBILITE.md`](SENSIBILITE.md).

## 9. Limites

- Quartiers et populations de démonstration ; plan de l'arrondissement 9 approximatif tant qu'ils ne sont pas
  remplacés.
- Paramètres de comportement des ménages non calés sur une enquête : les simulations comparent des scénarios,
  elles ne prédisent pas.
- Masquage : rappel visages sous la cible sur le jeu de contrôle, pas encore mesuré à Ouagadougou ; un bouton
  « flouter une zone » reste indispensable.
- Tournées refaites entièrement après une panne ; pas de démarrage depuis les tournées précédentes.
- Flotte de démonstration insuffisante pour la ville entière.

## 10. Réutilisation dans une autre commune

Un dossier `data/communes/<commune>/` (quartiers, paramètres, CCT), un extrait OSM et les bâtiments Open
Buildings de l'emprise suffisent ; `scripts/new_commune.py` prépare le dossier et la procédure est dans
[`NOUVELLE_COMMUNE.md`](NOUVELLE_COMMUNE.md). Les paramètres sont vérifiés par le même schéma ; le code ne
contient rien de propre à Ouagadougou. Licences : code AGPL-3.0, documents CC BY 4.0, données ODbL ; briques
réutilisées et leurs licences dans [`LICENCES_TIERCES.md`](LICENCES_TIERCES.md) et
[`MATRICE_CONTRIBUTION.md`](MATRICE_CONTRIBUTION.md).

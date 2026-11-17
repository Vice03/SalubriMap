<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Plan de collecte — Arrondissement 9 de Ouagadougou

Généré par `scripts/plan_arrondissement.py --arrondissement 9` le 2026-11-17, plan v2 du scénario « Arrondissement 9 » ; simulations du modèle à agents, 30 réplications par variante, médiane [intervalle à 90 %]. Ne pas modifier à la main : relancer le script.

> **Données de démonstration.** Les limites et populations des quartiers de cet arrondissement viennent du jeu de démonstration (`quartiers.geojson`, `source: demo`) : Arrondissement 9 — Nord (49 100 hab.), Arrondissement 9 — Sud (56 100 hab.). Les bâtiments sont réels (Open Buildings) mais les populations sont des ordres de grandeur. Remplacer par les limites des secteurs et les populations du recensement (INSD) avant tout usage, puis relancer.

## En bref

- **Population couverte** : 105 200 habitants ; **demande** 441,8 t/semaine.
- **87 points de regroupement** (capacité 2,5 t), couverture à 300 m de marche : 95 % de la population.
- **8 camion(s)** (BF-01, BF-02, BF-03, BF-04, BF-05, BF-06, BF-07, BF-08), 16 tournée(s) par jour d'enlèvement (lundi, jeudi), 425,5 km, **378 647 FCFA** par jour d'enlèvement.
- Points non desservis : 21 ; camions nécessaires pour tout desservir : 11 (disponibles : 8).

![Carte des points et des tournées](figures/plan_arr9_carte.svg)

## Tournées (par jour d'enlèvement)

| Camion | Rotation | Jours | 1er passage | Dernier passage | Points | Tonnage (t) | km | Coût (FCFA) |
|---|---|---|---|---|---|---|---|---|
| BF-01 | 1 | lundi, jeudi | 07:00 | 07:38 | 4 | 7,9 | 27,4 | 32 316 |
| BF-01 | 2 | lundi, jeudi | 08:40 | 09:03 | 3 | 6,9 | 21,8 | 9 820 |
| BF-02 | 1 | lundi, jeudi | 07:00 | 07:34 | 4 | 7,8 | 27,0 | 32 144 |
| BF-02 | 2 | lundi, jeudi | 08:39 | 09:02 | 3 | 7,0 | 22,5 | 10 125 |
| BF-03 | 1 | lundi, jeudi | 07:00 | 07:23 | 3 | 7,4 | 26,9 | 32 086 |
| BF-03 | 2 | lundi, jeudi | 08:31 | 08:54 | 3 | 7,5 | 22,9 | 10 326 |
| BF-04 | 1 | lundi, jeudi | 07:00 | 07:24 | 3 | 7,5 | 27,7 | 32 457 |
| BF-04 | 2 | lundi, jeudi | 08:33 | 08:56 | 3 | 7,2 | 23,1 | 10 382 |
| BF-05 | 1 | lundi, jeudi | 07:00 | 07:22 | 3 | 7,1 | 24,6 | 31 048 |
| BF-05 | 2 | lundi, jeudi | 08:28 | 09:09 | 4 | 7,8 | 27,5 | 12 389 |
| BF-06 | 1 | lundi, jeudi | 07:00 | 08:00 | 6 | 12,0 | 31,3 | 41 297 |
| BF-06 | 2 | lundi, jeudi | 09:14 | 10:01 | 5 | 11,1 | 28,0 | 14 582 |
| BF-07 | 1 | lundi, jeudi | 07:00 | 07:46 | 5 | 11,8 | 30,3 | 40 745 |
| BF-07 | 2 | lundi, jeudi | 08:57 | 09:54 | 6 | 11,8 | 26,5 | 13 801 |
| BF-08 | 1 | lundi, jeudi | 07:00 | 07:47 | 5 | 11,4 | 30,3 | 40 770 |
| BF-08 | 2 | lundi, jeudi | 08:57 | 09:57 | 6 | 11,9 | 27,6 | 14 359 |

## Points de regroupement

| Point | Demande (t/sem.) | Remplissage par enlèvement | Îlots | Créneau | Camion | Passage |
|---|---|---|---|---|---|---|
| CCT-078 | 6,85 | 137 % | 2 | 07:00–17:00 | BF-08 r2 | 09:23 |
| CCT-079 | 4,09 | 82 % | 1 | 07:00–17:00 | BF-08 r2 | 09:46 |
| CCT-080 | 5,91 | 118 % | 2 | 07:00–17:00 | BF-05 r1 | 07:22 |
| CCT-084 | 5,73 | 114 % | 2 | 07:00–17:00 | non desservi | — |
| CCT-086 | 3,57 | 72 % | 1 | 07:00–17:00 | BF-07 r1 | 07:23 |
| P001 | 4,30 | 86 % | 1 | 07:00–17:00 | BF-04 r2 | 08:56 |
| P002 | 3,66 | 73 % | 1 | 07:00–17:00 | non desservi | — |
| P003 | 6,95 | 139 % | 2 | 07:00–17:00 | BF-07 r1 | 07:46 |
| P004 | 6,86 | 137 % | 2 | 07:00–17:00 | BF-08 r1 | 07:47 |
| P005 | 5,63 | 113 % | 2 | 07:00–17:00 | BF-07 r2 | 09:20 |
| P006 | 7,02 | 140 % | 2 | 07:00–17:00 | BF-06 r1 | 07:37 |
| P007 | 3,83 | 77 % | 1 | 07:00–17:00 | BF-05 r2 | 08:40 |
| P008 | 5,50 | 110 % | 2 | 07:00–17:00 | BF-03 r2 | 08:42 |
| P009 | 3,18 | 64 % | 1 | 07:00–17:00 | BF-05 r2 | 08:55 |
| P010 | 5,67 | 113 % | 2 | 07:00–17:00 | BF-08 r1 | 07:00 |
| P011 | 3,67 | 73 % | 1 | 07:00–17:00 | BF-06 r2 | 09:50 |
| P012 | 6,52 | 130 % | 2 | 07:00–17:00 | non desservi | — |
| P013 | 3,99 | 80 % | 1 | 07:00–17:00 | BF-02 r1 | 07:00 |
| P014 | 3,73 | 75 % | 1 | 07:00–17:00 | BF-01 r2 | 08:40 |
| P015 | 8,11 | 162 % | 3 | 07:00–17:00 | BF-06 r2 | 09:38 |
| P016 | 3,56 | 71 % | 1 | 07:00–17:00 | BF-08 r1 | 07:23 |
| P017 | 3,52 | 70 % | 1 | 07:00–17:00 | non desservi | — |
| P018 | 3,50 | 70 % | 1 | 07:00–17:00 | non desservi | — |
| P019 | 5,47 | 109 % | 2 | 07:00–17:00 | BF-03 r1 | 07:11 |
| P020 | 4,53 | 91 % | 1 | 07:00–17:00 | non desservi | — |
| P021 | 6,13 | 123 % | 2 | 07:00–17:00 | BF-02 r2 | 08:51 |
| P022 | 3,06 | 61 % | 1 | 07:00–17:00 | BF-06 r1 | 07:25 |
| P023 | 6,30 | 126 % | 2 | 07:00–17:00 | BF-04 r2 | 08:33 |
| P024 | 5,13 | 103 % | 2 | 07:00–17:00 | BF-07 r2 | 09:32 |
| P025 | 5,63 | 113 % | 2 | 07:00–17:00 | non desservi | — |
| P026 | 4,82 | 96 % | 1 | 07:00–17:00 | BF-01 r1 | 07:25 |
| P027 | 5,59 | 112 % | 2 | 07:00–17:00 | BF-07 r1 | 07:11 |
| P028 | 7,26 | 145 % | 2 | 07:00–17:00 | non desservi | — |
| P029 | 4,52 | 90 % | 1 | 07:00–17:00 | BF-08 r2 | 09:11 |
| P030 | 5,58 | 112 % | 2 | 07:00–17:00 | BF-01 r2 | 09:03 |
| P031 | 3,35 | 67 % | 1 | 07:00–17:00 | non desservi | — |
| P032 | 6,25 | 125 % | 3 | 07:00–17:00 | BF-03 r2 | 08:31 |
| P033 | 9,72 | 194 % | 3 | 07:00–17:00 | BF-04 r1 | 07:11 |
| P034 | 6,30 | 126 % | 2 | 07:00–17:00 | non desservi | — |
| P035 | 6,69 | 134 % | 2 | 07:00–17:00 | non desservi | — |
| P036 | 6,32 | 126 % | 2 | 07:00–17:00 | BF-07 r1 | 07:34 |
| P037 | 6,02 | 120 % | 2 | 07:00–17:00 | BF-03 r1 | 07:23 |
| P038 | 4,60 | 92 % | 2 | 07:00–17:00 | BF-06 r1 | 08:00 |
| P039 | 7,08 | 142 % | 2 | 07:00–17:00 | BF-04 r2 | 08:44 |
| P040 | 6,66 | 133 % | 2 | 07:00–17:00 | BF-04 r1 | 07:00 |
| P041 | 5,93 | 119 % | 2 | 07:00–17:00 | non desservi | — |
| P042 | 2,94 | 59 % | 1 | 07:00–17:00 | BF-07 r2 | 09:43 |
| P043 | 5,52 | 110 % | 2 | 07:00–17:00 | BF-05 r2 | 08:28 |
| P044 | 5,12 | 102 % | 1 | 07:00–17:00 | BF-05 r1 | 07:00 |
| P045 | 6,30 | 126 % | 2 | 07:00–17:00 | BF-06 r2 | 09:14 |
| P046 | 3,17 | 63 % | 1 | 07:00–17:00 | BF-08 r2 | 09:57 |
| P047 | 3,95 | 79 % | 1 | 07:00–17:00 | non desservi | — |
| P048 | 6,90 | 138 % | 2 | 07:00–17:00 | BF-08 r1 | 07:11 |
| P049 | 7,21 | 144 % | 2 | 07:00–17:00 | non desservi | — |
| P050 | 3,62 | 72 % | 1 | 07:00–17:00 | BF-02 r1 | 07:34 |
| P051 | 5,43 | 108 % | 2 | 07:00–17:00 | BF-03 r2 | 08:54 |
| P052 | 3,26 | 65 % | 1 | 07:00–17:00 | BF-07 r2 | 08:57 |
| P053 | 3,97 | 80 % | 1 | 07:00–17:00 | BF-01 r1 | 07:38 |
| P054 | 5,46 | 109 % | 2 | 07:00–17:00 | non desservi | — |
| P055 | 4,04 | 81 % | 1 | 07:00–17:00 | BF-06 r1 | 07:48 |
| P056 | 3,57 | 71 % | 1 | 07:00–17:00 | BF-07 r2 | 09:08 |
| P057 | 3,92 | 78 % | 1 | 07:00–17:00 | BF-07 r2 | 09:54 |
| P058 | 3,75 | 75 % | 1 | 07:00–17:00 | BF-01 r1 | 07:00 |
| P059 | 6,19 | 124 % | 2 | 07:00–17:00 | BF-06 r2 | 10:01 |
| P060 | 6,07 | 121 % | 2 | 07:00–17:00 | BF-06 r1 | 07:14 |
| P061 | 5,41 | 108 % | 2 | 07:00–17:00 | non desservi | — |
| P062 | 2,51 | 50 % | 1 | 07:00–17:00 | BF-08 r2 | 08:57 |
| P063 | 4,89 | 98 % | 1 | 07:00–17:00 | BF-03 r1 | 07:00 |
| P064 | 3,20 | 64 % | 1 | 07:00–17:00 | BF-01 r1 | 07:13 |
| P065 | 3,67 | 73 % | 1 | 07:00–17:00 | BF-05 r2 | 09:09 |
| P066 | 2,88 | 58 % | 1 | 07:00–17:00 | non desservi | — |
| P067 | 5,64 | 113 % | 2 | 07:00–17:00 | non desservi | — |
| P068 | 5,80 | 116 % | 2 | 07:00–17:00 | non desservi | — |
| P069 | 4,16 | 83 % | 1 | 07:00–17:00 | BF-08 r1 | 07:35 |
| P070 | 5,96 | 119 % | 2 | 07:00–17:00 | BF-01 r2 | 08:51 |
| P071 | 8,90 | 178 % | 3 | 07:00–17:00 | BF-02 r1 | 07:11 |
| P072 | 3,02 | 60 % | 1 | 07:00–17:00 | BF-02 r1 | 07:23 |
| P073 | 2,22 | 44 % | 1 | 07:00–17:00 | BF-06 r1 | 07:00 |
| P074 | 3,92 | 78 % | 1 | 07:00–17:00 | BF-02 r2 | 09:02 |
| P075 | 6,04 | 121 % | 3 | 07:00–17:00 | BF-02 r2 | 08:39 |
| P076 | 4,24 | 85 % | 1 | 07:00–17:00 | BF-05 r1 | 07:11 |
| P077 | 3,56 | 71 % | 2 | 07:00–17:00 | non desservi | — |
| P078 | 7,49 | 150 % | 2 | 07:00–17:00 | BF-07 r1 | 07:00 |
| P079 | 3,53 | 70 % | 1 | 07:00–17:00 | BF-06 r2 | 09:25 |
| P080 | 6,57 | 131 % | 2 | 07:00–17:00 | non desservi | — |
| P081 | 4,45 | 89 % | 2 | 07:00–17:00 | BF-08 r2 | 09:34 |
| P082 | 5,10 | 102 % | 2 | 07:00–17:00 | BF-04 r1 | 07:24 |

## Coûts et personnel

- Coût par jour d'enlèvement : 378 647 FCFA, soit ~3 281 607 FCFA par mois (2.0 enlèvements par semaine).
- Personnel par jour d'enlèvement : 8 chauffeur(s) et 16 ripeur(s) (hypothèse : un chauffeur et deux ripeurs par camion).

## Indicateurs simulés (90 jours)

| Indicateur | Référence | 2 camions en panne | Saison des pluies | Abonnements +20 % |
|---|---|---|---|---|
| Tonnes collectées par camion | 3 408,8 [3 361,7 ; 3 463,4] | 2 686,0 [2 628,1 ; 2 751,7] | 3 354,1 [3 286,6 ; 3 411,6] | 3 378,1 [3 294,4 ; 3 436,7] |
| Tonnes pré-collectées | 311,5 [311,4 ; 311,6] | 311,5 [311,4 ; 311,6] | 311,6 [311,5 ; 311,7] | 311,6 [311,6 ; 311,7] |
| Tonnes en dépôt sauvage | 2 062,2 [2 002,6 ; 2 109,2] | 2 757,0 [2 692,2 ; 2 833,8] | 2 943,4 [2 893,0 ; 3 009,4] | 2 098,8 [2 027,2 ; 2 151,2] |
| Dépotoirs actifs (moyenne) | 121,8 [113,9 ; 124,8] | 125,9 [118,1 ; 134,2] | 129,8 [122,9 ; 135,1] | 121,7 [114,1 ; 127,9] |
| Couverture simulée* (%) | 61 [61 ; 62] | 52 [51 ; 53] | 55 [54 ; 55] | 61 [60 ; 62] |
| Taux d'abonnement final (%) | 26 [26 ; 27] | 26 [25 ; 26] | 26 [25 ; 26] | 29 [29 ; 30] |
| Pré-collecteurs actifs (fin) | 10 [10 ; 10] | 10 [10 ; 10] | 10 [10 ; 10] | 10 [10 ; 10] |
| Coût de la mairie (FCFA/t) | 2 696 [2 680 ; 2 709] | 2 566 [2 538 ; 2 593] | 2 830 [2 816 ; 2 847] | 2 703 [2 686 ; 2 720] |
| Jours-points en débordement | 2 678 [2 603 ; 2 741] | 3 536 [3 427 ; 3 624] | 3 238 [3 150 ; 3 325] | 2 746 [2 633 ; 2 841] |

\* Part de la population servie un jour donné : point à portée de marche **et pas plein**, ou passage du pré-collecteur dans les 7 jours. Plus stricte que la couverture du plan (distance seule).

## Risques

- **Pannes** : avec 2 camions en moins, 34 points ne sont pas desservis (21 en référence) ; aucun point ne bouge (points inchangés : 100 %), mais les tournées sont refaites (camions sur les mêmes points : 1 %). Prévoir un camion de réserve ou une rotation supplémentaire.
- **Pré-collecte** : la charrette est le goulot (`SIMULATION_ODD.md` § 11) ; plus d'abonnés sans plus de pré-collecteurs n'augmente pas la pré-collecte.
- **Données** : la quantité de déchets par habitant explique ~90 % de l'incertitude sur les dépôts (`SIMULATION_SENSIBILITE.md`) ; la mesurer par pesée dans l'arrondissement avant de dimensionner.

## Saison des pluies

- Demande +15 % (508,1 t/semaine) et vitesses réduites : 458,8 km, 394 817 FCFA par jour d'enlèvement, 26 point(s) non desservi(s), 16 tournée(s).
- Avant les pluies : curer les caniveaux près des points, déplacer hors des zones inondables les bacs signalés « près de l'eau », vider les dépotoirs proches des cours d'eau en priorité (règle de nettoyage du plan).
- Pendant : ajouter une rotation les jours après une forte pluie, garder un camion en réserve, renforcer les descentes Laabal dans les îlots récurrents en même temps que des rotations de camions (sinon les points débordent).

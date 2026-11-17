<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Plan de collecte — Arrondissement 9 de Ouagadougou

Généré par `scripts/plan_arrondissement.py --arrondissement 9` le 2026-11-17, plan v2 du scénario « Arrondissement 9 » ; simulations du modèle à agents, 30 réplications par variante, médiane [intervalle à 90 %]. Ne pas modifier à la main : relancer le script.

> **Données de démonstration.** Les limites et populations des quartiers de cet arrondissement viennent du jeu de démonstration (`quartiers.geojson`, `source: demo`) : Arrondissement 9 — Nord (49 100 hab.), Arrondissement 9 — Sud (56 100 hab.). Les bâtiments sont réels (Open Buildings) mais les populations sont des ordres de grandeur. Remplacer par les limites des secteurs et les populations du recensement (INSD) avant tout usage, puis relancer.

> **Population réelle** : 336 483 habitants en 2019 (INSD, RGPH 2019, monographie de la commune de Ouagadougou, tableau 2.2), soit 3,2 fois la population de démonstration ci-dessous. Les tonnages, le nombre de points et de camions sont donc à multiplier d'autant ; les limites des secteurs 37 à 40 ne sont pas publiées en données ouvertes (absentes de l'extrait OSM) : **à faire par l'équipe** (demander la carte des secteurs à la mairie d'arrondissement, la charger dans `quartiers.geojson`).

## En bref

- **Population couverte** : 105 200 habitants ; **demande** 441,8 t/semaine.
- **87 points de regroupement** (capacité 2,5 t), couverture à 300 m de marche : 91 % de la population.
- **8 camion(s)** (BF-01, BF-02, BF-03, BF-04, BF-05, BF-06, BF-07, BF-08), 16 tournée(s) par jour d'enlèvement (lundi, jeudi), 434,7 km, **382 833 FCFA** par jour d'enlèvement.
- Points non desservis : 19 ; camions nécessaires pour tout desservir : 11 (disponibles : 8).

![Carte des points et des tournées](figures/plan_arr9_carte.svg)

## Tournées (par jour d'enlèvement)

| Camion | Rotation | Jours | 1er passage | Dernier passage | Points | Tonnage (t) | km | Coût (FCFA) |
|---|---|---|---|---|---|---|---|---|
| BF-01 | 1 | lundi, jeudi | 07:00 | 07:24 | 3 | 7,0 | 25,3 | 31 366 |
| BF-01 | 2 | lundi, jeudi | 08:30 | 09:07 | 4 | 7,8 | 27,6 | 12 418 |
| BF-02 | 1 | lundi, jeudi | 07:00 | 07:24 | 3 | 7,3 | 27,2 | 32 235 |
| BF-02 | 2 | lundi, jeudi | 08:29 | 09:03 | 4 | 7,8 | 22,0 | 9 901 |
| BF-03 | 1 | lundi, jeudi | 07:00 | 07:39 | 4 | 7,8 | 27,6 | 32 438 |
| BF-03 | 2 | lundi, jeudi | 08:45 | 09:07 | 3 | 7,3 | 21,9 | 9 832 |
| BF-04 | 1 | lundi, jeudi | 07:00 | 07:25 | 3 | 7,3 | 25,8 | 31 626 |
| BF-04 | 2 | lundi, jeudi | 08:29 | 09:19 | 4 | 7,9 | 30,3 | 13 650 |
| BF-05 | 1 | lundi, jeudi | 07:00 | 07:24 | 3 | 7,5 | 28,5 | 32 810 |
| BF-05 | 2 | lundi, jeudi | 08:33 | 09:08 | 4 | 7,6 | 24,0 | 10 791 |
| BF-06 | 1 | lundi, jeudi | 07:00 | 08:06 | 6 | 11,9 | 34,3 | 42 830 |
| BF-06 | 2 | lundi, jeudi | 09:15 | 10:01 | 5 | 11,5 | 25,5 | 13 247 |
| BF-07 | 1 | lundi, jeudi | 07:00 | 07:47 | 5 | 11,8 | 30,4 | 40 814 |
| BF-07 | 2 | lundi, jeudi | 08:56 | 09:55 | 6 | 11,8 | 27,1 | 14 110 |
| BF-08 | 1 | lundi, jeudi | 07:00 | 07:46 | 5 | 11,6 | 30,9 | 41 052 |
| BF-08 | 2 | lundi, jeudi | 08:57 | 09:56 | 6 | 12,0 | 26,4 | 13 713 |

## Points de regroupement

| Point | Position (lat, lon) | Quartier servi | Capacité (t) | Demande (t/sem.) | Remplissage par enlèvement | Îlots | Jours d'enlèvement | Créneau | Camion | Passage |
|---|---|---|---|---|---|---|---|---|---|---|
| CCT-078 | 12.39468, -1.46454 | Arrondissement 9 — Sud | 2,5 | 6,85 | 137 % | 2 | lundi, jeudi | 07:00–17:00 | BF-07 r2 | 09:55 |
| CCT-079 | 12.39261, -1.46783 | Arrondissement 9 — Sud | 2,5 | 4,09 | 82 % | 1 | lundi, jeudi | 07:00–17:00 | BF-07 r2 | 09:20 |
| CCT-080 | 12.39177, -1.48015 | Arrondissement 9 — Nord | 2,5 | 5,91 | 118 % | 2 | lundi, jeudi | 07:00–17:00 | BF-06 r2 | 09:27 |
| CCT-084 | 12.38024, -1.45478 | Arrondissement 9 — Sud | 2,5 | 5,73 | 114 % | 2 | — | 07:00–17:00 | non desservi | — |
| CCT-086 | 12.37396, -1.47975 | Arrondissement 9 — Nord | 2,5 | 3,57 | 72 % | 1 | lundi, jeudi | 07:00–17:00 | BF-07 r1 | 07:34 |
| P001 | 12.39049, -1.45628 | Arrondissement 9 — Sud | 2,5 | 2,72 | 54 % | 1 | lundi, jeudi | 07:00–17:00 | BF-01 r2 | 08:54 |
| P002 | 12.40172, -1.44342 | Arrondissement 9 — Sud | 2,5 | 6,15 | 123 % | 2 | lundi, jeudi | 07:00–17:00 | BF-05 r1 | 07:00 |
| P003 | 12.37863, -1.44618 | Arrondissement 9 — Sud | 2,5 | 3,21 | 64 % | 1 | — | 07:00–17:00 | non desservi | — |
| P004 | 12.39702, -1.46826 | Arrondissement 9 — Nord | 2,5 | 3,17 | 63 % | 1 | lundi, jeudi | 07:00–17:00 | BF-07 r2 | 09:08 |
| P005 | 12.40127, -1.46081 | Arrondissement 9 — Sud | 2,5 | 6,25 | 125 % | 2 | lundi, jeudi | 07:00–17:00 | BF-04 r1 | 07:25 |
| P006 | 12.40397, -1.48350 | Arrondissement 9 — Nord | 2,5 | 2,94 | 59 % | 2 | lundi, jeudi | 07:00–17:00 | BF-02 r2 | 09:03 |
| P007 | 12.37432, -1.45793 | Arrondissement 9 — Sud | 2,5 | 6,69 | 134 % | 2 | — | 07:00–17:00 | non desservi | — |
| P008 | 12.37517, -1.48757 | Arrondissement 9 — Nord | 2,5 | 5,53 | 111 % | 3 | lundi, jeudi | 07:00–17:00 | BF-07 r1 | 07:11 |
| P009 | 12.38780, -1.47093 | Arrondissement 9 — Nord | 2,5 | 8,11 | 162 % | 3 | lundi, jeudi | 07:00–17:00 | BF-06 r1 | 08:06 |
| P010 | 12.40397, -1.47498 | Arrondissement 9 — Nord | 2,5 | 5,43 | 108 % | 2 | lundi, jeudi | 07:00–17:00 | BF-03 r2 | 08:45 |
| P011 | 12.40127, -1.49014 | Arrondissement 9 — Nord | 2,5 | 5,96 | 119 % | 2 | lundi, jeudi | 07:00–17:00 | BF-02 r2 | 08:40 |
| P012 | 12.38949, -1.47653 | Arrondissement 9 — Nord | 2,5 | 4,89 | 98 % | 1 | lundi, jeudi | 07:00–17:00 | BF-02 r1 | 07:00 |
| P013 | 12.38241, -1.45901 | Arrondissement 9 — Sud | 2,5 | 5,41 | 108 % | 2 | lundi, jeudi | 07:00–17:00 | BF-08 r1 | 07:23 |
| P014 | 12.39738, -1.47377 | Arrondissement 9 — Nord | 2,5 | 6,19 | 124 % | 2 | lundi, jeudi | 07:00–17:00 | BF-06 r2 | 10:01 |
| P015 | 12.39415, -1.44894 | Arrondissement 9 — Sud | 2,5 | 7,89 | 158 % | 3 | lundi, jeudi | 07:00–17:00 | BF-05 r1 | 07:24 |
| P016 | 12.38241, -1.47820 | Arrondissement 9 — Nord | 2,5 | 4,67 | 93 % | 1 | lundi, jeudi | 07:00–17:00 | BF-02 r1 | 07:12 |
| P017 | 12.40666, -1.44741 | Arrondissement 9 — Sud | 2,5 | 3,99 | 80 % | 1 | lundi, jeudi | 07:00–17:00 | BF-01 r1 | 07:00 |
| P018 | 12.37432, -1.44171 | Arrondissement 9 — Sud | 2,5 | 3,52 | 70 % | 1 | — | 07:00–17:00 | non desservi | — |
| P019 | 12.37303, -1.46550 | Arrondissement 9 — Sud | 2,5 | 4,53 | 91 % | 1 | — | 07:00–17:00 | non desservi | — |
| P020 | 12.39858, -1.48880 | Arrondissement 9 — Nord | 2,5 | 2,92 | 58 % | 1 | lundi, jeudi | 07:00–17:00 | BF-08 r2 | 09:56 |
| P021 | 12.37702, -1.45042 | Arrondissement 9 — Sud | 2,5 | 3,95 | 79 % | 1 | — | 07:00–17:00 | non desservi | — |
| P022 | 12.37432, -1.47603 | Arrondissement 9 — Nord | 2,5 | 6,32 | 126 % | 2 | — | 07:00–17:00 | non desservi | — |
| P023 | 12.37971, -1.47978 | Arrondissement 9 — Nord | 2,5 | 5,13 | 102 % | 2 | lundi, jeudi | 07:00–17:00 | BF-07 r1 | 07:47 |
| P024 | 12.39438, -1.45446 | Arrondissement 9 — Sud | 2,5 | 9,72 | 194 % | 3 | lundi, jeudi | 07:00–17:00 | BF-01 r2 | 08:43 |
| P025 | 12.39319, -1.47295 | Arrondissement 9 — Nord | 2,5 | 3,67 | 73 % | 1 | lundi, jeudi | 07:00–17:00 | BF-06 r2 | 09:49 |
| P026 | 12.37506, -1.44618 | Arrondissement 9 — Sud | 2,5 | 5,93 | 119 % | 2 | — | 07:00–17:00 | non desservi | — |
| P027 | 12.38387, -1.45446 | Arrondissement 9 — Sud | 2,5 | 6,23 | 125 % | 2 | lundi, jeudi | 07:00–17:00 | BF-08 r1 | 07:12 |
| P028 | 12.38423, -1.47377 | Arrondissement 9 — Nord | 2,5 | 6,30 | 126 % | 2 | lundi, jeudi | 07:00–17:00 | BF-06 r1 | 07:54 |
| P029 | 12.39858, -1.46506 | Arrondissement 9 — Sud | 2,5 | 4,52 | 90 % | 1 | lundi, jeudi | 07:00–17:00 | BF-04 r1 | 07:00 |
| P030 | 12.40666, -1.46459 | Arrondissement 9 — Sud | 2,5 | 4,32 | 86 % | 2 | lundi, jeudi | 07:00–17:00 | BF-03 r1 | 07:00 |
| P031 | 12.40223, -1.49309 | Arrondissement 9 — Nord | 2,5 | 3,73 | 75 % | 1 | lundi, jeudi | 07:00–17:00 | BF-02 r2 | 08:29 |
| P032 | 12.39962, -1.48205 | Arrondissement 9 — Nord | 2,5 | 4,30 | 86 % | 1 | lundi, jeudi | 07:00–17:00 | BF-04 r2 | 09:19 |
| P033 | 12.39049, -1.48590 | Arrondissement 9 — Nord | 2,5 | 3,67 | 73 % | 1 | lundi, jeudi | 07:00–17:00 | BF-08 r2 | 09:43 |
| P034 | 12.37777, -1.46826 | Arrondissement 9 — Sud | 2,5 | 5,46 | 109 % | 2 | — | 07:00–17:00 | non desservi | — |
| P035 | 12.37632, -1.48205 | Arrondissement 9 — Nord | 2,5 | 7,63 | 152 % | 2 | lundi, jeudi | 07:00–17:00 | BF-07 r1 | 07:23 |
| P036 | 12.38638, -1.45998 | Arrondissement 9 — Sud | 2,5 | 6,42 | 128 % | 2 | lundi, jeudi | 07:00–17:00 | BF-08 r1 | 07:35 |
| P037 | 12.39804, -1.45722 | Arrondissement 9 — Sud | 2,5 | 2,88 | 58 % | 1 | lundi, jeudi | 07:00–17:00 | BF-01 r2 | 09:07 |
| P038 | 12.40166, -1.47653 | Arrondissement 9 — Nord | 2,5 | 6,13 | 123 % | 2 | lundi, jeudi | 07:00–17:00 | BF-03 r2 | 08:56 |
| P039 | 12.39049, -1.49085 | Arrondissement 9 — Nord | 2,5 | 3,83 | 77 % | 1 | lundi, jeudi | 07:00–17:00 | BF-08 r2 | 08:57 |
| P040 | 12.38628, -1.47929 | Arrondissement 9 — Nord | 2,5 | 5,47 | 109 % | 2 | lundi, jeudi | 07:00–17:00 | BF-02 r1 | 07:24 |
| P041 | 12.39858, -1.48654 | Arrondissement 9 — Nord | 2,5 | 3,37 | 67 % | 1 | lundi, jeudi | 07:00–17:00 | BF-05 r2 | 08:33 |
| P042 | 12.38446, -1.44894 | Arrondissement 9 — Sud | 2,5 | 3,21 | 64 % | 1 | lundi, jeudi | 07:00–17:00 | BF-08 r1 | 07:00 |
| P043 | 12.38780, -1.44150 | Arrondissement 9 — Sud | 2,5 | 3,56 | 71 % | 1 | — | 07:00–17:00 | non desservi | — |
| P044 | 12.40397, -1.44208 | Arrondissement 9 — Sud | 2,5 | 5,78 | 116 % | 2 | lundi, jeudi | 07:00–17:00 | BF-03 r1 | 07:39 |
| P045 | 12.40666, -1.45815 | Arrondissement 9 — Sud | 2,5 | 5,77 | 115 % | 2 | lundi, jeudi | 07:00–17:00 | BF-01 r1 | 07:24 |
| P046 | 12.40455, -1.45170 | Arrondissement 9 — Sud | 2,5 | 6,86 | 137 % | 2 | lundi, jeudi | 07:00–17:00 | BF-01 r1 | 07:11 |
| P047 | 12.40127, -1.44739 | Arrondissement 9 — Sud | 2,5 | 3,62 | 72 % | 1 | lundi, jeudi | 07:00–17:00 | BF-03 r1 | 07:26 |
| P048 | 12.39936, -1.45170 | Arrondissement 9 — Sud | 2,5 | 2,65 | 53 % | 1 | lundi, jeudi | 07:00–17:00 | BF-03 r1 | 07:15 |
| P049 | 12.39661, -1.44342 | Arrondissement 9 — Sud | 2,5 | 6,86 | 137 % | 2 | lundi, jeudi | 07:00–17:00 | BF-05 r1 | 07:11 |
| P050 | 12.39143, -1.44342 | Arrondissement 9 — Sud | 2,5 | 8,37 | 167 % | 2 | — | 07:00–17:00 | non desservi | — |
| P051 | 12.39387, -1.45998 | Arrondissement 9 — Sud | 2,5 | 6,58 | 132 % | 2 | lundi, jeudi | 07:00–17:00 | BF-04 r1 | 07:12 |
| P052 | 12.40119, -1.45446 | Arrondissement 9 — Sud | 2,5 | 5,43 | 108 % | 2 | lundi, jeudi | 07:00–17:00 | BF-01 r2 | 08:30 |
| P053 | 12.40397, -1.46846 | Arrondissement 9 — Nord | 2,5 | 4,22 | 84 % | 2 | lundi, jeudi | 07:00–17:00 | BF-04 r2 | 08:29 |
| P054 | 12.40150, -1.47101 | Arrondissement 9 — Nord | 2,5 | 7,12 | 142 % | 2 | lundi, jeudi | 07:00–17:00 | BF-07 r2 | 08:56 |
| P055 | 12.40397, -1.47877 | Arrondissement 9 — Nord | 2,5 | 4,69 | 94 % | 2 | lundi, jeudi | 07:00–17:00 | BF-03 r2 | 09:07 |
| P056 | 12.40397, -1.48685 | Arrondissement 9 — Nord | 2,5 | 4,00 | 80 % | 1 | lundi, jeudi | 07:00–17:00 | BF-02 r2 | 08:52 |
| P057 | 12.39783, -1.49309 | Arrondissement 9 — Nord | 2,5 | 1,79 | 36 % | 1 | lundi, jeudi | 07:00–17:00 | BF-05 r2 | 09:08 |
| P058 | 12.39417, -1.49033 | Arrondissement 9 — Nord | 2,5 | 7,71 | 154 % | 2 | lundi, jeudi | 07:00–17:00 | BF-05 r2 | 08:56 |
| P059 | 12.39417, -1.48481 | Arrondissement 9 — Nord | 2,5 | 7,08 | 142 % | 2 | lundi, jeudi | 07:00–17:00 | BF-05 r2 | 08:44 |
| P060 | 12.39319, -1.47743 | Arrondissement 9 — Nord | 2,5 | 4,24 | 85 % | 1 | lundi, jeudi | 07:00–17:00 | BF-06 r2 | 09:38 |
| P061 | 12.39692, -1.47929 | Arrondissement 9 — Nord | 2,5 | 5,12 | 102 % | 1 | lundi, jeudi | 07:00–17:00 | BF-06 r2 | 09:15 |
| P062 | 12.38780, -1.48864 | Arrondissement 9 — Nord | 2,5 | 4,82 | 96 % | 1 | lundi, jeudi | 07:00–17:00 | BF-08 r2 | 09:19 |
| P063 | 12.38780, -1.49133 | Arrondissement 9 — Nord | 2,5 | 3,75 | 75 % | 1 | lundi, jeudi | 07:00–17:00 | BF-08 r2 | 09:08 |
| P064 | 12.38510, -1.48550 | Arrondissement 9 — Nord | 2,5 | 6,02 | 120 % | 2 | lundi, jeudi | 07:00–17:00 | BF-08 r2 | 09:31 |
| P065 | 12.38014, -1.48757 | Arrondissement 9 — Nord | 2,5 | 6,38 | 128 % | 2 | lundi, jeudi | 07:00–17:00 | BF-07 r1 | 07:00 |
| P066 | 12.37892, -1.47377 | Arrondissement 9 — Nord | 2,5 | 6,95 | 139 % | 2 | — | 07:00–17:00 | non desservi | — |
| P067 | 12.37702, -1.46308 | Arrondissement 9 — Sud | 2,5 | 2,31 | 46 % | 1 | lundi, jeudi | 07:00–17:00 | BF-04 r2 | 08:59 |
| P068 | 12.37702, -1.46084 | Arrondissement 9 — Sud | 2,5 | 4,26 | 85 % | 1 | lundi, jeudi | 07:00–17:00 | BF-06 r1 | 07:29 |
| P069 | 12.38241, -1.46398 | Arrondissement 9 — Sud | 2,5 | 7,02 | 140 % | 2 | lundi, jeudi | 07:00–17:00 | BF-04 r2 | 08:47 |
| P070 | 12.38197, -1.46826 | Arrondissement 9 — Sud | 2,5 | 7,57 | 151 % | 2 | lundi, jeudi | 07:00–17:00 | BF-06 r1 | 07:42 |
| P071 | 12.38685, -1.46550 | Arrondissement 9 — Sud | 2,5 | 4,60 | 92 % | 2 | lundi, jeudi | 07:00–17:00 | BF-07 r2 | 09:42 |
| P072 | 12.39049, -1.46712 | Arrondissement 9 — Sud | 2,5 | 1,83 | 37 % | 1 | lundi, jeudi | 07:00–17:00 | BF-07 r2 | 09:31 |
| P073 | 12.38960, -1.46274 | Arrondissement 9 — Sud | 2,5 | 4,92 | 98 % | 2 | lundi, jeudi | 07:00–17:00 | BF-08 r1 | 07:46 |
| P074 | 12.38838, -1.45170 | Arrondissement 9 — Sud | 2,5 | 6,09 | 122 % | 2 | — | 07:00–17:00 | non desservi | — |
| P075 | 12.38780, -1.44694 | Arrondissement 9 — Sud | 2,5 | 2,69 | 54 % | 1 | lundi, jeudi | 07:00–17:00 | BF-06 r1 | 07:00 |
| P076 | 12.38510, -1.44380 | Arrondissement 9 — Sud | 2,5 | 3,51 | 70 % | 1 | — | 07:00–17:00 | non desservi | — |
| P077 | 12.38319, -1.44342 | Arrondissement 9 — Sud | 2,5 | 6,19 | 124 % | 2 | — | 07:00–17:00 | non desservi | — |
| P078 | 12.37971, -1.44066 | Arrondissement 9 — Sud | 2,5 | 7,21 | 144 % | 2 | — | 07:00–17:00 | non desservi | — |
| P079 | 12.38166, -1.44894 | Arrondissement 9 — Sud | 2,5 | 3,66 | 73 % | 1 | — | 07:00–17:00 | non desservi | — |
| P080 | 12.37312, -1.45170 | Arrondissement 9 — Sud | 2,5 | 1,82 | 36 % | 1 | lundi, jeudi | 07:00–17:00 | BF-06 r1 | 07:15 |
| P081 | 12.37432, -1.45322 | Arrondissement 9 — Sud | 2,5 | 4,70 | 94 % | 1 | — | 07:00–17:00 | non desservi | — |
| P082 | 12.37432, -1.47026 | Arrondissement 9 — Nord | 2,5 | 5,63 | 113 % | 2 | — | 07:00–17:00 | non desservi | — |

## Coûts et personnel

- Coût par jour d'enlèvement : 382 833 FCFA, soit ~3 317 886 FCFA par mois (2.0 enlèvements par semaine).
- Personnel par jour d'enlèvement : 8 chauffeur(s) et 16 ripeur(s) (hypothèse : un chauffeur et deux ripeurs par camion).

## Indicateurs simulés (90 jours)

| Indicateur | Référence | 2 camions en panne | Saison des pluies | Abonnements +20 % | Budget −30 % | Pluies + 2 camions en panne |
|---|---|---|---|---|---|---|
| Tonnes collectées par camion | 3 323,1 [3 260,4 ; 3 388,7] | 2 606,8 [2 544,0 ; 2 652,2] | 3 362,8 [3 258,6 ; 3 435,2] | 3 305,0 [3 215,9 ; 3 356,3] | 3 323,1 [3 260,4 ; 3 388,7] | 2 636,2 [2 565,5 ; 2 668,8] |
| Tonnes pré-collectées | 311,6 [311,5 ; 311,6] | 311,6 [311,5 ; 311,6] | 311,7 [311,6 ; 311,8] | 311,7 [311,7 ; 311,8] | 311,6 [311,5 ; 311,6] | 311,7 [311,6 ; 311,8] |
| Tonnes en dépôt sauvage | 2 172,9 [2 119,3 ; 2 236,5] | 2 859,3 [2 835,0 ; 2 923,7] | 2 960,8 [2 880,4 ; 3 043,9] | 2 190,6 [2 139,8 ; 2 259,9] | 2 172,9 [2 119,3 ; 2 236,5] | 3 661,9 [3 630,2 ; 3 744,4] |
| Dépotoirs actifs (moyenne) | 114,3 [107,7 ; 124,0] | 122,4 [114,3 ; 132,2] | 124,1 [117,7 ; 130,7] | 114,9 [107,9 ; 120,5] | 114,3 [107,7 ; 124,0] | 126,8 [119,7 ; 133,9] |
| Couverture simulée* (%) | 59 [58 ; 60] | 49 [48 ; 50] | 53 [52 ; 54] | 58 [57 ; 59] | 59 [58 ; 60] | 45 [43 ; 45] |
| Taux d'abonnement final (%) | 26 [26 ; 27] | 26 [26 ; 27] | 26 [25 ; 26] | 29 [29 ; 30] | 26 [26 ; 27] | 25 [25 ; 26] |
| Pré-collecteurs actifs (fin) | 10 [10 ; 10] | 10 [10 ; 10] | 10 [10 ; 10] | 10 [10 ; 10] | 10 [10 ; 10] | 10 [10 ; 10] |
| Coût de la mairie (FCFA/t) | 2 802 [2 777 ; 2 818] | 2 678 [2 655 ; 2 693] | 2 904 [2 880 ; 2 920] | 2 808 [2 788 ; 2 831] | 2 802 [2 777 ; 2 818] | 2 794 [2 767 ; 2 808] |
| Jours-points en débordement | 2 357 [2 273 ; 2 448] | 3 270 [3 206 ; 3 364] | 2 854 [2 754 ; 2 973] | 2 392 [2 318 ; 2 523] | 2 357 [2 273 ; 2 448] | 3 677 [3 650 ; 3 802] |

\* Part de la population servie un jour donné : point à portée de marche **et pas plein**, ou passage du pré-collecteur dans les 7 jours. Plus stricte que la couverture du plan (distance seule).

## Risques

- **Pannes** : avec 2 camions en moins, 32 points ne sont pas desservis (19 en référence) ; aucun point ne bouge (points inchangés : 100 %), mais les tournées sont refaites (camions sur les mêmes points : 8 %). Prévoir un camion de réserve ou une rotation supplémentaire.
- **Budget** : le plan coûte ~3 317 886 FCFA par mois en camions, sous le budget même réduit de 30 % (17 500 000 FCFA) : la variante « Budget −30 % » donne donc exactement la référence. Le budget ne limite les tournées que s'il descend sous ce coût (ou si la valeur de départ de la mairie est bien plus basse que celle de démonstration).
- **Pré-collecte** : la charrette est le goulot (`SIMULATION_ODD.md` § 11) ; plus d'abonnés sans plus de pré-collecteurs n'augmente pas la pré-collecte.
- **Données** : la quantité de déchets par habitant explique ~90 % de l'incertitude sur les dépôts (`SIMULATION_SENSIBILITE.md`) ; la mesurer par pesée dans l'arrondissement avant de dimensionner.

## Saison des pluies

- Demande +15 % (508,1 t/semaine) et vitesses réduites : 480,4 km, 404 598 FCFA par jour d'enlèvement, 22 point(s) non desservi(s), 16 tournée(s).
- Avant les pluies : curer les caniveaux près des points, déplacer hors des zones inondables les bacs signalés « près de l'eau », vider les dépotoirs proches des cours d'eau en priorité (règle de nettoyage du plan).
- Pendant : ajouter une rotation les jours après une forte pluie, garder un camion en réserve, renforcer les descentes Laabal dans les îlots récurrents en même temps que des rotations de camions (sinon les points débordent).

## Indicateurs de suivi pour la mairie

Chaque mois, comparer à la valeur simulée de référence (colonne « Référence ») ; un écart qui sort de l'intervalle à 90 % appelle une explication.

| Indicateur | Comment le mesurer | Fréquence | Valeur simulée (référence) | Alerte si |
|---|---|---|---|---|
| Tonnes collectées par camion | bons de pesée au CET | mensuelle | 3 323,1 [3 260,4 ; 3 388,7] t / 90 j | sous le 5ᵉ centile |
| Tonnes en dépôt sauvage | signalements vérifiés × volume (Salubri Map) | mensuelle | 2 172,9 [2 119,3 ; 2 236,5] t / 90 j | au-dessus du 95ᵉ centile |
| Dépotoirs récurrents | Salubri Map, filtre « récurrent » | mensuelle | 70,5 [67,5 ; 77,5] | en hausse 2 mois de suite |
| Points en débordement | photos des chefs de point / signalements « point plein » | hebdomadaire | 2 357 [2 273 ; 2 448] jours-points / 90 j | un même point 2 semaines de suite |
| Taux d'abonnement à la pré-collecte | registres des associations | trimestrielle | 26 [26 ; 27] % | baisse de plus de 5 points |
| Coût par tonne | comptabilité (carburant, salaires, entretien) | mensuelle | 2 802 [2 777 ; 2 818] FCFA/t | au-dessus du 95ᵉ centile |
| Tournées faites / prévues | fiches de tournée signées | hebdomadaire | 100 % prévu | sous 90 % |

<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Plan de collecte — Arrondissement 9 de Ouagadougou

Généré par `scripts/plan_arrondissement.py --arrondissement 9` le 2026-11-18, plan v2 du scénario « Arrondissement 9 » ; simulations du modèle à agents, 30 réplications par variante, médiane [intervalle à 90 %]. Ne pas modifier à la main : relancer le script.

> **Limites de démonstration.** Les limites des quartiers de cet arrondissement viennent du jeu de démonstration (`quartiers.geojson`, `source: demo`) : Arrondissement 9 — Nord (157 047 hab.), Arrondissement 9 — Sud (179 436 hab.). Remplacer par les limites des secteurs avant tout usage opérationnel, puis relancer.

> **Population** : 336 483 habitants, total de l'arrondissement au recensement de 2019 (INSD, RGPH 2019, monographie de la commune de Ouagadougou, tableau 2.2), réparti entre les quartiers au prorata du jeu de démonstration. Le total est réel ; la répartition interne et les limites ne le sont pas (les limites des secteurs 37 à 40 ne sont pas en données ouvertes) : **à faire par l'équipe**, demander la carte des secteurs à la mairie d'arrondissement et la charger dans `quartiers.geojson`.

## En bref

- **Population couverte** : 336 483 habitants ; **demande** 1 413,2 t/semaine.
- **270 points de regroupement** (capacité 2,5 t), couverture à 300 m de marche : 100 % de la population.
- **8 camion(s)** (BF-01, BF-02, BF-03, BF-04, BF-05, BF-06, BF-07, BF-08), 16 tournée(s) par jour d'enlèvement (lundi, mercredi, vendredi), 419,9 km, **375 345 FCFA** par jour d'enlèvement.
- Points non desservis : 172 ; camions nécessaires pour tout desservir : 25 (disponibles : 8).

![Carte des points et des tournées](figures/plan_arr9_carte.svg)

## Capacité des points et flotte

- **Capacité par enlèvement** (contrainte du placement) : 3 enlèvement(s) par semaine (demandé : 2) ; 18 point(s) débordent encore, 22,0 t/semaine non collectées : CCT-078, CCT-080, CCT-084, CCT-086, P006, P021, P061, P080, P102, P119, P123, P125, P174, P180, P189, P219, P245, P247.

Flotte nécessaire : 22 camion(s) de 8 t de plus (le nombre estimé par le plan, puis un à la fois) jusqu'à ce que tous les points soient desservis (simulation : 30 réplications, médiane [intervalle à 90 %], 90 jours). La flotte actuelle est simulée avec le budget de l'arrondissement ; la flotte nécessaire avec le budget qu'elle demande (coût mensuel + 10 %) : c'est le montant à prévoir pour desservir tout l'arrondissement.

| Flotte | Camions | Points non desservis | Tonnes non enlevées par enlèvement | Coût par jour (FCFA) | Coût par mois (FCFA) | Budget simulé (FCFA/mois) | Dépôts sauvages simulés (t) | Couverture simulée (%) |
|---|---|---|---|---|---|---|---|---|
| Flotte actuelle | 8 | 172 | 314,9 | 375 345 | 4 879 485 | 3 482 877 | 13 082,2 [13 043,0 ; 13 128,1] | 50 [50 ; 50] |
| Flotte nécessaire | 30 | 0 | 0,0 | 1 282 255 | 16 669 315 | 18 336 246 | 1 117,1 [972,4 ; 1 262,4] | 95 [94 ; 95] |

## Tournées (par jour d'enlèvement)

| Camion | Rotation | Jours | 1er passage | Dernier passage | Points | Tonnage (t) | km | Coût (FCFA) |
|---|---|---|---|---|---|---|---|---|
| BF-01 | 1 | lundi, mercredi, vendredi | 07:00 | 08:11 | 7 | 7,9 | 33,1 | 34 905 |
| BF-01 | 2 | lundi, mercredi, vendredi | 09:15 | 10:11 | 6 | 7,8 | 23,4 | 10 508 |
| BF-02 | 1 | lundi, mercredi, vendredi | 07:00 | 08:00 | 6 | 7,7 | 27,7 | 32 468 |
| BF-02 | 2 | lundi, mercredi, vendredi | 09:11 | 09:56 | 5 | 8,0 | 27,1 | 12 203 |
| BF-03 | 1 | lundi, mercredi, vendredi | 07:00 | 07:46 | 5 | 7,9 | 24,7 | 31 116 |
| BF-03 | 2 | lundi, mercredi, vendredi | 08:53 | 09:40 | 5 | 7,8 | 27,1 | 12 212 |
| BF-04 | 1 | lundi, mercredi, vendredi | 07:00 | 07:44 | 5 | 8,0 | 25,9 | 31 665 |
| BF-04 | 2 | lundi, mercredi, vendredi | 08:50 | 09:33 | 5 | 7,7 | 23,1 | 10 400 |
| BF-05 | 1 | lundi, mercredi, vendredi | 07:00 | 07:32 | 4 | 8,0 | 22,0 | 29 896 |
| BF-05 | 2 | lundi, mercredi, vendredi | 08:34 | 09:19 | 5 | 7,9 | 23,2 | 10 448 |
| BF-06 | 1 | lundi, mercredi, vendredi | 07:00 | 08:37 | 9 | 11,7 | 34,5 | 42 914 |
| BF-06 | 2 | lundi, mercredi, vendredi | 09:47 | 10:52 | 7 | 11,9 | 23,8 | 12 390 |
| BF-07 | 1 | lundi, mercredi, vendredi | 07:00 | 08:05 | 7 | 11,5 | 25,8 | 38 394 |
| BF-07 | 2 | lundi, mercredi, vendredi | 09:10 | 10:19 | 7 | 11,9 | 26,1 | 13 593 |
| BF-08 | 1 | lundi, mercredi, vendredi | 05:30 | 07:45 | 7 | 11,4 | 26,5 | 38 770 |
| BF-08 | 2 | lundi, mercredi, vendredi | 08:51 | 10:08 | 8 | 11,8 | 25,9 | 13 463 |

## Points de regroupement

| Point | Position (lat, lon) | Quartier servi | Capacité (t) | Demande (t/sem.) | Remplissage par enlèvement | Îlots | Jours d'enlèvement | Créneau | Camion | Passage |
|---|---|---|---|---|---|---|---|---|---|---|
| CCT-078 | 12.39468, -1.46454 | Arrondissement 9 — Sud | 2,5 | 10,22 | 136 % | 19 | — | 07:00–17:00 | non desservi | — |
| CCT-079 | 12.39261, -1.46783 | Arrondissement 9 — Sud | 2,5 | 5,99 | 80 % | 11 | lundi, mercredi, vendredi | 07:00–17:00 | BF-02 r2 | 09:33 |
| CCT-080 | 12.39177, -1.48015 | Arrondissement 9 — Nord | 2,5 | 9,53 | 127 % | 11 | lundi, mercredi, vendredi | 07:00–17:00 | BF-08 r1 | 07:33 |
| CCT-084 | 12.38024, -1.45478 | Arrondissement 9 — Sud | 2,5 | 10,79 | 144 % | 21 | — | 07:00–17:00 | non desservi | — |
| CCT-086 | 12.37396, -1.47975 | Arrondissement 9 — Nord | 2,5 | 12,29 | 164 % | 18 | — | 07:00–17:00 | non desservi | — |
| P001 | 12.38298, -1.49092 | Arrondissement 9 — Nord | 2,5 | 6,50 | 87 % | 6 | — | 07:00–17:00 | non desservi | — |
| P002 | 12.38780, -1.45180 | Arrondissement 9 — Sud | 2,5 | 5,09 | 68 % | 10 | — | 07:00–17:00 | non desservi | — |
| P003 | 12.39784, -1.47422 | Arrondissement 9 — Nord | 2,5 | 5,31 | 71 % | 8 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r2 | 10:30 |
| P004 | 12.37522, -1.46097 | Arrondissement 9 — Sud | 2,5 | 3,87 | 52 % | 10 | — | 05:00–08:00 | non desservi | — |
| P005 | 12.40384, -1.45666 | Arrondissement 9 — Sud | 2,5 | 4,85 | 65 % | 8 | lundi, mercredi, vendredi | 07:00–17:00 | BF-03 r1 | 07:13 |
| P006 | 12.37897, -1.47537 | Arrondissement 9 — Nord | 2,5 | 7,84 | 105 % | 11 | — | 07:00–17:00 | non desservi | — |
| P007 | 12.38723, -1.47211 | Arrondissement 9 — Nord | 2,5 | 6,55 | 87 % | 12 | — | 07:00–17:00 | non desservi | — |
| P008 | 12.39260, -1.44236 | Arrondissement 9 — Sud | 2,5 | 5,51 | 74 % | 18 | — | 07:00–17:00 | non desservi | — |
| P009 | 12.37341, -1.44056 | Arrondissement 9 — Sud | 2,5 | 2,44 | 32 % | 8 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r1 | 07:59 |
| P010 | 12.39987, -1.45877 | Arrondissement 9 — Sud | 2,5 | 3,86 | 52 % | 10 | lundi, mercredi, vendredi | 07:00–17:00 | BF-01 r1 | 08:11 |
| P011 | 12.37688, -1.48475 | Arrondissement 9 — Nord | 2,5 | 6,18 | 82 % | 12 | — | 07:00–17:00 | non desservi | — |
| P012 | 12.40596, -1.46752 | Arrondissement 9 — Nord | 2,5 | 6,29 | 84 % | 11 | — | 07:00–17:00 | non desservi | — |
| P013 | 12.40318, -1.45095 | Arrondissement 9 — Sud | 2,5 | 4,65 | 62 % | 15 | — | 07:00–17:00 | non desservi | — |
| P014 | 12.40117, -1.48217 | Arrondissement 9 — Nord | 2,5 | 4,82 | 64 % | 8 | lundi, mercredi, vendredi | 07:00–17:00 | BF-01 r2 | 09:36 |
| P015 | 12.38692, -1.46321 | Arrondissement 9 — Sud | 2,5 | 5,04 | 67 % | 14 | — | 07:00–17:00 | non desservi | — |
| P016 | 12.37770, -1.44707 | Arrondissement 9 — Sud | 2,5 | 4,58 | 61 % | 16 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r1 | 08:12 |
| P017 | 12.38645, -1.48191 | Arrondissement 9 — Nord | 2,5 | 6,58 | 88 % | 10 | lundi, mercredi, vendredi | 07:00–17:00 | BF-04 r1 | 07:33 |
| P018 | 12.37268, -1.47138 | Arrondissement 9 — Nord | 2,5 | 6,57 | 88 % | 10 | — | 07:00–17:00 | non desservi | — |
| P019 | 12.39524, -1.45510 | Arrondissement 9 — Sud | 2,5 | 4,21 | 56 % | 9 | lundi, mercredi, vendredi | 07:00–17:00 | BF-01 r1 | 07:59 |
| P020 | 12.38276, -1.44180 | Arrondissement 9 — Sud | 2,5 | 7,43 | 99 % | 21 | — | 07:00–17:00 | non desservi | — |
| P021 | 12.39376, -1.48306 | Arrondissement 9 — Nord | 2,5 | 9,00 | 120 % | 14 | lundi, mercredi, vendredi | 07:00–17:00 | BF-07 r2 | 09:33 |
| P022 | 12.37633, -1.47069 | Arrondissement 9 — Nord | 2,5 | 7,00 | 93 % | 9 | — | 07:00–17:00 | non desservi | — |
| P023 | 12.40440, -1.44127 | Arrondissement 9 — Sud | 2,5 | 4,27 | 57 % | 11 | — | 07:00–17:00 | non desservi | — |
| P024 | 12.37649, -1.48756 | Arrondissement 9 — Nord | 2,5 | 6,61 | 88 % | 9 | — | 07:00–17:00 | non desservi | — |
| P025 | 12.37806, -1.46434 | Arrondissement 9 — Sud | 2,5 | 6,61 | 88 % | 15 | — | 07:00–17:00 | non desservi | — |
| P026 | 12.40557, -1.47716 | Arrondissement 9 — Nord | 2,5 | 4,29 | 57 % | 3 | lundi, mercredi, vendredi | 07:00–17:00 | BF-05 r2 | 09:19 |
| P027 | 12.40194, -1.46453 | Arrondissement 9 — Sud | 2,5 | 6,50 | 87 % | 10 | — | 07:00–17:00 | non desservi | — |
| P028 | 12.37417, -1.45206 | Arrondissement 9 — Sud | 2,5 | 3,48 | 46 % | 17 | — | 07:00–17:00 | non desservi | — |
| P029 | 12.38947, -1.46045 | Arrondissement 9 — Sud | 2,5 | 4,65 | 62 % | 9 | — | 07:00–17:00 | non desservi | — |
| P030 | 12.39977, -1.44211 | Arrondissement 9 — Sud | 2,5 | 3,21 | 43 % | 5 | lundi, mercredi, vendredi | 07:00–17:00 | BF-03 r2 | 09:06 |
| P031 | 12.39239, -1.47521 | Arrondissement 9 — Nord | 2,5 | 5,64 | 75 % | 10 | lundi, mercredi, vendredi | 07:00–17:00 | BF-07 r1 | 07:54 |
| P032 | 12.39872, -1.46642 | Arrondissement 9 — Sud | 2,5 | 6,75 | 90 % | 13 | — | 05:00–08:00 | non desservi | — |
| P033 | 12.40327, -1.49330 | Arrondissement 9 — Nord | 2,5 | 2,90 | 39 % | 5 | lundi, mercredi, vendredi | 07:00–17:00 | BF-01 r2 | 10:11 |
| P034 | 12.39134, -1.44554 | Arrondissement 9 — Sud | 2,5 | 5,44 | 72 % | 17 | — | 07:00–17:00 | non desservi | — |
| P035 | 12.38275, -1.45835 | Arrondissement 9 — Sud | 2,5 | 5,27 | 70 % | 8 | — | 07:00–17:00 | non desservi | — |
| P036 | 12.38463, -1.44798 | Arrondissement 9 — Sud | 2,5 | 5,24 | 70 % | 25 | — | 07:00–17:00 | non desservi | — |
| P037 | 12.38336, -1.46920 | Arrondissement 9 — Nord | 2,5 | 4,77 | 64 % | 8 | — | 07:00–17:00 | non desservi | — |
| P038 | 12.40566, -1.47216 | Arrondissement 9 — Nord | 2,5 | 7,42 | 99 % | 11 | lundi, mercredi, vendredi | 07:00–17:00 | BF-05 r1 | 07:32 |
| P039 | 12.40410, -1.44852 | Arrondissement 9 — Sud | 2,5 | 5,26 | 70 % | 13 | — | 07:00–17:00 | non desservi | — |
| P040 | 12.40650, -1.46221 | Arrondissement 9 — Sud | 2,5 | 5,88 | 78 % | 14 | lundi, mercredi, vendredi | 07:00–17:00 | BF-04 r2 | 09:33 |
| P041 | 12.37378, -1.45679 | Arrondissement 9 — Sud | 2,5 | 5,91 | 79 % | 18 | — | 07:00–17:00 | non desservi | — |
| P042 | 12.37990, -1.47985 | Arrondissement 9 — Nord | 2,5 | 6,91 | 92 % | 9 | — | 07:00–17:00 | non desservi | — |
| P043 | 12.38807, -1.48482 | Arrondissement 9 — Nord | 2,5 | 3,89 | 52 % | 4 | lundi, mercredi, vendredi | 07:00–17:00 | BF-04 r1 | 07:22 |
| P044 | 12.39540, -1.44731 | Arrondissement 9 — Sud | 2,5 | 3,48 | 46 % | 16 | lundi, mercredi, vendredi | 07:00–17:00 | BF-02 r1 | 07:24 |
| P045 | 12.38002, -1.48505 | Arrondissement 9 — Nord | 2,5 | 7,44 | 99 % | 12 | — | 07:00–17:00 | non desservi | — |
| P046 | 12.40074, -1.47147 | Arrondissement 9 — Nord | 2,5 | 5,22 | 70 % | 9 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r2 | 09:57 |
| P047 | 12.39809, -1.45299 | Arrondissement 9 — Sud | 2,5 | 7,03 | 94 % | 15 | — | 07:00–17:00 | non desservi | — |
| P048 | 12.38867, -1.44091 | Arrondissement 9 — Sud | 2,5 | 4,82 | 64 % | 14 | — | 07:00–17:00 | non desservi | — |
| P049 | 12.39424, -1.45898 | Arrondissement 9 — Sud | 2,5 | 3,87 | 52 % | 5 | lundi, mercredi, vendredi | 07:00–17:00 | BF-08 r2 | 09:24 |
| P050 | 12.39054, -1.45535 | Arrondissement 9 — Sud | 2,5 | 4,86 | 65 % | 14 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r1 | 08:37 |
| P051 | 12.37306, -1.46600 | Arrondissement 9 — Sud | 2,5 | 5,47 | 73 % | 13 | — | 07:00–17:00 | non desservi | — |
| P052 | 12.37284, -1.47574 | Arrondissement 9 — Nord | 2,5 | 5,63 | 75 % | 7 | — | 07:00–17:00 | non desservi | — |
| P053 | 12.38658, -1.45763 | Arrondissement 9 — Sud | 2,5 | 7,18 | 96 % | 13 | — | 07:00–17:00 | non desservi | — |
| P054 | 12.38920, -1.47639 | Arrondissement 9 — Nord | 2,5 | 6,86 | 91 % | 5 | lundi, mercredi, vendredi | 05:00–08:00 | BF-08 r1 | 05:30 |
| P055 | 12.38437, -1.45095 | Arrondissement 9 — Sud | 2,5 | 5,12 | 68 % | 14 | — | 07:00–17:00 | non desservi | — |
| P056 | 12.37812, -1.48881 | Arrondissement 9 — Nord | 2,5 | 5,73 | 76 % | 10 | — | 07:00–17:00 | non desservi | — |
| P057 | 12.38044, -1.44290 | Arrondissement 9 — Sud | 2,5 | 3,05 | 41 % | 10 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r1 | 07:26 |
| P058 | 12.40090, -1.47904 | Arrondissement 9 — Nord | 2,5 | 4,70 | 63 % | 6 | lundi, mercredi, vendredi | 07:00–17:00 | BF-07 r2 | 09:10 |
| P059 | 12.37830, -1.46199 | Arrondissement 9 — Sud | 2,5 | 4,47 | 60 % | 10 | — | 05:00–08:00 | non desservi | — |
| P060 | 12.38891, -1.46686 | Arrondissement 9 — Sud | 2,5 | 4,33 | 58 % | 6 | lundi, mercredi, vendredi | 07:00–17:00 | BF-02 r2 | 09:22 |
| P061 | 12.38757, -1.47852 | Arrondissement 9 — Nord | 2,5 | 8,91 | 119 % | 9 | lundi, mercredi, vendredi | 05:00–08:00 | BF-08 r1 | 07:21 |
| P062 | 12.38250, -1.46394 | Arrondissement 9 — Sud | 2,5 | 5,70 | 76 % | 11 | — | 07:00–17:00 | non desservi | — |
| P063 | 12.38364, -1.47894 | Arrondissement 9 — Nord | 2,5 | 3,42 | 46 % | 5 | — | 07:00–17:00 | non desservi | — |
| P064 | 12.39233, -1.47124 | Arrondissement 9 — Nord | 2,5 | 3,47 | 46 % | 6 | lundi, mercredi, vendredi | 07:00–17:00 | BF-07 r1 | 07:21 |
| P065 | 12.40636, -1.45129 | Arrondissement 9 — Sud | 2,5 | 5,63 | 75 % | 16 | lundi, mercredi, vendredi | 07:00–17:00 | BF-02 r1 | 08:00 |
| P066 | 12.39485, -1.47183 | Arrondissement 9 — Nord | 2,5 | 7,47 | 100 % | 13 | — | 07:00–17:00 | non desservi | — |
| P067 | 12.37460, -1.48501 | Arrondissement 9 — Nord | 2,5 | 6,75 | 90 % | 8 | — | 07:00–17:00 | non desservi | — |
| P068 | 12.37821, -1.45217 | Arrondissement 9 — Sud | 2,5 | 5,96 | 79 % | 19 | — | 07:00–17:00 | non desservi | — |
| P069 | 12.39675, -1.47888 | Arrondissement 9 — Nord | 2,5 | 4,96 | 66 % | 8 | lundi, mercredi, vendredi | 07:00–17:00 | BF-07 r2 | 09:21 |
| P070 | 12.40097, -1.44710 | Arrondissement 9 — Sud | 2,5 | 3,98 | 53 % | 6 | lundi, mercredi, vendredi | 07:00–17:00 | BF-02 r1 | 07:47 |
| P071 | 12.38507, -1.47312 | Arrondissement 9 — Nord | 2,5 | 6,14 | 82 % | 12 | — | 07:00–17:00 | non desservi | — |
| P072 | 12.40334, -1.47085 | Arrondissement 9 — Nord | 2,5 | 6,95 | 93 % | 11 | lundi, mercredi, vendredi | 07:00–17:00 | BF-05 r1 | 07:21 |
| P073 | 12.38057, -1.44725 | Arrondissement 9 — Sud | 2,5 | 3,09 | 41 % | 15 | — | 07:00–17:00 | non desservi | — |
| P074 | 12.37660, -1.45514 | Arrondissement 9 — Sud | 2,5 | 5,82 | 78 % | 13 | — | 07:00–17:00 | non desservi | — |
| P075 | 12.39201, -1.45023 | Arrondissement 9 — Sud | 2,5 | 3,52 | 47 % | 14 | — | 07:00–17:00 | non desservi | — |
| P076 | 12.39140, -1.48400 | Arrondissement 9 — Nord | 2,5 | 5,75 | 77 % | 7 | lundi, mercredi, vendredi | 07:00–17:00 | BF-07 r2 | 09:44 |
| P077 | 12.38044, -1.47632 | Arrondissement 9 — Nord | 2,5 | 5,32 | 71 % | 7 | — | 07:00–17:00 | non desservi | — |
| P078 | 12.37411, -1.48995 | Arrondissement 9 — Nord | 2,5 | 6,45 | 86 % | 11 | — | 07:00–17:00 | non desservi | — |
| P079 | 12.40375, -1.45886 | Arrondissement 9 — Sud | 2,5 | 5,86 | 78 % | 13 | — | 07:00–17:00 | non desservi | — |
| P080 | 12.38229, -1.48493 | Arrondissement 9 — Nord | 2,5 | 8,74 | 116 % | 11 | — | 07:00–17:00 | non desservi | — |
| P081 | 12.38719, -1.49054 | Arrondissement 9 — Nord | 2,5 | 2,81 | 38 % | 6 | — | 07:00–17:00 | non desservi | — |
| P082 | 12.38847, -1.44618 | Arrondissement 9 — Sud | 2,5 | 4,18 | 56 % | 17 | — | 07:00–17:00 | non desservi | — |
| P083 | 12.39603, -1.46817 | Arrondissement 9 — Nord | 2,5 | 6,01 | 80 % | 12 | lundi, mercredi, vendredi | 07:00–17:00 | BF-02 r2 | 09:45 |
| P084 | 12.37392, -1.44620 | Arrondissement 9 — Sud | 2,5 | 4,30 | 57 % | 15 | — | 07:00–17:00 | non desservi | — |
| P085 | 12.39970, -1.47635 | Arrondissement 9 — Nord | 2,5 | 5,90 | 79 % | 13 | lundi, mercredi, vendredi | 07:00–17:00 | BF-05 r2 | 08:56 |
| P086 | 12.37613, -1.45688 | Arrondissement 9 — Sud | 2,5 | 5,04 | 67 % | 10 | — | 07:00–17:00 | non desservi | — |
| P087 | 12.39909, -1.46840 | Arrondissement 9 — Nord | 2,5 | 4,18 | 56 % | 7 | lundi, mercredi, vendredi | 07:00–17:00 | BF-02 r2 | 09:56 |
| P088 | 12.37920, -1.46730 | Arrondissement 9 — Sud | 2,5 | 3,79 | 51 % | 4 | — | 07:00–17:00 | non desservi | — |
| P089 | 12.39799, -1.46021 | Arrondissement 9 — Sud | 2,5 | 3,90 | 52 % | 8 | lundi, mercredi, vendredi | 07:00–17:00 | BF-08 r2 | 09:02 |
| P090 | 12.39797, -1.48226 | Arrondissement 9 — Nord | 2,5 | 2,28 | 30 % | 4 | lundi, mercredi, vendredi | 07:00–17:00 | BF-08 r1 | 07:45 |
| P091 | 12.38514, -1.44502 | Arrondissement 9 — Sud | 2,5 | 5,04 | 67 % | 15 | — | 07:00–17:00 | non desservi | — |
| P092 | 12.40031, -1.45354 | Arrondissement 9 — Sud | 2,5 | 7,00 | 93 % | 16 | — | 07:00–17:00 | non desservi | — |
| P093 | 12.39871, -1.46257 | Arrondissement 9 — Sud | 2,5 | 4,52 | 60 % | 9 | lundi, mercredi, vendredi | 07:00–17:00 | BF-08 r2 | 09:46 |
| P094 | 12.37503, -1.46825 | Arrondissement 9 — Sud | 2,5 | 5,95 | 79 % | 16 | — | 07:00–17:00 | non desservi | — |
| P095 | 12.40323, -1.47516 | Arrondissement 9 — Nord | 2,5 | 3,94 | 53 % | 2 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r2 | 10:52 |
| P096 | 12.38987, -1.47534 | Arrondissement 9 — Nord | 2,5 | 5,13 | 68 % | 8 | lundi, mercredi, vendredi | 07:00–17:00 | BF-07 r1 | 07:43 |
| P097 | 12.39358, -1.48730 | Arrondissement 9 — Nord | 2,5 | 2,96 | 39 % | 5 | lundi, mercredi, vendredi | 07:00–17:00 | BF-04 r1 | 07:00 |
| P098 | 12.40639, -1.44880 | Arrondissement 9 — Sud | 2,5 | 4,92 | 66 % | 10 | lundi, mercredi, vendredi | 07:00–17:00 | BF-03 r2 | 09:40 |
| P099 | 12.39829, -1.45601 | Arrondissement 9 — Sud | 2,5 | 6,45 | 86 % | 12 | — | 05:00–08:00 | non desservi | — |
| P100 | 12.38632, -1.46566 | Arrondissement 9 — Sud | 2,5 | 3,39 | 45 % | 6 | lundi, mercredi, vendredi | 07:00–17:00 | BF-02 r2 | 09:11 |
| P101 | 12.40199, -1.46058 | Arrondissement 9 — Sud | 2,5 | 6,91 | 92 % | 14 | — | 07:00–17:00 | non desservi | — |
| P102 | 12.37756, -1.47988 | Arrondissement 9 — Nord | 2,5 | 7,71 | 103 % | 10 | — | 07:00–17:00 | non desservi | — |
| P103 | 12.37770, -1.44056 | Arrondissement 9 — Sud | 2,5 | 3,98 | 53 % | 13 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r1 | 07:47 |
| P104 | 12.39578, -1.47372 | Arrondissement 9 — Nord | 2,5 | 6,70 | 89 % | 11 | lundi, mercredi, vendredi | 07:00–17:00 | BF-07 r1 | 07:00 |
| P105 | 12.40664, -1.45475 | Arrondissement 9 — Sud | 2,5 | 4,14 | 55 % | 7 | lundi, mercredi, vendredi | 07:00–17:00 | BF-02 r1 | 07:00 |
| P106 | 12.37931, -1.49100 | Arrondissement 9 — Nord | 2,5 | 6,05 | 81 % | 12 | — | 07:00–17:00 | non desservi | — |
| P107 | 12.40251, -1.44192 | Arrondissement 9 — Sud | 2,5 | 6,04 | 80 % | 10 | — | 05:00–08:00 | non desservi | — |
| P108 | 12.39271, -1.45252 | Arrondissement 9 — Sud | 2,5 | 4,23 | 56 % | 11 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r1 | 07:00 |
| P109 | 12.39910, -1.45041 | Arrondissement 9 — Sud | 2,5 | 2,98 | 40 % | 8 | lundi, mercredi, vendredi | 07:00–17:00 | BF-02 r1 | 07:13 |
| P110 | 12.37281, -1.45903 | Arrondissement 9 — Sud | 2,5 | 4,74 | 63 % | 10 | — | 07:00–17:00 | non desservi | — |
| P111 | 12.37575, -1.47506 | Arrondissement 9 — Nord | 2,5 | 4,17 | 56 % | 7 | — | 07:00–17:00 | non desservi | — |
| P112 | 12.38478, -1.46281 | Arrondissement 9 — Sud | 2,5 | 3,37 | 45 % | 4 | — | 07:00–17:00 | non desservi | — |
| P113 | 12.38735, -1.46962 | Arrondissement 9 — Nord | 2,5 | 6,43 | 86 % | 11 | — | 07:00–17:00 | non desservi | — |
| P114 | 12.37500, -1.46327 | Arrondissement 9 — Sud | 2,5 | 5,57 | 74 % | 10 | — | 07:00–17:00 | non desservi | — |
| P115 | 12.37967, -1.45973 | Arrondissement 9 — Sud | 2,5 | 6,01 | 80 % | 16 | — | 07:00–17:00 | non desservi | — |
| P116 | 12.38157, -1.45106 | Arrondissement 9 — Sud | 2,5 | 5,16 | 69 % | 19 | — | 07:00–17:00 | non desservi | — |
| P117 | 12.39719, -1.44326 | Arrondissement 9 — Sud | 2,5 | 4,97 | 66 % | 13 | — | 07:00–17:00 | non desservi | — |
| P118 | 12.38527, -1.48676 | Arrondissement 9 — Nord | 2,5 | 6,83 | 91 % | 9 | — | 07:00–17:00 | non desservi | — |
| P119 | 12.38808, -1.48037 | Arrondissement 9 — Nord | 2,5 | 7,77 | 104 % | 11 | — | 07:00–17:00 | non desservi | — |
| P120 | 12.40370, -1.46827 | Arrondissement 9 — Nord | 2,5 | 5,70 | 76 % | 11 | — | 07:00–17:00 | non desservi | — |
| P121 | 12.38791, -1.47432 | Arrondissement 9 — Nord | 2,5 | 4,20 | 56 % | 6 | — | 07:00–17:00 | non desservi | — |
| P122 | 12.40411, -1.49027 | Arrondissement 9 — Nord | 2,5 | 1,87 | 25 % | 3 | lundi, mercredi, vendredi | 07:00–17:00 | BF-01 r2 | 10:00 |
| P123 | 12.37705, -1.49043 | Arrondissement 9 — Nord | 2,5 | 7,68 | 102 % | 12 | — | 07:00–17:00 | non desservi | — |
| P124 | 12.39023, -1.46430 | Arrondissement 9 — Sud | 2,5 | 4,48 | 60 % | 9 | — | 07:00–17:00 | non desservi | — |
| P125 | 12.38151, -1.48824 | Arrondissement 9 — Nord | 2,5 | 8,05 | 107 % | 9 | — | 07:00–17:00 | non desservi | — |
| P126 | 12.39778, -1.47225 | Arrondissement 9 — Nord | 2,5 | 5,71 | 76 % | 8 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r2 | 10:19 |
| P127 | 12.38891, -1.47256 | Arrondissement 9 — Nord | 2,5 | 5,66 | 75 % | 7 | — | 07:00–17:00 | non desservi | — |
| P128 | 12.40227, -1.48014 | Arrondissement 9 — Nord | 2,5 | 5,12 | 68 % | 6 | lundi, mercredi, vendredi | 07:00–17:00 | BF-01 r2 | 09:25 |
| P129 | 12.39378, -1.44418 | Arrondissement 9 — Sud | 2,5 | 4,54 | 60 % | 16 | — | 07:00–17:00 | non desservi | — |
| P130 | 12.39988, -1.47347 | Arrondissement 9 — Nord | 2,5 | 6,19 | 82 % | 10 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r2 | 10:41 |
| P131 | 12.40606, -1.44617 | Arrondissement 9 — Sud | 2,5 | 6,15 | 82 % | 21 | lundi, mercredi, vendredi | 07:00–17:00 | BF-03 r2 | 08:53 |
| P132 | 12.37652, -1.46662 | Arrondissement 9 — Sud | 2,5 | 6,07 | 81 % | 11 | — | 07:00–17:00 | non desservi | — |
| P133 | 12.40160, -1.46717 | Arrondissement 9 — Sud | 2,5 | 7,09 | 94 % | 9 | — | 07:00–17:00 | non desservi | — |
| P134 | 12.40308, -1.45377 | Arrondissement 9 — Sud | 2,5 | 5,00 | 67 % | 17 | lundi, mercredi, vendredi | 07:00–17:00 | BF-03 r1 | 07:24 |
| P135 | 12.39062, -1.45772 | Arrondissement 9 — Sud | 2,5 | 4,67 | 62 % | 10 | — | 07:00–17:00 | non desservi | — |
| P136 | 12.40381, -1.46620 | Arrondissement 9 — Sud | 2,5 | 4,43 | 59 % | 9 | lundi, mercredi, vendredi | 07:00–17:00 | BF-08 r2 | 10:08 |
| P137 | 12.39537, -1.45144 | Arrondissement 9 — Sud | 2,5 | 5,11 | 68 % | 17 | — | 07:00–17:00 | non desservi | — |
| P138 | 12.40713, -1.46504 | Arrondissement 9 — Sud | 2,5 | 3,53 | 47 % | 8 | lundi, mercredi, vendredi | 07:00–17:00 | BF-03 r1 | 07:00 |
| P139 | 12.40713, -1.45902 | Arrondissement 9 — Sud | 2,5 | 3,98 | 53 % | 10 | lundi, mercredi, vendredi | 07:00–17:00 | BF-03 r1 | 07:46 |
| P140 | 12.38648, -1.44966 | Arrondissement 9 — Sud | 2,5 | 4,44 | 59 % | 14 | — | 07:00–17:00 | non desservi | — |
| P141 | 12.39495, -1.47647 | Arrondissement 9 — Nord | 2,5 | 2,39 | 32 % | 3 | lundi, mercredi, vendredi | 07:00–17:00 | BF-07 r1 | 08:05 |
| P142 | 12.37538, -1.44843 | Arrondissement 9 — Sud | 2,5 | 4,59 | 61 % | 17 | — | 07:00–17:00 | non desservi | — |
| P143 | 12.38110, -1.48346 | Arrondissement 9 — Nord | 2,5 | 6,26 | 84 % | 9 | — | 07:00–17:00 | non desservi | — |
| P144 | 12.39367, -1.48446 | Arrondissement 9 — Nord | 2,5 | 3,76 | 50 % | 6 | lundi, mercredi, vendredi | 07:00–17:00 | BF-07 r2 | 10:08 |
| P145 | 12.38981, -1.44953 | Arrondissement 9 — Sud | 2,5 | 5,51 | 74 % | 20 | — | 07:00–17:00 | non desservi | — |
| P146 | 12.38593, -1.47570 | Arrondissement 9 — Nord | 2,5 | 2,83 | 38 % | 4 | lundi, mercredi, vendredi | 07:00–17:00 | BF-08 r1 | 07:00 |
| P147 | 12.39615, -1.44496 | Arrondissement 9 — Sud | 2,5 | 2,95 | 39 % | 12 | lundi, mercredi, vendredi | 07:00–17:00 | BF-02 r1 | 07:35 |
| P148 | 12.37279, -1.46176 | Arrondissement 9 — Sud | 2,5 | 5,90 | 79 % | 9 | — | 07:00–17:00 | non desservi | — |
| P149 | 12.40380, -1.47398 | Arrondissement 9 — Nord | 2,5 | 4,71 | 63 % | 3 | lundi, mercredi, vendredi | 07:00–17:00 | BF-05 r1 | 07:10 |
| P150 | 12.37469, -1.48718 | Arrondissement 9 — Nord | 2,5 | 7,48 | 100 % | 10 | — | 07:00–17:00 | non desservi | — |
| P151 | 12.38840, -1.46476 | Arrondissement 9 — Sud | 2,5 | 3,74 | 50 % | 7 | — | 07:00–17:00 | non desservi | — |
| P152 | 12.37625, -1.45049 | Arrondissement 9 — Sud | 2,5 | 4,20 | 56 % | 15 | lundi, mercredi, vendredi | 07:00–17:00 | BF-01 r1 | 07:22 |
| P153 | 12.40420, -1.46229 | Arrondissement 9 — Sud | 2,5 | 5,41 | 72 % | 12 | lundi, mercredi, vendredi | 07:00–17:00 | BF-04 r2 | 09:11 |
| P154 | 12.39003, -1.45254 | Arrondissement 9 — Sud | 2,5 | 5,22 | 70 % | 10 | — | 07:00–17:00 | non desservi | — |
| P155 | 12.40165, -1.45769 | Arrondissement 9 — Sud | 2,5 | 5,83 | 78 % | 12 | — | 07:00–17:00 | non desservi | — |
| P156 | 12.38587, -1.44159 | Arrondissement 9 — Sud | 2,5 | 4,31 | 57 % | 16 | — | 07:00–17:00 | non desservi | — |
| P157 | 12.38703, -1.45356 | Arrondissement 9 — Sud | 2,5 | 2,41 | 32 % | 8 | lundi, mercredi, vendredi | 07:00–17:00 | BF-01 r1 | 07:46 |
| P158 | 12.40538, -1.47003 | Arrondissement 9 — Nord | 2,5 | 5,07 | 68 % | 8 | — | 07:00–17:00 | non desservi | — |
| P159 | 12.37904, -1.47808 | Arrondissement 9 — Nord | 2,5 | 6,62 | 88 % | 9 | — | 07:00–17:00 | non desservi | — |
| P160 | 12.38312, -1.47411 | Arrondissement 9 — Nord | 2,5 | 6,25 | 83 % | 8 | — | 07:00–17:00 | non desservi | — |
| P161 | 12.39015, -1.44396 | Arrondissement 9 — Sud | 2,5 | 3,74 | 50 % | 15 | — | 07:00–17:00 | non desservi | — |
| P162 | 12.38045, -1.46536 | Arrondissement 9 — Sud | 2,5 | 4,54 | 60 % | 11 | — | 07:00–17:00 | non desservi | — |
| P163 | 12.37670, -1.45948 | Arrondissement 9 — Sud | 2,5 | 5,47 | 73 % | 13 | — | 05:00–08:00 | non desservi | — |
| P164 | 12.37854, -1.48279 | Arrondissement 9 — Nord | 2,5 | 5,40 | 72 % | 10 | — | 07:00–17:00 | non desservi | — |
| P165 | 12.38492, -1.46746 | Arrondissement 9 — Sud | 2,5 | 4,37 | 58 % | 7 | — | 07:00–17:00 | non desservi | — |
| P166 | 12.38520, -1.47016 | Arrondissement 9 — Nord | 2,5 | 7,02 | 94 % | 13 | — | 07:00–17:00 | non desservi | — |
| P167 | 12.38989, -1.48714 | Arrondissement 9 — Nord | 2,5 | 3,47 | 46 % | 2 | lundi, mercredi, vendredi | 07:00–17:00 | BF-04 r1 | 07:11 |
| P168 | 12.39462, -1.44113 | Arrondissement 9 — Sud | 2,5 | 3,22 | 43 % | 6 | — | 07:00–17:00 | non desservi | — |
| P169 | 12.38492, -1.48442 | Arrondissement 9 — Nord | 2,5 | 5,55 | 74 % | 10 | — | 07:00–17:00 | non desservi | — |
| P170 | 12.40012, -1.46116 | Arrondissement 9 — Sud | 2,5 | 4,19 | 56 % | 11 | lundi, mercredi, vendredi | 07:00–17:00 | BF-08 r2 | 08:51 |
| P171 | 12.38811, -1.45897 | Arrondissement 9 — Sud | 2,5 | 5,48 | 73 % | 12 | — | 07:00–17:00 | non desservi | — |
| P172 | 12.38411, -1.48114 | Arrondissement 9 — Nord | 2,5 | 5,01 | 67 % | 11 | — | 07:00–17:00 | non desservi | — |
| P173 | 12.37848, -1.48630 | Arrondissement 9 — Nord | 2,5 | 5,61 | 75 % | 10 | — | 07:00–17:00 | non desservi | — |
| P174 | 12.37366, -1.47293 | Arrondissement 9 — Nord | 2,5 | 8,43 | 112 % | 9 | — | 07:00–17:00 | non desservi | — |
| P175 | 12.38526, -1.48954 | Arrondissement 9 — Nord | 2,5 | 3,60 | 48 % | 4 | — | 07:00–17:00 | non desservi | — |
| P176 | 12.38917, -1.47007 | Arrondissement 9 — Nord | 2,5 | 5,21 | 70 % | 9 | — | 07:00–17:00 | non desservi | — |
| P177 | 12.38042, -1.46297 | Arrondissement 9 — Sud | 2,5 | 3,91 | 52 % | 6 | — | 07:00–17:00 | non desservi | — |
| P178 | 12.37311, -1.45064 | Arrondissement 9 — Sud | 2,5 | 2,79 | 37 % | 16 | lundi, mercredi, vendredi | 07:00–17:00 | BF-01 r1 | 07:00 |
| P179 | 12.39567, -1.48357 | Arrondissement 9 — Nord | 2,5 | 6,95 | 93 % | 10 | lundi, mercredi, vendredi | 07:00–17:00 | BF-07 r2 | 10:19 |
| P180 | 12.38098, -1.49081 | Arrondissement 9 — Nord | 2,5 | 7,75 | 103 % | 10 | — | 07:00–17:00 | non desservi | — |
| P181 | 12.39872, -1.44087 | Arrondissement 9 — Sud | 2,5 | 4,36 | 58 % | 6 | — | 07:00–17:00 | non desservi | — |
| P182 | 12.37335, -1.45432 | Arrondissement 9 — Sud | 2,5 | 4,87 | 65 % | 26 | — | 07:00–17:00 | non desservi | — |
| P183 | 12.40340, -1.44629 | Arrondissement 9 — Sud | 2,5 | 5,00 | 67 % | 12 | lundi, mercredi, vendredi | 07:00–17:00 | BF-03 r2 | 09:28 |
| P184 | 12.38563, -1.49124 | Arrondissement 9 — Nord | 2,5 | 4,58 | 61 % | 5 | — | 07:00–17:00 | non desservi | — |
| P185 | 12.38849, -1.45580 | Arrondissement 9 — Sud | 2,5 | 6,15 | 82 % | 14 | — | 07:00–17:00 | non desservi | — |
| P186 | 12.39311, -1.45421 | Arrondissement 9 — Sud | 2,5 | 4,28 | 57 % | 7 | — | 07:00–17:00 | non desservi | — |
| P187 | 12.39906, -1.44826 | Arrondissement 9 — Sud | 2,5 | 5,59 | 74 % | 15 | — | 07:00–17:00 | non desservi | — |
| P188 | 12.39770, -1.47608 | Arrondissement 9 — Nord | 2,5 | 7,47 | 100 % | 11 | — | 07:00–17:00 | non desservi | — |
| P189 | 12.37666, -1.47720 | Arrondissement 9 — Nord | 2,5 | 7,65 | 102 % | 13 | — | 07:00–17:00 | non desservi | — |
| P190 | 12.37363, -1.46977 | Arrondissement 9 — Nord | 2,5 | 6,54 | 87 % | 11 | — | 07:00–17:00 | non desservi | — |
| P191 | 12.39256, -1.45686 | Arrondissement 9 — Sud | 2,5 | 5,75 | 77 % | 8 | — | 07:00–17:00 | non desservi | — |
| P192 | 12.40152, -1.44896 | Arrondissement 9 — Sud | 2,5 | 5,97 | 80 % | 11 | — | 07:00–17:00 | non desservi | — |
| P193 | 12.39161, -1.45976 | Arrondissement 9 — Sud | 2,5 | 4,24 | 56 % | 8 | — | 07:00–17:00 | non desservi | — |
| P194 | 12.38908, -1.48258 | Arrondissement 9 — Nord | 2,5 | 7,00 | 93 % | 10 | lundi, mercredi, vendredi | 07:00–17:00 | BF-04 r1 | 07:44 |
| P195 | 12.37659, -1.48237 | Arrondissement 9 — Nord | 2,5 | 5,18 | 69 % | 9 | — | 07:00–17:00 | non desservi | — |
| P196 | 12.39598, -1.46098 | Arrondissement 9 — Sud | 2,5 | 5,21 | 69 % | 10 | lundi, mercredi, vendredi | 07:00–17:00 | BF-08 r2 | 09:35 |
| P197 | 12.38267, -1.46631 | Arrondissement 9 — Sud | 2,5 | 5,52 | 74 % | 10 | — | 07:00–17:00 | non desservi | — |
| P198 | 12.39371, -1.44635 | Arrondissement 9 — Sud | 2,5 | 3,94 | 52 % | 15 | — | 07:00–17:00 | non desservi | — |
| P199 | 12.38080, -1.46765 | Arrondissement 9 — Sud | 2,5 | 4,22 | 56 % | 9 | — | 07:00–17:00 | non desservi | — |
| P200 | 12.40333, -1.47846 | Arrondissement 9 — Nord | 2,5 | 4,27 | 57 % | 6 | lundi, mercredi, vendredi | 07:00–17:00 | BF-01 r2 | 09:15 |
| P201 | 12.37811, -1.46907 | Arrondissement 9 — Nord | 2,5 | 7,02 | 94 % | 12 | — | 07:00–17:00 | non desservi | — |
| P202 | 12.38132, -1.45930 | Arrondissement 9 — Sud | 2,5 | 5,99 | 80 % | 9 | — | 07:00–17:00 | non desservi | — |
| P203 | 12.38334, -1.47141 | Arrondissement 9 — Nord | 2,5 | 5,36 | 71 % | 10 | — | 07:00–17:00 | non desservi | — |
| P204 | 12.40087, -1.45575 | Arrondissement 9 — Sud | 2,5 | 5,96 | 79 % | 15 | — | 07:00–17:00 | non desservi | — |
| P205 | 12.38491, -1.46476 | Arrondissement 9 — Sud | 2,5 | 5,65 | 75 % | 9 | — | 07:00–17:00 | non desservi | — |
| P206 | 12.38799, -1.44341 | Arrondissement 9 — Sud | 2,5 | 4,54 | 60 % | 13 | — | 07:00–17:00 | non desservi | — |
| P207 | 12.38041, -1.44093 | Arrondissement 9 — Sud | 2,5 | 4,32 | 58 % | 13 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r1 | 07:36 |
| P208 | 12.38260, -1.44558 | Arrondissement 9 — Sud | 2,5 | 4,57 | 61 % | 18 | — | 07:00–17:00 | non desservi | — |
| P209 | 12.39715, -1.46742 | Arrondissement 9 — Sud | 2,5 | 4,90 | 65 % | 11 | — | 07:00–17:00 | non desservi | — |
| P210 | 12.38386, -1.48817 | Arrondissement 9 — Nord | 2,5 | 4,72 | 63 % | 5 | — | 07:00–17:00 | non desservi | — |
| P211 | 12.39367, -1.47448 | Arrondissement 9 — Nord | 2,5 | 4,84 | 65 % | 7 | — | 07:00–17:00 | non desservi | — |
| P212 | 12.40675, -1.46964 | Arrondissement 9 — Nord | 2,5 | 4,44 | 59 % | 7 | — | 07:00–17:00 | non desservi | — |
| P213 | 12.39091, -1.44127 | Arrondissement 9 — Sud | 2,5 | 5,23 | 70 % | 11 | — | 07:00–17:00 | non desservi | — |
| P214 | 12.39929, -1.48201 | Arrondissement 9 — Nord | 2,5 | 4,44 | 59 % | 7 | lundi, mercredi, vendredi | 07:00–17:00 | BF-01 r2 | 09:47 |
| P215 | 12.38556, -1.46023 | Arrondissement 9 — Sud | 2,5 | 4,19 | 56 % | 4 | — | 07:00–17:00 | non desservi | — |
| P216 | 12.39638, -1.45836 | Arrondissement 9 — Sud | 2,5 | 4,48 | 60 % | 13 | lundi, mercredi, vendredi | 07:00–17:00 | BF-08 r2 | 09:13 |
| P217 | 12.40435, -1.46393 | Arrondissement 9 — Sud | 2,5 | 4,47 | 60 % | 9 | lundi, mercredi, vendredi | 07:00–17:00 | BF-04 r2 | 09:00 |
| P218 | 12.39356, -1.46090 | Arrondissement 9 — Sud | 2,5 | 6,21 | 83 % | 14 | — | 07:00–17:00 | non desservi | — |
| P219 | 12.37444, -1.47552 | Arrondissement 9 — Nord | 2,5 | 7,73 | 103 % | 11 | — | 07:00–17:00 | non desservi | — |
| P220 | 12.38191, -1.48049 | Arrondissement 9 — Nord | 2,5 | 6,63 | 88 % | 13 | — | 07:00–17:00 | non desservi | — |
| P221 | 12.38302, -1.45275 | Arrondissement 9 — Sud | 2,5 | 6,20 | 83 % | 11 | — | 07:00–17:00 | non desservi | — |
| P222 | 12.39773, -1.47017 | Arrondissement 9 — Nord | 2,5 | 5,91 | 79 % | 12 | — | 07:00–17:00 | non desservi | — |
| P223 | 12.37519, -1.46549 | Arrondissement 9 — Sud | 2,5 | 6,14 | 82 % | 12 | — | 07:00–17:00 | non desservi | — |
| P224 | 12.39066, -1.47401 | Arrondissement 9 — Nord | 2,5 | 6,21 | 83 % | 7 | lundi, mercredi, vendredi | 07:00–17:00 | BF-07 r1 | 07:32 |
| P225 | 12.37292, -1.46763 | Arrondissement 9 — Sud | 2,5 | 4,33 | 58 % | 9 | — | 07:00–17:00 | non desservi | — |
| P226 | 12.38003, -1.44536 | Arrondissement 9 — Sud | 2,5 | 3,61 | 48 % | 12 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r1 | 07:15 |
| P227 | 12.38235, -1.44867 | Arrondissement 9 — Sud | 2,5 | 4,35 | 58 % | 16 | — | 07:00–17:00 | non desservi | — |
| P228 | 12.37868, -1.45021 | Arrondissement 9 — Sud | 2,5 | 3,40 | 45 % | 14 | lundi, mercredi, vendredi | 07:00–17:00 | BF-01 r1 | 07:33 |
| P229 | 12.38581, -1.45239 | Arrondissement 9 — Sud | 2,5 | 4,39 | 59 % | 9 | — | 07:00–17:00 | non desservi | — |
| P230 | 12.40522, -1.46043 | Arrondissement 9 — Sud | 2,5 | 4,29 | 57 % | 13 | lundi, mercredi, vendredi | 07:00–17:00 | BF-04 r2 | 09:22 |
| P231 | 12.37806, -1.45742 | Arrondissement 9 — Sud | 2,5 | 6,05 | 81 % | 18 | — | 07:00–17:00 | non desservi | — |
| P232 | 12.37212, -1.46409 | Arrondissement 9 — Sud | 2,5 | 3,34 | 44 % | 5 | — | 07:00–17:00 | non desservi | — |
| P233 | 12.37590, -1.45319 | Arrondissement 9 — Sud | 2,5 | 4,38 | 58 % | 21 | — | 07:00–17:00 | non desservi | — |
| P234 | 12.37318, -1.44835 | Arrondissement 9 — Sud | 2,5 | 2,91 | 39 % | 14 | lundi, mercredi, vendredi | 07:00–17:00 | BF-01 r1 | 07:10 |
| P235 | 12.40252, -1.47278 | Arrondissement 9 — Nord | 2,5 | 4,13 | 55 % | 6 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r2 | 09:47 |
| P236 | 12.40541, -1.47457 | Arrondissement 9 — Nord | 2,5 | 4,79 | 64 % | 4 | lundi, mercredi, vendredi | 07:00–17:00 | BF-05 r1 | 07:00 |
| P237 | 12.38793, -1.47649 | Arrondissement 9 — Nord | 2,5 | 2,59 | 35 % | 3 | lundi, mercredi, vendredi | 05:00–08:00 | BF-08 r1 | 05:40 |
| P238 | 12.40008, -1.46408 | Arrondissement 9 — Sud | 2,5 | 4,81 | 64 % | 8 | lundi, mercredi, vendredi | 07:00–17:00 | BF-08 r2 | 09:57 |
| P239 | 12.39066, -1.47137 | Arrondissement 9 — Nord | 2,5 | 6,17 | 82 % | 7 | — | 07:00–17:00 | non desservi | — |
| P240 | 12.37997, -1.44891 | Arrondissement 9 — Sud | 2,5 | 3,96 | 53 % | 18 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r1 | 08:23 |
| P241 | 12.39999, -1.44366 | Arrondissement 9 — Sud | 2,5 | 3,99 | 53 % | 12 | lundi, mercredi, vendredi | 07:00–17:00 | BF-03 r2 | 09:17 |
| P242 | 12.37803, -1.44443 | Arrondissement 9 — Sud | 2,5 | 3,10 | 41 % | 9 | — | 07:00–17:00 | non desservi | — |
| P243 | 12.39194, -1.44756 | Arrondissement 9 — Sud | 2,5 | 4,13 | 55 % | 16 | — | 07:00–17:00 | non desservi | — |
| P244 | 12.39298, -1.47263 | Arrondissement 9 — Nord | 2,5 | 5,02 | 67 % | 9 | lundi, mercredi, vendredi | 07:00–17:00 | BF-07 r1 | 07:11 |
| P245 | 12.37425, -1.48293 | Arrondissement 9 — Nord | 2,5 | 9,29 | 124 % | 14 | — | 07:00–17:00 | non desservi | — |
| P246 | 12.39670, -1.44981 | Arrondissement 9 — Sud | 2,5 | 3,58 | 48 % | 16 | — | 07:00–17:00 | non desservi | — |
| P247 | 12.39793, -1.46354 | Arrondissement 9 — Sud | 2,5 | 7,58 | 101 % | 18 | — | 05:00–08:00 | non desservi | — |
| P248 | 12.39515, -1.45334 | Arrondissement 9 — Sud | 2,5 | 3,73 | 50 % | 10 | — | 07:00–17:00 | non desservi | — |
| P249 | 12.38389, -1.47796 | Arrondissement 9 — Nord | 2,5 | 5,61 | 75 % | 7 | — | 07:00–17:00 | non desservi | — |
| P250 | 12.39914, -1.47849 | Arrondissement 9 — Nord | 2,5 | 4,59 | 61 % | 7 | lundi, mercredi, vendredi | 07:00–17:00 | BF-05 r2 | 08:45 |
| P251 | 12.40489, -1.45484 | Arrondissement 9 — Sud | 2,5 | 6,20 | 83 % | 9 | lundi, mercredi, vendredi | 07:00–17:00 | BF-03 r1 | 07:35 |
| P252 | 12.38536, -1.47967 | Arrondissement 9 — Nord | 2,5 | 4,91 | 65 % | 8 | — | 07:00–17:00 | non desservi | — |
| P253 | 12.39086, -1.46179 | Arrondissement 9 — Sud | 2,5 | 4,65 | 62 % | 10 | — | 07:00–17:00 | non desservi | — |
| P254 | 12.37684, -1.46228 | Arrondissement 9 — Sud | 2,5 | 5,90 | 79 % | 11 | — | 05:00–08:00 | non desservi | — |
| P255 | 12.38738, -1.46130 | Arrondissement 9 — Sud | 2,5 | 4,76 | 64 % | 9 | — | 07:00–17:00 | non desservi | — |
| P256 | 12.39383, -1.44886 | Arrondissement 9 — Sud | 2,5 | 3,75 | 50 % | 20 | — | 07:00–17:00 | non desservi | — |
| P257 | 12.40126, -1.47469 | Arrondissement 9 — Nord | 2,5 | 6,04 | 80 % | 6 | lundi, mercredi, vendredi | 07:00–17:00 | BF-05 r2 | 09:07 |
| P258 | 12.40000, -1.46974 | Arrondissement 9 — Nord | 2,5 | 5,13 | 68 % | 7 | lundi, mercredi, vendredi | 07:00–17:00 | BF-06 r2 | 10:08 |
| P259 | 12.37490, -1.45967 | Arrondissement 9 — Sud | 2,5 | 4,97 | 66 % | 10 | — | 07:00–17:00 | non desservi | — |
| P260 | 12.39842, -1.45754 | Arrondissement 9 — Sud | 2,5 | 4,84 | 65 % | 10 | — | 07:00–17:00 | non desservi | — |
| P261 | 12.40577, -1.46565 | Arrondissement 9 — Sud | 2,5 | 3,07 | 41 % | 6 | lundi, mercredi, vendredi | 07:00–17:00 | BF-04 r2 | 08:50 |
| P262 | 12.38601, -1.47794 | Arrondissement 9 — Nord | 2,5 | 4,76 | 63 % | 7 | lundi, mercredi, vendredi | 07:00–17:00 | BF-08 r1 | 07:10 |
| P263 | 12.39801, -1.48114 | Arrondissement 9 — Nord | 2,5 | 3,00 | 40 % | 5 | lundi, mercredi, vendredi | 07:00–17:00 | BF-05 r2 | 08:34 |
| P264 | 12.38752, -1.44799 | Arrondissement 9 — Sud | 2,5 | 3,80 | 51 % | 12 | — | 07:00–17:00 | non desservi | — |
| P265 | 12.38798, -1.48820 | Arrondissement 9 — Nord | 2,5 | 2,07 | 28 % | 3 | lundi, mercredi, vendredi | 07:00–17:00 | BF-07 r2 | 09:56 |

## Coûts et personnel

- Coût par jour d'enlèvement : 375 345 FCFA, soit ~4 879 485 FCFA par mois (3.0 enlèvements par semaine).
- Personnel par jour d'enlèvement : 8 chauffeur(s) et 16 ripeur(s) (hypothèse : un chauffeur et deux ripeurs par camion).

## Indicateurs simulés (90 jours)

| Indicateur | Référence | Flotte nécessaire | 2 camions en panne | Saison des pluies | Abonnements +20 % | Budget −30 % | Pluies + 2 camions en panne |
|---|---|---|---|---|---|---|---|
| Tonnes collectées par camion | 4 104,5 [4 083,6 ; 4 130,3] | 16 702,4 [16 600,4 ; 16 865,4] | 4 167,5 [4 127,7 ; 4 193,5] | 3 805,7 [3 793,0 ; 3 820,7] | 4 100,6 [4 074,9 ; 4 143,6] | 2 830,6 [2 803,1 ; 2 855,2] | 4 002,3 [3 982,9 ; 4 025,9] |
| Tonnes pré-collectées | 5 335,6 [5 304,7 ; 5 363,8] | 5 280,2 [5 248,7 ; 5 311,2] | 5 331,7 [5 300,0 ; 5 358,6] | 5 532,6 [5 501,7 ; 5 546,5] | 5 579,8 [5 559,1 ; 5 598,1] | 5 337,1 [5 307,7 ; 5 370,4] | 5 526,3 [5 502,1 ; 5 552,4] |
| Tonnes en dépôt sauvage | 13 082,2 [13 043,0 ; 13 128,1] | 1 117,1 [972,4 ; 1 262,4] | 13 194,3 [13 132,7 ; 13 264,1] | 16 123,7 [16 077,6 ; 16 174,0] | 13 075,5 [12 996,2 ; 13 120,9] | 14 377,8 [14 344,7 ; 14 421,7] | 16 005,4 [15 965,7 ; 16 066,5] |
| Dépotoirs actifs (moyenne) | 2 652,7 [2 633,3 ; 2 665,2] | 464,4 [129,9 ; 687,1] | 2 315,7 [2 286,2 ; 2 364,5] | 2 758,7 [2 750,6 ; 2 768,6] | 2 637,7 [2 622,5 ; 2 651,0] | 2 764,5 [2 761,7 ; 2 771,2] | 2 507,8 [2 473,4 ; 2 555,6] |
| Couverture simulée* (%) | 50 [50 ; 50] | 95 [94 ; 95] | 50 [49 ; 50] | 45 [45 ; 45] | 51 [51 ; 52] | 45 [45 ; 45] | 45 [45 ; 45] |
| Taux d'abonnement final (%) | 40 [39 ; 40] | 41 [40 ; 41] | 40 [40 ; 40] | 38 [38 ; 38] | 43 [42 ; 43] | 40 [40 ; 40] | 38 [38 ; 38] |
| Pré-collecteurs actifs (fin) | 191 [189 ; 192] | 191 [189 ; 192] | 191 [189 ; 192] | 191 [189 ; 192] | 192 [191 ; 192] | 191 [189 ; 192] | 190 [189 ; 192] |
| Coût de la mairie (FCFA/t) | 2 551 [2 537 ; 2 563] | 2 981 [2 970 ; 2 989] | 2 508 [2 498 ; 2 523] | 2 764 [2 748 ; 2 775] | 2 556 [2 530 ; 2 569] | 2 592 [2 570 ; 2 614] | 2 621 [2 606 ; 2 630] |
| Jours-points en débordement | 17 022 [16 965 ; 17 057] | 1 495 [1 295 ; 1 690] | 16 510 [16 429 ; 16 616] | 17 968 [17 940 ; 18 013] | 17 008 [16 945 ; 17 081] | 18 924 [18 855 ; 18 955] | 17 523 [17 483 ; 17 593] |

\* Part de la population servie un jour donné : point à portée de marche **et pas plein**, ou passage du pré-collecteur dans les 7 jours. Plus stricte que la couverture du plan (distance seule).

## Incertitude des chiffres simulés

Les intervalles ci-dessus ne viennent que du hasard des simulations (graines). Les paramètres de comportement ne sont pas calés (`SIMULATION_CALIBRATION.md`) : chaque variante est donc simulée une seconde fois en tirant à chaque réplication les déchets par habitant (±25 %), la propension de base à jeter (±1 en log-cote) et l'effet de la distance (de la moitié au double). Référence :

| Indicateur | Graines seules | Graines + paramètres non calés |
|---|---|---|
| Tonnes en dépôt sauvage | 13 082,2 [13 043,0 ; 13 128,1] | 13 062,0 [10 719,8 ; 16 860,9] |
| Tonnes collectées par camion | 4 104,5 [4 083,6 ; 4 130,3] | 4 111,6 [3 712,9 ; 4 223,0] |
| Couverture simulée (%) | 50 [50 ; 50] | 49 [43 ; 54] |
| Coût de la mairie (FCFA/t) | 2 551 [2 537 ; 2 563] | 2 550 [2 479 ; 2 822] |

Les valeurs absolues sont donc fragiles ; les **écarts à la référence** le sont moins (mêmes graines, mêmes paramètres pour toutes les variantes). Écart des médianes à la référence, dépôts sauvages :

| Variante | Écart (t, graines) | Écart (t, avec paramètres) |
|---|---|---|
| Flotte nécessaire | -11965,0 | -11973,1 |
| 2 camions en panne | +112,1 | +171,8 |
| Saison des pluies | +3041,6 | +3082,7 |
| Abonnements +20 % | -6,6 | -0,5 |
| Budget −30 % | +1295,6 | +1276,1 |
| Pluies + 2 camions en panne | +2923,3 | +2976,5 |

## Risques

- **Pannes** : avec 2 camions en moins, 185 points ne sont pas desservis (172 en référence) ; aucun point ne bouge (points inchangés : 100 %), mais les tournées sont refaites (camions sur les mêmes points : 5 %). Prévoir un camion de réserve ou une rotation supplémentaire.
- **Budget** : 3 482 877 FCFA par mois, soit le budget de la commune (25 000 000 FCFA, hypothèse à remplacer par celui de la mairie) au prorata de la population de l'arrondissement (13,9 %). Le plan coûte ~4 879 485 FCFA par mois en camions : au-dessus du budget. Quand l'argent du mois est épuisé, les camions s'arrêtent : dépôts sauvages simulés 13 082,2 [13 043,0 ; 13 128,1] t en référence, 14 377,8 [14 344,7 ; 14 421,7] t avec le budget réduit de 30 %.
- **Pré-collecte** : la charrette est le goulot (`SIMULATION_ODD.md` § 11) ; plus d'abonnés sans plus de pré-collecteurs n'augmente pas la pré-collecte.
- **Données** : la quantité de déchets par habitant explique ~90 % de l'incertitude sur les dépôts (`SIMULATION_SENSIBILITE.md`) ; la mesurer par pesée dans l'arrondissement avant de dimensionner.

## Saison des pluies

- Demande +15 % (1 625,2 t/semaine) et vitesses réduites : 482,5 km, 405 147 FCFA par jour d'enlèvement, 179 point(s) non desservi(s), 16 tournée(s).
- Avant les pluies : curer les caniveaux près des points, déplacer hors des zones inondables les bacs signalés « près de l'eau », vider les dépotoirs proches des cours d'eau en priorité (règle de nettoyage du plan).
- Pendant : ajouter une rotation les jours après une forte pluie, garder un camion en réserve, renforcer les descentes Laabal dans les îlots récurrents en même temps que des rotations de camions (sinon les points débordent).

## Indicateurs de suivi pour la mairie

Chaque mois, comparer à la valeur simulée de référence (colonne « Référence ») ; un écart qui sort de l'intervalle à 90 % appelle une explication.

| Indicateur | Comment le mesurer | Fréquence | Valeur simulée (référence) | Alerte si |
|---|---|---|---|---|
| Tonnes collectées par camion | bons de pesée au CET | mensuelle | 4 104,5 [4 083,6 ; 4 130,3] t / 90 j | sous le 5ᵉ centile |
| Tonnes en dépôt sauvage | signalements vérifiés × volume (Salubri Map) | mensuelle | 13 082,2 [13 043,0 ; 13 128,1] t / 90 j | au-dessus du 95ᵉ centile |
| Dépotoirs récurrents | Salubri Map, filtre « récurrent » | mensuelle | 140,5 [121,5 ; 151,6] | en hausse 2 mois de suite |
| Points en débordement | photos des chefs de point / signalements « point plein » | hebdomadaire | 17 022 [16 965 ; 17 057] jours-points / 90 j | un même point 2 semaines de suite |
| Taux d'abonnement à la pré-collecte | registres des associations | trimestrielle | 40 [39 ; 40] % | baisse de plus de 5 points |
| Coût par tonne | comptabilité (carburant, salaires, entretien) | mensuelle | 2 551 [2 537 ; 2 563] FCFA/t | au-dessus du 95ᵉ centile |
| Tournées faites / prévues | fiches de tournée signées | hebdomadaire | 100 % prévu | sous 90 % |

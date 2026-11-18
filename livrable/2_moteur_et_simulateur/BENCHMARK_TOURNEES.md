<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Banc d'essai des tournées

Généré par `scripts/benchmark_tournees.py` le 2026-11-17 (2 cœurs ; OSRM http://localhost:5000 injoignable : matrice approchée seule). Matrice approchée = vol d'oiseau × détour (repli sans OSRM). Objectif OR-Tools = coût (carburant au km + coût fixe des camions sortis + pénalité par point non desservi). **Écart** = écart à la meilleure solution connue (meilleur objectif des 9 exécutions de l'instance) ; **borne** = borne inférieure garantie des km (`vrp.lower_bound_km` : radiale et aller-retour le plus long), faible, donc l'écart aux km qu'elle donne est un majorant très prudent.

## Zone pilote (plan v62), matrice approchée — 77 points, 8 camions

| Solveur, limite (effective) | Départ | Objectif | Écart à la meilleure connue | km | Borne inf. km | Desservis | Tonnes non desservies | Durée |
|---|---|---|---|---|---|---|---|---|
| OR-Tools 1 s (1 s) | PARALLEL_CHEAPEST_INSERTION | 383 214 | 7,1 % | 531.5 | 380.7 | 77 / 77 | 0.0 | 1.1 s |
| OR-Tools 1 s (1 s) | PATH_CHEAPEST_ARC | 385 032 | 7,6 % | 536.7 | 380.7 | 77 / 77 | 0.0 | 1.0 s |
| OR-Tools 1 s (1 s) | SAVINGS | 384 640 | 7,5 % | 536.4 | 380.7 | 77 / 77 | 0.0 | 1.0 s |
| OR-Tools 5 s (5 s) | PARALLEL_CHEAPEST_INSERTION | 382 386 | 6,9 % | 529.0 | 380.7 | 77 / 77 | 0.0 | 5.0 s |
| OR-Tools 5 s (5 s) | PATH_CHEAPEST_ARC | 384 469 | 7,5 % | 535.7 | 380.7 | 77 / 77 | 0.0 | 5.0 s |
| OR-Tools 5 s (5 s) | SAVINGS | 383 368 | 7,2 % | 533.0 | 380.7 | 77 / 77 | 0.0 | 5.0 s |
| OR-Tools 15 s (15 s) | PARALLEL_CHEAPEST_INSERTION | 381 407 | 6,6 % | 526.8 | 380.7 | 77 / 77 | 0.0 | 15.0 s |
| OR-Tools 15 s (15 s) | PATH_CHEAPEST_ARC | 357 680 | 0,0 % | 503.2 | 380.7 | 77 / 77 | 0.0 | 15.0 s |
| OR-Tools 15 s (15 s) | SAVINGS | 383 283 | 7,2 % | 530.6 | 380.7 | 77 / 77 | 0.0 | 15.0 s |
| repli | heuristique de repli (sans OR-Tools) | 502 175 | — (objectif sans pénalité) | 603.5 | 357.5 | 73 / 77 | 6.8 | 0.0 s |

## Ville entière (démo) (plan v52), matrice approchée — 1034 points, 8 camions

| Solveur, limite (effective) | Départ | Objectif | Écart à la meilleure connue | km | Borne inf. km | Desservis | Tonnes non desservies | Durée |
|---|---|---|---|---|---|---|---|---|
| OR-Tools 1 s (3.45 s) | PARALLEL_CHEAPEST_INSERTION | 9 610 302 804 | 0,2 % | 267.0 | 171.2 | 73 / 1034 | 2033.2 | 6.4 s |
| OR-Tools 1 s (3.45 s) | PATH_CHEAPEST_ARC | 9 630 294 428 | 0,4 % | 251.2 | 161.9 | 71 / 1034 | 2035.1 | 5.9 s |
| OR-Tools 1 s (3.45 s) | SAVINGS → heuristique de repli | 10 179 309 | — (repli) | 637.1 | 398.0 | 64 / 1034 | 2052.1 | 5.7 s |
| OR-Tools 5 s (5 s) | PARALLEL_CHEAPEST_INSERTION | 9 610 300 097 | 0,2 % | 261.2 | 168.6 | 73 / 1034 | 2034.2 | 7.5 s |
| OR-Tools 5 s (5 s) | PATH_CHEAPEST_ARC | 9 610 304 844 | 0,2 % | 272.6 | 170.9 | 73 / 1034 | 2033.6 | 7.6 s |
| OR-Tools 5 s (5 s) | SAVINGS → heuristique de repli | 10 179 309 | — (repli) | 637.1 | 398.0 | 64 / 1034 | 2052.1 | 7.3 s |
| OR-Tools 15 s (15 s) | PARALLEL_CHEAPEST_INSERTION | 9 590 299 694 | 0,0 % | 260.2 | 171.4 | 75 / 1034 | 2031.8 | 17.4 s |
| OR-Tools 15 s (15 s) | PATH_CHEAPEST_ARC | 9 600 297 696 | 0,1 % | 257.1 | 168.0 | 74 / 1034 | 2033.7 | 17.6 s |
| OR-Tools 15 s (15 s) | SAVINGS → heuristique de repli | 10 179 309 | — (repli) | 637.1 | 398.0 | 64 / 1034 | 2052.1 | 17.4 s |
| repli | heuristique de repli (sans OR-Tools) | 10 179 309 | — (objectif sans pénalité) | 637.1 | 398.0 | 64 / 1034 | 2052.1 | 2.5 s |

## Lecture

- **Zone pilote** : à 1 s, la meilleure stratégie est à 7,1 % de la meilleure solution connue.
- **Ville entière (démo)** : la flotte de démonstration (8 camions) ne dessert que 75 points sur 1034 par jour d'enlèvement ; l'objectif est dominé par la pénalité des points non desservis. Ce n'est pas un défaut du solveur : il manque des camions (ou des rotations) pour la ville. À reprendre avec la vraie flotte de la mairie.
- **Heuristique de repli** (zone pilote) : 603.5 km et 6.8 t non desservies, contre 503.2 km et 0.0 t pour la meilleure exécution OR-Tools : c'est le prix d'une panne d'OR-Tools, pas le fonctionnement normal.
- **Avec / sans OSRM** : OSRM n'était pas joignable là où ce banc a tourné ; relancer avec `--osrm` sur la machine de démonstration (à faire par l'équipe). Le facteur de détour du repli est calé par `scripts/calibrer_detour.py` (`docs/DETOUR_CALIBRATION.md`).
- La limite par défaut du test en direct est 1 s (`vrp_time_limit_s`), relevée automatiquement pour les grandes instances (1 s par 300 points, au plus 8 s).
- L'écart de 1 s à la meilleure connue mesure ce que coûte la réponse rapide pendant la démonstration ; relancer avec une limite plus longue pour le plan définitif.

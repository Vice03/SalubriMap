<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Banc d'essai des tournées

Généré par `scripts/benchmark_tournees.py` le 2026-11-17 (2 cœurs, matrice approchée vol d'oiseau × détour). Objectif OR-Tools = coût (carburant au km + coût fixe des camions sortis + pénalité par point non desservi). **Écart** = écart à la meilleure solution connue (meilleur objectif des 9 exécutions de l'instance) ; **borne** = borne inférieure garantie des km (`vrp.lower_bound_km` : radiale et aller-retour le plus long), faible, donc l'écart aux km qu'elle donne est un majorant très prudent.

## Zone pilote (plan v167) — 77 points, 8 camions

| Limite (effective) | Départ | Objectif | Écart à la meilleure connue | km | Borne inf. km | Desservis | Durée |
|---|---|---|---|---|---|---|---|
| 1 s (1 s) | PARALLEL_CHEAPEST_INSERTION | 383 606 | 0,7 % | 532.6 | 380.6 | 77 / 77 | 1.1 s |
| 1 s (1 s) | PATH_CHEAPEST_ARC | 387 329 | 1,6 % | 543.0 | 380.6 | 77 / 77 | 1.0 s |
| 1 s (1 s) | SAVINGS | 384 692 | 0,9 % | 536.1 | 380.6 | 77 / 77 | 1.0 s |
| 5 s (5 s) | PARALLEL_CHEAPEST_INSERTION | 383 008 | 0,5 % | 531.0 | 380.6 | 77 / 77 | 5.0 s |
| 5 s (5 s) | PATH_CHEAPEST_ARC | 383 347 | 0,6 % | 532.5 | 380.6 | 77 / 77 | 5.0 s |
| 5 s (5 s) | SAVINGS | 384 069 | 0,8 % | 534.4 | 380.6 | 77 / 77 | 5.0 s |
| 15 s (15 s) | PARALLEL_CHEAPEST_INSERTION | 381 123 | 0,0 % | 526.1 | 380.6 | 77 / 77 | 15.0 s |
| 15 s (15 s) | PATH_CHEAPEST_ARC | 383 347 | 0,6 % | 532.5 | 380.6 | 77 / 77 | 15.0 s |
| 15 s (15 s) | SAVINGS | 383 375 | 0,6 % | 532.6 | 380.6 | 77 / 77 | 15.0 s |

## Ville entière (démo) (plan v129) — 1034 points, 8 camions

| Limite (effective) | Départ | Objectif | Écart à la meilleure connue | km | Borne inf. km | Desservis | Durée |
|---|---|---|---|---|---|---|---|
| 1 s (3.45 s) | PARALLEL_CHEAPEST_INSERTION | 9 610 299 278 | 0,1 % | 260.7 | 167.9 | 73 / 1034 | 6.2 s |
| 1 s (3.45 s) | PATH_CHEAPEST_ARC | 9 600 300 199 | 0,0 % | 263.8 | 167.7 | 74 / 1034 | 6.4 s |
| 1 s (3.45 s) | SAVINGS → heuristique de repli | 10 168 280 | — (repli) | 618.0 | 379.6 | 64 / 1034 | 6.2 s |
| 5 s (5 s) | PARALLEL_CHEAPEST_INSERTION | 9 600 301 092 | 0,0 % | 264.7 | 170.6 | 74 / 1034 | 7.7 s |
| 5 s (5 s) | PATH_CHEAPEST_ARC | 9 600 299 335 | 0,0 % | 262.1 | 168.0 | 74 / 1034 | 7.8 s |
| 5 s (5 s) | SAVINGS → heuristique de repli | 10 168 280 | — (repli) | 618.0 | 379.6 | 64 / 1034 | 7.7 s |
| 15 s (15 s) | PARALLEL_CHEAPEST_INSERTION | 9 600 298 944 | 0,0 % | 259.8 | 169.3 | 74 / 1034 | 18.1 s |
| 15 s (15 s) | PATH_CHEAPEST_ARC | 9 600 297 651 | 0,0 % | 258.3 | 167.2 | 74 / 1034 | 17.7 s |
| 15 s (15 s) | SAVINGS → heuristique de repli | 10 168 280 | — (repli) | 618.0 | 379.6 | 64 / 1034 | 17.3 s |

## Lecture

- **Zone pilote** : à 1 s, la meilleure stratégie est à 0,7 % de la meilleure solution connue.
- **Ville entière (démo)** : la flotte de démonstration (8 camions) ne dessert que 74 points sur 1034 par jour d'enlèvement ; l'objectif est dominé par la pénalité des points non desservis. Ce n'est pas un défaut du solveur : il manque des camions (ou des rotations) pour la ville. À reprendre avec la vraie flotte de la mairie.
- La limite par défaut du test en direct est 1 s (`vrp_time_limit_s`), relevée automatiquement pour les grandes instances (1 s par 300 points, au plus 8 s).
- L'écart de 1 s à la meilleure connue mesure ce que coûte la réponse rapide pendant la démonstration ; relancer avec une limite plus longue pour le plan définitif.

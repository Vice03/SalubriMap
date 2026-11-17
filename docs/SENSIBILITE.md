<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Sensibilité du modèle à agents

Généré par `scripts/sensibilite.py` le 2026-11-17 — Zone pilote, plan v137, horizon 90 jours, 2 graines par point, 3282 simulations en 497 s. Ne pas modifier à la main : relancer le script.

## Paramètres étudiés

| Paramètre | Bornes | Source des bornes |
|---|---|---|
| Déchets par habitant (kg/j) (`kg_per_person_day`) | 0,4 – 0,9 | 0,6 annoncé par la mairie ; ±50 % selon quartier |
| Taux d'abonnement initial (`subscription_rate`) | 0,2 – 0,5 | hypothèse 35 %, aucune enquête |
| Prix de l'abonnement (FCFA/mois) (`fee_fcfa_month`) | 500 – 3 000 | tarifs observés 1 000 à 2 500 |
| Propension de base à jeter (log-cote) (`p0`) | -2,5 – -0,5 | hypothèse |
| Effet de la distance au-delà de la marche (/m) (`slope_dist`) | 0,002 – 0,008 | hypothèse |
| Dissuasion d'un contrôle Laabal (`laabal_deterrence`) | 0,2 – 0,8 | hypothèse |
| Poids de la norme sociale de l'îlot (`beta_norme`) | 0 – 4 | hypothèse |
| Pannes de camion (par jour) (`breakdown_rate`) | 0,01 – 0,1 | 2 % par défaut ; parc vieillissant |

## 1. Criblage de Morris (μ*, unités de la sortie)

μ* = effet moyen absolu quand le paramètre parcourt les 2/3 de son intervalle. Plus il est grand, plus le paramètre compte.

| Paramètre | Tonnes jetées en dépôt sauvage | Tonnes collectées par camion | Coût de la mairie à la tonne | Taux d'abonnement final |
|---|---|---|---|---|
| Déchets par habitant (kg/j) | 1 919 | 509 | 981 | 0,0364 |
| Taux d'abonnement initial | 49,4 | 62,7 | 33,8 | 0,124 |
| Prix de l'abonnement (FCFA/mois) | 57,9 | 62,5 | 59,9 | 0,125 |
| Propension de base à jeter (log-cote) | 298 | 82,2 | 43,4 | 0,0061 |
| Effet de la distance au-delà de la marche (/m) | 41,2 | 46,8 | 31,9 | 0,0075 |
| Dissuasion d'un contrôle Laabal | 71,8 | 41,3 | 32,9 | 0,0041 |
| Poids de la norme sociale de l'îlot | 76,2 | 49,6 | 38,9 | 0,007 |
| Pannes de camion (par jour) | 253 | 272 | 139 | 0,0065 |

## 2. Indices de Sobol sur les 4 paramètres les plus influents (dépôts sauvages)

S1 = part de la variance de la sortie due au paramètre seul ; ST = part totale, interactions comprises. Entre crochets : intervalle de confiance à 95 % (bootstrap). Avec peu d'échantillons, les intervalles sont larges : l'ordre des paramètres compte plus que les valeurs.

### Tonnes jetées en dépôt sauvage

Hasard propre au modèle : 0,1 % de la variance.

| Paramètre | S1 | ST |
|---|---|---|
| Déchets par habitant (kg/j) | 0,94 [0,798 ; 1,09] | 0,919 [0,801 ; 1,05] |
| Propension de base à jeter (log-cote) | 0,002 [-0,015 ; 0,017] | 0,008 [0,007 ; 0,01] |
| Pannes de camion (par jour) | 0,052 [0,015 ; 0,088] | 0,037 [0,031 ; 0,046] |
| Poids de la norme sociale de l'îlot | 0,003 [-0,006 ; 0,015] | 0,005 [0,004 ; 0,006] |

### Tonnes collectées par camion

Hasard propre au modèle : 0,9 % de la variance.

| Paramètre | S1 | ST |
|---|---|---|
| Déchets par habitant (kg/j) | 0,681 [0,547 ; 0,83] | 0,741 [0,602 ; 0,862] |
| Propension de base à jeter (log-cote) | -0,02 [-0,041 ; 0,006] | 0,022 [0,018 ; 0,027] |
| Pannes de camion (par jour) | 0,141 [0,044 ; 0,24] | 0,235 [0,189 ; 0,287] |
| Poids de la norme sociale de l'îlot | -0,022 [-0,046 ; 0,005] | 0,024 [0,019 ; 0,03] |

### Coût de la mairie à la tonne

Hasard propre au modèle : 0,1 % de la variance.

| Paramètre | S1 | ST |
|---|---|---|
| Déchets par habitant (kg/j) | 0,856 [0,677 ; 1,03] | 0,848 [0,722 ; 0,972] |
| Propension de base à jeter (log-cote) | 0 [-0,009 ; 0,007] | 0,003 [0,002 ; 0,004] |
| Pannes de camion (par jour) | 0,028 [-0,007 ; 0,062] | 0,029 [0,02 ; 0,04] |
| Poids de la norme sociale de l'îlot | 0,002 [-0,006 ; 0,01] | 0,003 [0,002 ; 0,004] |

### Taux d'abonnement final

Hasard propre au modèle : 14,9 % de la variance.

| Paramètre | S1 | ST |
|---|---|---|
| Déchets par habitant (kg/j) | 0,829 [0,687 ; 1,01] | 0,903 [0,758 ; 1,03] |
| Propension de base à jeter (log-cote) | -0,024 [-0,072 ; 0,024] | 0,079 [0,064 ; 0,1] |
| Pannes de camion (par jour) | -0,029 [-0,08 ; 0,023] | 0,068 [0,056 ; 0,081] |
| Poids de la norme sociale de l'îlot | -0,006 [-0,05 ; 0,044] | 0,076 [0,06 ; 0,097] |

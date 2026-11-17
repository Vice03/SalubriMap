<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Évaluation du masquage

Généré par `scripts/eval_masquage.py` — **Jeu public de contrôle (WIDER Face + plaques Roboflow) — pas Ouagadougou**, 120 images, 115.4 ms par photo (médiane, serveur, chaîne téléphone). Critères : `scripts/eval_masquage.py` (zone masquée si ≥ 70 % de sa surface est pixellisée ; détection juste si IoU ≥ 0,3 ; visages < 20 px et plaques < 10 px de haut ignorés). Cibles : rappel ≥ 0,95 visages, ≥ 0,90 plaques.

## Téléphone seul

| Type | Rappel | Précision | Cible | Atteinte | Zones | Ignorées |
|---|---|---|---|---|---|---|
| visage | 0,933 | 0,812 | 0,950 | **non** | 404 | 425 |
| plaque | 0,935 | 0,881 | 0,900 | oui | 62 | 1 |

| Type | Petites (< 40 px) | Moyennes (40–100 px) | Grandes (≥ 100 px) |
|---|---|---|---|
| visage | 0,875 (182/208) | 0,993 (149/150) | 1,000 (46/46) |
| plaque | 0,917 (33/36) | 0,958 (23/24) | 1,000 (2/2) |

## Téléphone + seconde passe du serveur

| Type | Rappel | Précision | Cible | Atteinte | Zones | Ignorées |
|---|---|---|---|---|---|---|
| visage | 0,938 | 0,824 | 0,950 | **non** | 404 | 425 |
| plaque | 0,935 | 0,702 | 0,900 | oui | 62 | 1 |

| Type | Petites (< 40 px) | Moyennes (40–100 px) | Grandes (≥ 100 px) |
|---|---|---|---|
| visage | 0,885 (184/208) | 0,993 (149/150) | 1,000 (46/46) |
| plaque | 0,917 (33/36) | 0,958 (23/24) | 1,000 (2/2) |

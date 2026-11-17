# Rapport de répétition de l'épreuve

Généré le 17/11/2026 20:39 UTC — API http://localhost:8088, OSRM down.

## Signalements piégés

Jeu de pièges : `routes-synthetiques_batiments-synthetiques`

| Piège | Attendu | Obtenu | Règles | Résultat |
|---|---|---|---|---|
| trap-001-control | probable  | probable (100) | — | ✅ |
| trap-002-control | probable  | probable (100) | — | ✅ |
| trap-003-control | probable  | probable (100) | — | ✅ |
| trap-004-control | probable  | probable (100) | — | ✅ |
| trap-005-control | probable  | probable (100) | — | ✅ |
| trap-006-r1-first | probable  | probable (100) | — | ✅ |
| trap-007-r1-dup | to_review R1 | to_review (60) | R1 | ✅ |
| trap-008-r1-first | probable  | probable (100) | — | ✅ |
| trap-009-r1-dup | to_review R1 | to_review (60) | R1 | ✅ |
| trap-010-r1-first | probable  | probable (100) | — | ✅ |
| trap-011-r1-dup | to_review R1 | to_review (60) | R1 | ✅ |
| trap-012-r2-source | probable  | probable (100) | — | ✅ |
| trap-013-r2-identical | rejected R2 | rejected (30) | R2 | ✅ |
| trap-014-r2-source | probable  | probable (100) | — | ✅ |
| trap-015-r2-recompressed | to_review/rejected R2 | to_review (50) | R2 | ✅ |
| trap-016-r3-exif-gps | probable/to_review R3 | probable (70) | R3 | ✅ |
| trap-017-r4-exif-old | probable R4 | probable (80) | R4 | ✅ |
| trap-018-r5-bobo | rejected R5 | rejected (0) | R5 | ✅ |
| trap-019-r5-koudougou | rejected R5 | rejected (0) | R5 | ✅ |
| trap-020-r5-golfe | rejected R5 | rejected (0) | R5 | ✅ |
| trap-021-r6-building | to_review/rejected R6 | to_review (50) | R6 | ✅ |
| trap-022-r6-building | to_review/rejected R6 | to_review (50) | R6 | ✅ |
| trap-023-r6-building | to_review/rejected R6 | to_review (50) | R6 | ✅ |
| trap-024-r7-reservoir | rejected R7 | rejected (0) | R7 | ✅ |
| trap-025-r7-reservoir | rejected R7 | rejected (0) | R7 | ✅ |
| trap-026-r7-river | to_review/rejected R7 | to_review (55) | R7 | ✅ |
| trap-027-r8-zero | rejected R8 | rejected (0) | R5, R8 | ✅ |
| trap-028-r8-rounded | probable/to_review R8 | probable (75) | R8 | ✅ |
| trap-029-r8-accuracy | probable R8 | probable (85) | R8 | ✅ |
| trap-030-r8-copied-point | to_review/rejected R8 | to_review (60) | R8 | ✅ |
| trap-031-r9-first | probable  | probable (100) | — | ✅ |
| trap-032-r9-jump | to_review/probable/rejected R9 | to_review (60) | R9 | ✅ |
| trap-033-r10-burst | probable  | probable (100) | — | ✅ |
| trap-034-r10-burst | probable  | probable (100) | — | ✅ |
| trap-035-r10-burst | probable  | probable (100) | — | ✅ |
| trap-036-r10-burst | probable  | probable (100) | — | ✅ |
| trap-037-r10-burst | probable  | probable (100) | — | ✅ |
| trap-038-r10-burst | probable  | probable (100) | — | ✅ |
| trap-039-r10-burst | probable  | probable (100) | — | ✅ |
| trap-040-r10-burst | probable  | probable (100) | — | ✅ |
| trap-041-r10-burst | probable  | probable (100) | — | ✅ |
| trap-042-r10-burst | probable  | probable (100) | — | ✅ |
| trap-043-r10-burst | probable/to_review R10 | probable (70) | R10 | ✅ |
| trap-044-r10-burst | probable/to_review R10 | probable (70) | R10 | ✅ |
| trap-045-r10-comment | probable  | probable (100) | — | ✅ |
| trap-046-r10-comment | probable  | probable (100) | — | ✅ |
| trap-047-r10-comment | probable  | probable (100) | — | ✅ |
| trap-048-r10-comment | probable  | probable (100) | — | ✅ |
| trap-049-r10-comment | probable/to_review R10 | probable (70) | R10 | ✅ |
| trap-050-r11-dark | probable R11 | probable (80) | R11 | ✅ |
| trap-051-r11-small | probable R11 | probable (80) | R11 | ✅ |
| trap-052-r12-truck-light | probable R12 | probable (90) | R12 | ✅ |
| trap-053-r12-medical | probable R12 | probable (90) | R12 | ✅ |
| trap-054-combined | rejected R2 R6 | rejected (0) | R2, R6 | ✅ |

Dépotoirs consolidés avant/après : 195 → 195 ✅

## Changements de paramètres

| Étape | Événement | Étapes recalculées | En cache | Durée serveur | Durée totale | Points inchangés | Déplacement moyen / max | Tournées (Jaccard) | Δ coût | Couverture avant → après | Invariants |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 camions en panne | fleet_changed | E5, E6, E7 | E1, E2, E3, E4 | 1.13 s | 1.29 s | 100 % | 0.0 / 0.0 m | 0.015 | 38263 | 100 % → 100 % | ✅ |
| Saison des pluies | season_changed | E2, E4, E5, E6, E7 | E1, E3 | 1.16 s | 1.29 s | 100 % | 0.0 / 0.0 m | 0.145 | 67626 | 100 % → 100 % | ✅ |
| Secteur nouveau (répétition) | zone_changed | E2, E3, E4, E5, E6, E7 | E1 | 3.57 s | 3.79 s | 100 % | 0.0 / 0.0 m | 0.208 | 65724 | 100 % → 99 % | ✅ |
| Budget −30 % | budget_changed | E6, E7 | E1, E2, E3, E4, E5 | 0.24 s | 0.48 s | 100 % | 0.0 / 0.0 m | 1.0 | 0 | 99 % → 99 % | ✅ |
| Réparation de BF-01 | fleet_changed | E5, E6, E7 | E1, E2, E3, E4 | 1.23 s | 1.43 s | 100 % | 0.0 / 0.0 m | 0.031 | 78044 | 99 % → 99 % | ✅ |
| Retour en saison sèche | season_changed | E2, E4, E5, E6, E7 | E1, E3 | 1.25 s | 1.38 s | 100 % | 0.0 / 0.0 m | 0.137 | -24562 | 99 % → 99 % | ✅ |
| Deux modifications en 100 ms | subscription_changed | E7 | E1, E2, E3, E4, E5, E6 | 0.00 s | 0.24 s | 100 % | 0.0 / 0.0 m | 1.0 | 0 | 99 % → 99 % | ✅ |

Ce qui change et pourquoi :

- **Saison des pluies** : aucun point ne bouge (exigé : 100 %), la pluie ne change pas où sont les bacs. Les tournées, elles, sont refaites : distances plus longues (graphe OSRM « pluie » ou détour ×1,5 sans OSRM), vitesse ×0,7 sur les voies inondables et +15 % de déchets mouillés (E2). Les nouvelles tournées évitent les voies coupées et tiennent dans les journées des chauffeurs ; c'est attendu qu'elles diffèrent beaucoup (Jaccard bas).

## Perturbations au hasard (comme un jury)

Graine 2026, 10 changements tirés dans `perturbations.parametres`, enchaînés. Bornes : points inchangés ≥ 70 %, déplacement moyen sur tous les points ≤ 30 m, perte de couverture ≤ 0 % quand le paramètre ne touche pas au placement.

| # | Paramètre → valeur | Points inchangés | Déplacement des points déplacés, moyen / max | Déplacement moyen, tous points | Tournées (Jaccard) | Couverture avant → après | Résultat |
|---|---|---|---|---|---|---|---|
| 1 | `collection_point_capacity_t` → 2.479 | 98 % | 160.7 / 160.7 m | 2.4 m | 0.267 | 100 % → 100 % | ✅ |
| 2 | `walk_distance_max_m` → 347.08 | 100 % | 0.0 / 0.0 m | 0.0 m | 0.317 | 100 % → 100 % | ✅ |
| 3 | `collection_point_capacity_t` → 3.326 | 100 % | 0.0 / 0.0 m | 0.0 m | 0.062 | 100 % → 100 % | ✅ |
| 4 | `waste_kg_per_person_day` → 0.668 | 99 % | 173.6 / 173.6 m | 2.4 m | 0.116 | 100 % → 100 % | ✅ |
| 5 | `subscription_rate` → 0.435 | 100 % | 0.0 / 0.0 m | 0.0 m | 1.0 | 100 % → 100 % | ✅ |
| 6 | `walk_distance_max_m` → 376.36 | 100 % | 0.0 / 0.0 m | 0.0 m | 1.0 | 100 % → 100 % | ✅ |
| 7 | `truck_breakdown_rate_per_day` → 0.063 | 100 % | 0.0 / 0.0 m | 0.0 m | 1.0 | 100 % → 100 % | ✅ |
| 8 | `waste_kg_per_person_day` → 0.604 | 100 % | 0.0 / 0.0 m | 0.0 m | 0.106 | 100 % → 100 % | ✅ |
| 9 | `budget_factor` → 1.03 | 100 % | 0.0 / 0.0 m | 0.0 m | 1.0 | 100 % → 100 % | ✅ |
| 10 | `collection_point_capacity_t` → 2.431 | 96 % | 228.2 / 304.3 m | 9.4 m | 0.153 | 100 % → 100 % | ✅ |

**Résultat : tout est vert.**

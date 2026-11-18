# Rapport de répétition de l'épreuve

Généré le 18/11/2026 07:18 UTC — API http://localhost:8088, OSRM down.

## Signalements piégés

Jeu de pièges : `routes-osm_batiments-reels`

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
| trap-025-r7-reservoir | rejected R7 | rejected (0) | R5, R7 | ✅ |
| trap-026-r7-river | to_review/rejected R7 | rejected (0) | R5, R7 | ✅ |
| trap-027-r8-zero | rejected R8 | rejected (0) | R5, R8 | ✅ |
| trap-028-r8-rounded | probable/to_review R8 | probable (75) | R8 | ✅ |
| trap-029-r8-accuracy | probable R8 | probable (85) | R8 | ✅ |
| trap-030-r8-copied-point | to_review/rejected R8 | to_review (60) | R8 | ✅ |
| trap-031-r9-first | probable  | probable (100) | — | ✅ |
| trap-032-r9-jump | to_review/probable/rejected R9 | probable (100) | — | ❌ |
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

Dépotoirs consolidés avant/après : 174 → 174 ✅

## Changements de paramètres

| Étape | Événement | Étapes recalculées | En cache | Durée serveur | Durée totale | Points inchangés | Déplacement moyen / max | Tournées (Jaccard) | Δ coût | Couverture avant → après | Invariants |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 camions en panne | fleet_changed | E5, E6, E7 | E1, E2, E3, E4 | 1.18 s | 1.42 s | 100 % | 0.0 / 0.0 m | 0.069 | 47272 | 96 % → 96 % | ✅ |
| Saison des pluies | season_changed | E2, E4, E5, E6, E7 | E1, E3 | 1.36 s | 1.59 s | 100 % | 0.0 / 0.0 m | 0.116 | -61201 | 96 % → 96 % | ✅ |
| Secteur nouveau (répétition) | zone_changed | E2, E3, E4, E5, E6, E7 | E1 | 5.19 s | 7.11 s | 100 % | 0.0 / 0.0 m | 0.019 | 151622 | 96 % → 98 % | ❌ 5.2 s > 5 s |
| Budget −30 % | budget_changed | E6, E7 | E1, E2, E3, E4, E5 | 0.24 s | 0.62 s | 100 % | 0.0 / 0.0 m | 1.0 | 0 | 98 % → 98 % | ✅ |
| Réparation de BF-01 | fleet_changed | E5, E6, E7 | E1, E2, E3, E4 | 1.25 s | 1.51 s | 100 % | 0.0 / 0.0 m | 0.082 | 65723 | 98 % → 98 % | ✅ |
| Retour en saison sèche | season_changed | E2, E4, E5, E6, E7 | E1, E3 | 1.25 s | 1.49 s | 100 % | 0.0 / 0.0 m | 0.036 | -26656 | 98 % → 98 % | ✅ |
| Deux modifications en 100 ms | subscription_changed | E7 | E1, E2, E3, E4, E5, E6 | 0.00 s | 0.39 s | 100 % | 0.0 / 0.0 m | 1.0 | 0 | 98 % → 98 % | ✅ |

Ce qui change et pourquoi :

- **Saison des pluies** : aucun point ne bouge (exigé : 100 %), la pluie ne change pas où sont les bacs. Les tournées, elles, sont refaites : distances plus longues (graphe OSRM « pluie » ou détour ×1,5 sans OSRM), vitesse ×0,7 sur les voies inondables et +15 % de déchets mouillés (E2). Les nouvelles tournées évitent les voies coupées et tiennent dans les journées des chauffeurs ; c'est attendu qu'elles diffèrent beaucoup (Jaccard bas).

## Perturbations au hasard (comme un jury)

Graine 2026, 10 changements tirés dans `perturbations.parametres`, enchaînés. Bornes : points inchangés ≥ 70 %, déplacement moyen sur tous les points ≤ 30 m, perte de couverture ≤ 0 % quand le paramètre ne touche pas au placement.

| # | Paramètre → valeur | Points inchangés | Déplacement des points déplacés, moyen / max | Déplacement moyen, tous points | Tournées (Jaccard) | Couverture avant → après | Résultat |
|---|---|---|---|---|---|---|---|
| 1 | `collection_point_capacity_t` → 2.479 | 100 % | 0.0 / 0.0 m | 0.0 m | 0.259 | 96 % → 96 % | ✅ |
| 2 | `walk_distance_max_m` → 347.08 | 100 % | 0.0 / 0.0 m | 0.0 m | 1.0 | 96 % → 99 % | ✅ |
| 3 | `collection_point_capacity_t` → 3.326 | 100 % | 0.0 / 0.0 m | 0.0 m | 0.34 | 99 % → 99 % | ✅ |
| 4 | `waste_kg_per_person_day` → 0.668 | 100 % | 0.0 / 0.0 m | 0.0 m | 0.154 | 99 % → 99 % | ✅ |
| 5 | `subscription_rate` → 0.435 | 100 % | 0.0 / 0.0 m | 0.0 m | 1.0 | 99 % → 99 % | ✅ |
| 6 | `walk_distance_max_m` → 376.36 | 100 % | 0.0 / 0.0 m | 0.0 m | 1.0 | 99 % → 100 % | ✅ |
| 7 | `truck_breakdown_rate_per_day` → 0.063 | 100 % | 0.0 / 0.0 m | 0.0 m | 1.0 | 100 % → 100 % | ✅ |
| 8 | `waste_kg_per_person_day` → 0.604 | 100 % | 0.0 / 0.0 m | 0.0 m | 0.203 | 100 % → 100 % | ✅ |
| 9 | `budget_factor` → 1.03 | 100 % | 0.0 / 0.0 m | 0.0 m | 1.0 | 100 % → 100 % | ✅ |
| 10 | `collection_point_capacity_t` → 2.431 | 100 % | 0.0 / 0.0 m | 0.0 m | 0.145 | 100 % → 100 % | ✅ |

**Résultat : des contrôles échouent.**

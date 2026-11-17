# Rapport de répétition de l'épreuve

Généré le 17/11/2026 13:45 UTC — API http://localhost:8088, OSRM down.

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
| 2 camions en panne | fleet_changed | E5, E6, E7 | E1, E2, E3, E4 | 1.14 s | 1.29 s | 100 % | 0.0 / 0.0 m | 0.028 | -41447 | 100 % → 100 % | ✅ |
| Saison des pluies | season_changed | E2, E4, E5, E6, E7 | E1, E3 | 1.16 s | 1.28 s | 100 % | 0.0 / 0.0 m | 0.114 | 18923 | 100 % → 100 % | ✅ |
| Secteur nouveau (répétition) | zone_changed | E2, E3, E4, E5, E6, E7 | E1 | 3.63 s | 4.07 s | 100 % | 0.0 / 0.0 m | 0.815 | 30 | 100 % → 97 % | ✅ |
| Budget −30 % | budget_changed | E6, E7 | E1, E2, E3, E4, E5 | 0.22 s | 0.44 s | 100 % | 0.0 / 0.0 m | 1.0 | 0 | 97 % → 97 % | ✅ |
| Réparation de BF-01 | fleet_changed | E5, E6, E7 | E1, E2, E3, E4 | 1.21 s | 1.39 s | 100 % | 0.0 / 0.0 m | 0.067 | 60287 | 97 % → 97 % | ✅ |
| Retour en saison sèche | season_changed | E2, E4, E5, E6, E7 | E1, E3 | 1.25 s | 1.41 s | 100 % | 0.0 / 0.0 m | 0.141 | -13962 | 97 % → 97 % | ✅ |
| Deux modifications en 100 ms | subscription_changed | E7 | E1, E2, E3, E4, E5, E6 | 0.00 s | 0.25 s | 100 % | 0.0 / 0.0 m | 1.0 | 0 | 97 % → 97 % | ✅ |

**Résultat : tout est vert.**

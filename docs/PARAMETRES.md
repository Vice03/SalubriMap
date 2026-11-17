<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Paramètres

Généré par `python -m salubri_api.params doc` depuis `data/communes/ouagadougou/params_schema.json` — ne pas modifier à la main. Les valeurs de départ sont dans `params_default.json` ; chaque scénario les copie et Salubri Sim permet de les changer. Une valeur hors de l'intervalle plausible est refusée au chargement.

**Charger les valeurs de la mairie** (une commande, avec rapport des différences) :

```bash
docker compose exec api python -m salubri_api.params import /chemin/mairie.json --simulation
```

Le fichier ne contient que les clés à changer, par exemple `{"budget_fcfa_month": 31000000, "waste_kg_per_person_day": 0.55, "validation": {"duplicate_radius_m": 25}}`. `--a-blanc` affiche les différences sans rien écrire.

Sources : **mairie** (donnée à obtenir ou obtenue), **littérature** (référence citée), **choix technique** ou **hypothèse** (avec justification, à remplacer dès qu'une donnée existe).

## Plan et simulation

| Clé | Paramètre | Unité | Intervalle plausible | Défaut | Source | Utilisé par |
|---|---|---|---|---|---|---|
| `population_factor` | Facteur de population | × | 0,5 – 3 | 1 | hypothèse : 1 = populations de quartiers.geojson ; >1 pour une croissance ou un recensement plus récent | E2 demande, simulation |
| `waste_kg_per_person_day` | Déchets par habitant | kg/hab/jour | 0,3 – 1,2 | 0,6 | mairie de Ouagadougou citée par Sidwaya (≈ 0,6 kg/hab/j) ; à confirmer par pesée (SENSIBILITE.md : paramètre le plus influent) | E2 demande, E3 placement, simulation |
| `subscription_rate` | Taux d'abonnement à la pré-collecte | part | 0,05 – 0,8 | 0,35 | hypothèse : 35 %, aucune enquête disponible ; à mesurer auprès des associations de pré-collecte | simulation |
| `subscription_fee_fcfa_month` | Tarif d'abonnement | FCFA/mois | 500 – 5 000 | 1 500 | hypothèse : 1 500 FCFA, ordre de grandeur des tarifs pratiqués par les pré-collecteurs (1 000 à 2 500) | simulation |
| `precollector_capacity_t` | Capacité d'un pré-collecteur | t par tournée | 0,3 – 3 | 1,2 | hypothèse : charrette ou tricycle de 1 à 2 m³ | simulation |
| `precollector_frequency_per_week` | Passages de pré-collecte | par semaine | 1 – 7 | 2 | hypothèse : 2 passages par semaine | simulation |
| `precollector_cost_fcfa_month` | Coût d'un pré-collecteur | FCFA/mois | 20 000 – 200 000 | 60 000 | hypothèse : salaire, entretien de la charrette ; 60 000 FCFA | simulation |
| `collection_point_capacity_t` | Capacité d'un point de regroupement | t | 0,5 – 10 | 2,5 | hypothèse : bac de 6 m³ ≈ 2,5 t (densité 0,4 t/m³) | E3 placement, E5 tournées, simulation |
| `collection_point_max` | Nombre maximum de points | points | 1 – 500 | 80 | mairie : nombre de bacs ou de sites disponibles ; 80 par défaut pour la démo | E3 placement |
| `pickup_frequency_per_week` | Enlèvements par camion | par semaine | 1 – 7 | 2 | hypothèse : 2 enlèvements par semaine et par point | E3 placement, E5 tournées, simulation |
| `walk_distance_max_m` | Distance de marche acceptable | m | 100 – 800 | 300 | hypothèse : 300 m, valeur courante des schémas de gestion des déchets (à confirmer par enquête ménages) | E3 placement, simulation |
| `season` | Saison | dry ou rain | dry / rain | dry | fiche du défi : scénario saison des pluies | E2 demande (+15 %), E4 distances, simulation |
| `flood_speed_factor` | Vitesse en saison des pluies | facteur | 0,3 – 1 | 0,7 | hypothèse : × 0,7 sur les vitesses, voies en terre presque impraticables | E4 distances |
| `truck_breakdown_rate_per_day` | Taux de panne des camions | par camion et par jour | 0 – 0,2 | 0,02 | hypothèse : 2 % ; à remplacer par l'historique du parc (SENSIBILITE.md : 2ᵉ paramètre le plus influent sur le tonnage collecté) | simulation |
| `budget_fcfa_month` | Budget mensuel de la collecte | FCFA/mois | 1 000 000 – 500 000 000 | 2,5e+07 | hypothèse : 25 M FCFA, à remplacer par le budget fourni par la mairie | simulation |
| `fuel_cost_fcfa_per_km` | Coût du carburant | FCFA/km | 150 – 1 500 | 450 | hypothèse : ≈ 0,6 L/km à ~750 FCFA/L | simulation, coût des tournées |
| `cleanup_capacity_t_day` | Nettoyage des dépotoirs | t/jour | 0 – 100 | 12 | hypothèse : services techniques de la mairie, 12 t/jour | simulation |
| `laabal_operations_per_week` | Opérations de la brigade Laabal | par semaine | 0 – 14 | 3 | hypothèse : 3 descentes par semaine ; aucun chiffre publié | simulation |
| `laabal_deterrence` | Effet dissuasif d'un contrôle Laabal | 0 à 1 | 0 – 1 | 0,5 | hypothèse : −50 % de dépôts pendant 21 jours ; aucun chiffre publié | simulation |
| `horizon_days` | Horizon de simulation | jours | 7 – 365 | 90 | choix d'étude : 90 jours = un trimestre | simulation |
| `seed` | Graine aléatoire | entier | 0 – 2 147 483 647 | 42 | choix technique : reproductibilité | simulation, E3 placement (k-means) |
| `vrp_time_limit_s` | Temps de calcul des tournées | s | 0,2 – 30 | 1 | choix technique : 1 s pour le test en direct (BENCHMARK_TOURNEES.md) | E5 tournées |
| `ilot_size_buildings` | Bâtiments par îlot | bâtiments | 5 – 500 | 30 | choix technique : ~30 concessions par îlot | E1 îlots |
| `sim_mode` | Modèle de simulation | agents ou agrege | agents / agrege | agents | choix technique : SIMULATION_ODD.md | simulation |
| `placement_time_limit_s` | Temps de calcul du placement | s | 0,5 – 60 | 2 | choix technique : 2 s pour le test en direct | E3 placement |
| `placement_stability_m` | Stabilité des points | m de marche équivalents | 0 – 2 000 | 300 | hypothèse : déplacer un point coûte comme faire marcher sa charge 300 m de plus | E3 placement |

## Règles de validation des signalements

| Clé | Paramètre | Unité | Intervalle plausible | Défaut | Source | Utilisé par |
|---|---|---|---|---|---|---|
| `duplicate_radius_m` | Rayon de doublon | m | 5 – 200 | 30 | hypothèse : 30 m, précision GPS d'un téléphone en ville | R1 doublon |
| `duplicate_window_h` | Fenêtre de doublon | h | 1 – 720 | 72 | hypothèse : 72 h | R1 doublon |
| `phash_max_hamming` | Écart maximal de pHash | bits sur 64 | 0 – 20 | 8 | littérature : seuil usuel 8–10 pour des copies d'une même image (Zauner, 2010) ; test sur photos masquées (MASQUAGE.md) | R2 photo réutilisée |
| `exif_gps_max_m` | Écart GPS photo / signalement | m | 50 – 5 000 | 500 | hypothèse : 500 m | R3 lieu de la photo |
| `exif_max_age_days` | Âge maximal de la photo | jours | 1 – 365 | 30 | hypothèse : 30 jours | R4 date de la photo |
| `zone_buffer_m` | Marge autour de la commune | m | 0 – 5 000 | 500 | hypothèse : 500 m | R5 hors zone |
| `building_min_confidence` | Confiance minimale des bâtiments | 0 à 1 | 0,5 – 1 | 0,7 | Open Buildings (Google) : 0,7 = seuil « haute précision » recommandé | R6 dans un bâtiment |
| `building_small_m2` | Petit bâtiment | m² | 10 – 200 | 40 | hypothèse : en dessous, souvent un abri ou une cour | R6 dans un bâtiment |
| `building_large_m2` | Grand bâtiment | m² | 50 – 2 000 | 200 | hypothèse : au-dessus, un dépôt sur une cour reste peu probable | R6 dans un bâtiment |
| `waterway_buffer_m` | Marge autour des cours d'eau | m | 0 – 50 | 8 | hypothèse : 8 m | R7 dans l'eau |
| `big_water_m2` | Grande étendue d'eau | m² | 1 000 – 1 000 000 | 10 000 | hypothèse : 1 ha | R7 dans l'eau |
| `gps_accuracy_max_m` | Précision GPS maximale | m | 10 – 1 000 | 150 | hypothèse : 150 m | R8 faux GPS |
| `same_point_m` | Même point exact | m | 0,1 – 10 | 1 | hypothèse : 1 m : coordonnées recopiées | R8 faux GPS |
| `max_speed_kmh` | Vitesse impossible | km/h | 30 – 300 | 120 | hypothèse : 120 km/h entre deux signalements d'un même téléphone | R9 vitesse impossible |
| `spam_per_hour` | Signalements par heure | par téléphone | 3 – 100 | 10 | hypothèse : 10 | R10 pourriel |
| `spam_block_factor` | Facteur de blocage | × spam_per_hour | 1 – 10 | 3 | hypothèse : refus 429 au-delà de 3 × spam_per_hour | limite d'envoi (lot A3) |
| `spam_same_comment` | Même commentaire répété | fois | 2 – 50 | 5 | hypothèse : 5 | R10 pourriel |
| `luminance_var_min` | Variance de luminance minimale | niveaux de gris² | 0 – 500 | 25 | hypothèse : 25 : photo noire ou blanche | R11 photo sans information |
| `photo_min_side_px` | Petit côté minimal de la photo | px | 50 – 2 000 | 200 | hypothèse : 200 px | R11 photo sans information |
| `truck_photo_min_bytes` | Taille minimale d'une photo « camion » | octets | 1 000 – 1 000 000 | 50 000 | hypothèse : 50 ko | R12 cohérence du type |
| `medical_poi_radius_m` | Rayon autour des centres de santé | m | 50 – 2 000 | 300 | hypothèse : 300 m | R12 cohérence du type |
| `probable_min` | Score « probable » | points | 0 – 100 | 70 | choix de conception : RULES.md | score de validation |
| `review_min` | Score « à vérifier » | points | 0 – 100 | 40 | choix de conception : RULES.md | score de validation |

## Paramètres de comportement du modèle à agents

Propres à la simulation, hors de ce fichier : `apps/api/salubri_api/services/simulation/abm/params.py`, décrits et justifiés dans `docs/SIMULATION_ODD.md` § 7 ; leur influence est mesurée dans `docs/SENSIBILITE.md`.

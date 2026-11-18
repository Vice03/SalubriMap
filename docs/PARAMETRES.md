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
| `waste_kg_per_person_day` | Déchets par habitant | kg/hab/jour | 0,3 – 1,2 | 0,6 | mairie de Ouagadougou citée par Sidwaya (≈ 0,6 kg/hab/j) ; à confirmer par pesée (SIMULATION_SENSIBILITE.md : paramètre le plus influent) | E2 demande, E3 placement, simulation |
| `subscription_rate` | Taux d'abonnement à la pré-collecte | part | 0,05 – 0,8 | 0,35 | hypothèse : 35 %, aucune enquête disponible ; à mesurer auprès des associations de pré-collecte | simulation |
| `subscription_fee_fcfa_month` | Tarif d'abonnement | FCFA/mois | 500 – 5 000 | 1 500 | hypothèse : 1 500 FCFA, ordre de grandeur des tarifs pratiqués par les pré-collecteurs (1 000 à 2 500) | simulation |
| `precollector_capacity_t` | Capacité d'un pré-collecteur | t par tournée | 0,3 – 3 | 1,2 | hypothèse : charrette ou tricycle de 1 à 2 m³ | simulation |
| `precollector_frequency_per_week` | Passages de pré-collecte | par semaine | 1 – 7 | 2 | hypothèse : 2 passages par semaine | simulation |
| `precollector_cost_fcfa_month` | Coût d'un pré-collecteur | FCFA/mois | 20 000 – 200 000 | 60 000 | hypothèse : salaire, entretien de la charrette ; 60 000 FCFA | simulation |
| `collection_point_capacity_t` | Capacité d'un point de regroupement | t | 0,5 – 10 | 2,5 | hypothèse : bac de 6 m³ ≈ 2,5 t (densité 0,4 t/m³) | E3 placement, E5 tournées, simulation |
| `collection_point_max` | Nombre maximum de points | points | 1 – 500 | 80 | mairie : nombre de bacs ou de sites disponibles ; 80 par défaut pour la démo | E3 placement |
| `pickup_frequency_per_week` | Enlèvements par camion | par semaine | 1 – 7 | 2 | hypothèse : 2 enlèvements par semaine et par point | E3 placement, E5 tournées, simulation |
| `pickup_frequency_max_per_week` | Enlèvements par semaine, au plus | par semaine | 1 – 7 | 3 | hypothèse : un troisième passage hebdomadaire est possible avec la flotte existante (lundi, mercredi, vendredi) ; au-delà, ajouter des points ou des bacs | E3 placement, E5 tournées, simulation |
| `walk_distance_max_m` | Distance de marche acceptable | m | 100 – 800 | 300 | hypothèse : 300 m, valeur courante des schémas de gestion des déchets (à confirmer par enquête ménages) | E3 placement, simulation |
| `season` | Saison | dry ou rain | dry / rain | dry | fiche du défi : scénario saison des pluies | E2 demande (+15 %), E4 distances, simulation |
| `flood_speed_factor` | Vitesse en saison des pluies | facteur | 0,3 – 1 | 0,7 | hypothèse : × 0,7 sur les vitesses, voies en terre presque impraticables | E4 distances |
| `truck_breakdown_rate_per_day` | Taux de panne des camions | par camion et par jour | 0 – 0,2 | 0,02 | hypothèse : 2 % ; à remplacer par l'historique du parc (SIMULATION_SENSIBILITE.md : 2ᵉ paramètre le plus influent sur le tonnage collecté) | simulation |
| `budget_fcfa_month` | Budget mensuel de la collecte | FCFA/mois | 1 000 000 – 500 000 000 | 2,5e+07 | hypothèse : 25 M FCFA, à remplacer par le budget fourni par la mairie | simulation |
| `fuel_cost_fcfa_per_km` | Coût du carburant | FCFA/km | 150 – 1 500 | 450 | hypothèse : ≈ 0,6 L/km à ~750 FCFA/L ; ancien réglage, remplacé par prix du gasoil × consommation + entretien | simulation, coût des tournées |
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
| `fallback_detour_dry` | Détour routier sans OSRM, saison sèche | × vol d'oiseau | 1 – 3 | 1,35 | hypothèse (valeurs usuelles 1,2–1,4 en ville) ; à caler sur OSRM avec scripts/calibrer_detour.py (docs/DETOUR_CALIBRATION.md) | tournées (repli sans OSRM) |
| `fallback_detour_rain` | Détour routier sans OSRM, saison des pluies | × vol d'oiseau | 1 – 3 | 1,5 | hypothèse (voies inondables évitées) ; à caler sur le graphe OSRM « pluie » avec scripts/calibrer_detour.py | tournées (repli sans OSRM) |
| `work_start_h` | Début de journée des équipes | h | 0 – 23 | 8 | demande de l'équipe : équipes de 8 h à 18 h ; réglable | tournées |
| `work_end_h` | Fin de journée des équipes | h | 1 – 24 | 18 | demande de l'équipe : équipes de 8 h à 18 h ; réglable | tournées |
| `break_min` | Pause | min | 0 – 240 | 60 | hypothèse : 1 h de pause déduite de la journée | tournées |
| `work_days_per_week` | Jours travaillés par semaine | jours | 1 – 7 | 6 | hypothèse : lundi à samedi | tournées, simulation, coûts |
| `fuel_price_fcfa_l` | Prix du gasoil | FCFA/L | 300 – 1 500 | 750 | prix à la pompe au Burkina depuis le 10 août 2026 (675 → 750 FCFA/L, CIDPH ; Sidwaya, Burkina24) | coûts, simulation |
| `fuel_l_per_100km` | Consommation d'un camion benne | L/100 km | 15 – 100 | 40 | [HYPOTHÈSE] camion benne 8 t en ville (arrêts fréquents) ; à mesurer sur la flotte | coûts, simulation |
| `maintenance_fcfa_per_km` | Entretien et pneus | FCFA/km | 0 – 600 | 120 | [HYPOTHÈSE] à remplacer par les factures du garage municipal | coûts, simulation |
| `driver_salary_fcfa_month` | Salaire d'un chauffeur | FCFA/mois | 45 000 – 500 000 | 120 000 | [HYPOTHÈSE] chauffeur poids lourd ; SMIG 45 000 FCFA/mois (décret de janvier 2024) | coûts |
| `loader_salary_fcfa_month` | Salaire d'un ripeur | FCFA/mois | 45 000 – 300 000 | 60 000 | [HYPOTHÈSE] au-dessus du SMIG (45 000 FCFA/mois) | coûts |
| `loaders_per_truck` | Ripeurs par camion | personnes | 0 – 8 | 3 | [HYPOTHÈSE] 1 chauffeur + 3 ripeurs | coûts |
| `social_charges_rate` | Charges sociales patronales | part | 0 – 0,4 | 0,16 | [HYPOTHÈSE] ≈ 16 % (CNSS employeur) ; à confirmer | coûts |
| `truck_price_fcfa` | Prix d'un camion benne | FCFA | 10 000 000 – 200 000 000 | 5,5e+07 | [HYPOTHÈSE] benne 8 t neuve ; à remplacer par un devis | coûts |
| `truck_life_years` | Durée de vie d'un camion | ans | 2 – 20 | 8 | [HYPOTHÈSE] amortissement linéaire | coûts |
| `truck_insurance_fcfa_year` | Assurance et visite technique | FCFA/an | 0 – 10 000 000 | 1,2e+06 | [HYPOTHÈSE] | coûts |
| `bin_price_fcfa` | Prix d'un bac de regroupement | FCFA | 100 000 – 10 000 000 | 1,2e+06 | [HYPOTHÈSE] bac métallique 6 m³ ; à remplacer par un devis | coûts |
| `bin_life_years` | Durée de vie d'un bac | ans | 1 – 20 | 5 | [HYPOTHÈSE] | coûts |

## Comportements simulés (ménages, pré-collecteurs, brigade Laabal)

| Clé | Paramètre | Unité | Intervalle plausible | Défaut | Source | Utilisé par |
|---|---|---|---|---|---|---|
| `household_size` | Taille moyenne des ménages | personnes | 3 – 12 | 7 | INSD : ménages de 5 à 7 personnes à Ouagadougou ; 7 retenu, à confirmer avec le RGPH 2019 | simulation (agrégé, agents) |
| `ilots_per_precollector` | Îlots par pré-collecteur | îlots | 5 – 40 | 15 | hypothèse : une charrette sert ~15 îlots de ~30 concessions | simulation (agrégé, agents) |
| `p0` | Propension de base à jeter, point hors de portée | log-cote | -4 – 1 | -1,5 | calé sur le SDGD 2020 (docs/SIMULATION_CALIBRATION.md) | simulation (agrégé, agents) |
| `slope_dist` | Effet de la distance au-delà de la marche | log-cote par m | 0 – 0,02 | 0,004 | hypothèse : +0,4 de log-cote par 100 m de trop | simulation (agrégé, agents) |
| `slope_full` | Effet d'un point plein | log-cote | 0 – 3 | 0,5 | hypothèse :  | simulation (agrégé, agents) |
| `slope_rain` | Effet de la pluie | log-cote | 0 – 2 | 0,3 | hypothèse :  | simulation (agrégé, agents) |
| `rain_waste_factor` | Déchets en plus en saison des pluies | part | 0 – 0,5 | 0,15 | hypothèse : +15 % (déchets mouillés, plus lourds) | simulation, E2 demande |
| `sub_up` | Hausse mensuelle des abonnements si le service est régulier | part par mois | 0 – 0,2 | 0,02 | hypothèse :  | simulation (agrégé ; agents homogènes) |
| `sub_down` | Baisse mensuelle des abonnements si le service est irrégulier | part par mois | 0 – 0,2 | 0,03 | hypothèse :  | simulation (agrégé ; agents homogènes) |
| `regularity_ok` | Régularité jugée suffisante | part des passages faits | 0,5 – 1 | 0,8 | hypothèse :  | simulation (agrégé, agents) |
| `recurring_days` | Délai pour dire qu'un dépotoir revient | jours | 1 – 90 | 15 | hypothèse :  | simulation (agrégé, agents) |
| `sub_wait_days` | Attente d'un abonné avant de décider seul | jours de production | 1 – 14 | 4 | hypothèse : poubelle domestique pleine en ~4 jours | simulation (agrégé, agents) |
| `laabal_ilots_per_operation` | Îlots contrôlés par descente Laabal | îlots | 1 – 30 | 6 | hypothèse :  | simulation (agrégé, agents) |
| `laabal_watch_days` | Durée de l'effet d'un contrôle Laabal | jours | 1 – 90 | 21 | hypothèse :  | simulation (agrégé, agents) |
| `laabal_sub_boost` | Abonnements gagnés après un contrôle Laabal | part | 0 – 0,3 | 0,05 | hypothèse :  | simulation (agrégé, agents) |
| `heterogeneite` | Ménages différents (taille, revenu, distance) | oui / non | oui / non | oui | choix de modélisation (SIMULATION_ODD.md § 8 : non = contrôle de cohérence) | simulation (agents) |
| `revenu_parts` | Parts des classes de revenu (faible, moyen, élevé) | parts | 0 – 1 | 0,5 / 0,35 / 0,15 | hypothèse : aucune enquête de revenus utilisée | simulation (agents) |
| `revenu_fcfa_mois` | Revenu de référence par classe | FCFA/mois | 10 000 – 1 000 000 | 40 000 / 90 000 / 250 000 | hypothèse : SMIG ~45 000 FCFA ; ordres de grandeur | simulation (agents) |
| `sigma_production` | Dispersion de la production par ménage | écart-type log | 0 – 1 | 0,3 | hypothèse :  | simulation (agents) |
| `jitter_distance_m` | Écart de position du ménage dans l'îlot | m | 0 – 200 | 50 | hypothèse : îlot de ~30 concessions ≈ 100 m de côté | simulation (agents) |
| `alpha_porter` | Constante du choix « porter » quand le point est à portée | log-cote | 0 – 20 | 8 | choix de modélisation : porter est presque certain sans autre terme (P > 0,999) | simulation (agents) |
| `beta_dist_porter` | Effet de la distance sur « porter » | log-cote par 100 m | 0 – 3 | 0,3 | hypothèse :  | simulation (agents) |
| `beta_reg` | Effet de la régularité vécue (attendre le pré-collecteur) | log-cote | 0 – 10 | 2 | hypothèse :  | simulation (agents) |
| `beta_norme` | Poids de la norme sociale de l'îlot | log-cote | 0 – 10 | 2 | hypothèse : sensibilité faible (SIMULATION_SENSIBILITE.md) | simulation (agents) |
| `norme_reference` | Part de référence de voisins qui jettent | part | 0 – 1 | 0,2 | hypothèse :  | simulation (agents) |
| `beta_habitude` | Poids de l'habitude (refaire le choix de la veille) | log-cote | 0 – 5 | 0,5 | hypothèse :  | simulation (agents) |
| `a_abo` | Constante de l'abonnement mensuel | log-cote | -10 – 0 | -3,11 | calée pour retrouver sub_up au point de référence (SIMULATION_ODD.md § 7.1) | simulation (agents) |
| `a_desabo` | Constante du désabonnement mensuel | log-cote | -10 – 0 | -4,93 | calée pour retrouver sub_down au point de référence | simulation (agents) |
| `beta_reg_mois` | Effet de la régularité sur l'abonnement | log-cote | 0 – 20 | 4 | hypothèse :  | simulation (agents) |
| `beta_prix` | Effet du prix rapporté au revenu | log-cote par unité | 0 – 100 | 20 | hypothèse :  | simulation (agents) |
| `extension_marge` | Marge pour qu'un pré-collecteur reprenne des îlots | × coût | 1 – 5 | 1,5 | hypothèse :  | simulation (agents) |
| `extension_charge_max` | Charge maximale de la charrette pour s'étendre | part | 0 – 1 | 0,7 | hypothèse :  | simulation (agents) |
| `amende_fcfa` | Amende Laabal par ménage pris à jeter | FCFA | 0 – 100 000 | 5 000 | hypothèse : aucun barème publié trouvé | simulation (agents) |
| `priorite_recurrent` | Priorité de nettoyage d'un dépotoir récurrent | × | 1 – 5 | 1,3 | fiche du défi (récurrents en priorité) ; valeur hypothèse | simulation (agents) |

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

Ces comportements ne sont calés sur aucune enquête ; le SDGD 2020 ne suffit pas à caler `p0` et `slope_dist` (`docs/SIMULATION_CALIBRATION.md`). Leur influence est mesurée dans `docs/SIMULATION_SENSIBILITE.md`, leur rôle décrit dans `docs/SIMULATION_ODD.md` § 7.

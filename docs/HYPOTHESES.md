# Hypothèses (à confirmer avec la mairie ou le jury)

| # | Hypothèse | Valeur | Où la changer |
|---|---|---|---|
| H1 | Déchets produits par habitant | 0,6 kg/jour (ordre de grandeur cité par la mairie dans Sidwaya), +15 % en saison des pluies | `params_default.json` |
| H2 | Distance de marche acceptable vers un point ; capacité d'un point | 300 m ; 2,5 t (bac de 6 m³) | `params_default.json` |
| H3 | Flotte de démonstration | 8 camions (5 × 8 t, 3 × 12 t), dépôt unique au nord-est | `vehicles.csv`, `commune.json` |
| H4 | Position du dépôt (CTVD de Polesgo) | (−1,50 ; 12,47), approximative | `commune.json` → `depot` |
| H5 | Abonnement pré-collecte | 1 500 FCFA/mois, taux initial 35 % ; coût d'un pré-collecteur 60 000 FCFA/mois | `params_default.json` |
| H6 | Nettoyage des dépotoirs (services techniques de la mairie) | 12 t/jour | `params_default.json` |
| H6b | Brigade Laabal (police civique, ministère de la Sécurité, créée en juin 2025) : elle **ne ramasse pas**, elle contrôle, sensibilise et sanctionne | 3 opérations/semaine, 6 îlots inspectés par opération, effet dissuasif −50 % pendant 21 jours, +5 points d'abonnement sur l'îlot contrôlé, riverains contraints d'évacuer le dépôt vers leur point | `params_default.json`, `simulation/params.py` — hypothèse, aucun chiffre d'effet publié |
| H7 | Quartiers de démonstration | 24 polygones approximatifs, 35 000 à 65 000 habitants chacun | `quartiers.geojson` |
| H8 | Ville synthétique tant que les extraits réels manquent | grille de voies tous les 300 m, un marigot et trois barrages, une concession pour 25 habitants | `data/osm`, `data/open_buildings` |
| H9 | Comportement des ménages non abonnés | probabilité de dépôt sauvage σ(−1,5 + 0,004 × (distance − 300 m) + 0,5 si point plein + 0,3 en saison des pluies) | `services/simulation/params.py` |
| H10 | Réabonnement | +2 points/mois si ≥ 80 % des passages prévus ont eu lieu, −3 sinon | `services/simulation/params.py` |
| H11 | Fenêtres horaires | marchés 05 h–08 h, ailleurs 07 h–17 h ; 10 min par arrêt ; 8 h par tournée ; 2 rotations par camion | `services/plan/pipeline.py`, `planning/vrp.py` |
| H12 | Saison des pluies | vitesses × 0,7 ; pistes et voies en terre presque impraticables (OSRM) ; × 1,5 sur les distances à vol d'oiseau | `params_default.json`, `services/osrm/profiles/car_rain.lua` |
| H13 | Corroboration | 2 appareils différents, > 1 h d'écart, ≤ 30 m, même type → vérifié | `services/validation/engine.py` |
| H14 | Identifiants | UUID v4 (et non v7) | `models/__init__.py` |
| H15 | Le maximum de points (`collection_point_max`) borne un placement complet ; un nouveau quartier reçoit toujours les points dont il a besoin | | `planning/collection_points.py` |

## Référence officielle : SDGD Ouagadougou 2020

Source : *Actualisation du Schéma directeur de gestion des déchets solides de la ville de Ouagadougou*, rapport définitif phase 2 « Mise en place de la base de données » (Commune de Ouagadougou / AMGT, CID–CINTECH, financement BAD, mars 2020), enquête de terrain 2019 :

- 44 centres de collecte et de tri (CCT), 1 CTVD, 12 décharges encadrées par la DSPH, 58 décharges sauvages, 4 autres sites ;
- 13 secteurs sans aucun centre de collecte : 2, 8, 12, 13, 20, 31, 34, 35, 39, 40, 41, 45, 50 ;
- arrondissements les plus touchés par les décharges sauvages : 12, 1 et 6, puis 4 et 3.

`data/communes/ouagadougou/sdgd2020.geojson` : 115 sites numérisés depuis la carte « Répartition spatiale des décharges et CCT » (p. 29), par détection des symboles puis calage du contour de la commune sur la limite OSM (relation 5675756). Précision estimée ± 500 m ; couche de référence affichée sur la carte, non utilisée dans les calculs.

Utilisation dans les calculs (v0.2) :
- les décharges SDGD (sauvages, encadrées DSPH, autres) sont chargées comme **signalements officiels vérifiés** (`external_id = sdgd2020:…`, sans passer par les règles anti-pièges) et deviennent des dépotoirs ;
- les CCT existants qui desservent la zone active sont **gardés comme points de regroupement fixes** (paramètre « Garder les CCT existants », activé par défaut) ; l'algorithme n'ajoute des points que là où aucun CCT n'est à distance de marche.

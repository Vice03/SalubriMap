# Formats d'import (jeu de test du jury)

`POST /api/imports` (ou glisser-déposer dans Salubri Map). `dry_run=true` pour prévisualiser sans enregistrer ; `POST /api/imports/{id}/rollback` pour annuler.

## GeoJSON

`FeatureCollection` de `Point` (`[longitude, latitude]`). Propriétés reconnues, toutes facultatives :

| Propriété | Synonymes | Exemple |
|---|---|---|
| `waste_type` | `type`, `type_dechet` | `household`, `plastique`, `gravats`… |
| `volume_class` | `volume` | `cart`, `charrette`, `sac`… |
| `reported_at` | `date`, `datetime` | `2026-11-14T10:00:00Z` ou `14/11/2026 10:00` |
| `comment` | `commentaire`, `description` | |
| `device_id` | `appareil` | |
| `accuracy` | `precision`, `gps_accuracy_m` | `12` (mètres) |
| `photo` | `photo_path`, `image` | `photos/a.jpg` (dans le ZIP) ou `data:image/jpeg;base64,…` |
| `external_id` | `id` | identifiant du jury, renvoyé dans le rapport |

## CSV

UTF-8 (BOM accepté) ou Latin-1, séparateur `,` ou `;` détecté. Colonnes de coordonnées : `lat`/`lon`, `latitude`/`longitude` ou `y`/`x`, puis les mêmes propriétés que ci-dessus. Décimales avec point ou virgule.

## ZIP

Un `.geojson`/`.json`/`.csv` et des photos (`.jpg`, `.jpeg`, `.png`, `.webp`) n'importe où dans l'archive ; la propriété `photo` désigne le nom du fichier.

## Règles d'import

- Ligne sans coordonnées, coordonnées non numériques, date invalide → ligne **rejetée** avec un message en français.
- Latitude ∈ [−5 ; 0] et longitude ∈ [10 ; 14] → coordonnées **inversées**, corrigées, avertissement `coords_swapped`.
- Type ou volume inconnus → remplacés par `other` / `bag`, avertissement.
- Photo citée mais absente de l'archive → signalement importé sans photo, avertissement.
- Chaque ligne acceptée reçoit un score, un statut et ses règles déclenchées, exactement comme un signalement mobile.

Exemples : `data/jury/exemple_import.csv` (10 lignes dont 2 rejetées) et `data/jury/exemple_import.geojson` (dont une ligne inversée).

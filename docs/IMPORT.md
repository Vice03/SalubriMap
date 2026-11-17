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

## Fichiers d'autres outils (jeu caché du jury)

- **Noms de colonnes** : en plus des noms ci-dessus, les noms d'autres outils sont reconnus sans tenir compte des
  accents, majuscules et séparateurs (« Latitude_DD », « Catégorie de déchets », « Quantité estimée », « Date du
  signalement », « Observations », « _gps_latitude » de KoboToolbox…). La réponse donne `colonnes` : chaque
  colonne du fichier et le champ qu'elle remplit, `null` si elle est ignorée.
- **Systèmes de coordonnées** : un GeoJSON qui déclare son `crs` (« EPSG:32630 », « urn:ogc:def:crs:EPSG::32630 »)
  est converti en WGS 84. Des coordonnées en mètres sans `crs` (ou dans un CSV) sont rapportées au système qui
  les place près de la commune (UTM 30N, UTM 31N, Web Mercator) ; sinon le fichier est refusé avec un message.
  La réponse donne `crs` : ce qui a été lu ou deviné.
- **Doublons** : une ligne qui répète l'identifiant d'une ligne précédente, ou le même point à la même date avec
  le même type et le même commentaire, est refusée (« Doublon de la ligne N du fichier ») ; un identifiant déjà
  présent en base est refusé (« Déjà importé ») — réimporter le même fichier ne crée rien.
- **Hors de la commune** : la ligne entre et le signalement est rejeté par la règle R5, comme depuis Salubri Go ;
  l'avertissement de la ligne donne la distance aux quartiers.
- Jeu d'essai : `data/rehearsal/jeu_inedit/` (5 fichiers, testés par `apps/api/tests/test_import_inedit.py`).

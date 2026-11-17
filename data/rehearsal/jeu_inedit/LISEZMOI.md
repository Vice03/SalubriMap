<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Jeu d'import inédit (robustesse face au jeu caché du jury)

Cinq fichiers que l'import n'avait jamais vus, chacun avec un piège différent. Les coordonnées tombent dans la
zone de test (`tests/conftest.py`, quartier Q1) comme dans Ouagadougou. Résultat attendu : accepté avec un rapport
clair (correspondance des colonnes, système de coordonnées) ou refusé ligne par ligne avec un message en français.
Testé par `apps/api/tests/test_import_inedit.py`.

| Fichier | Piège | Attendu |
|---|---|---|
| `1_colonnes_autres.csv` | colonnes d'un tableur (« Latitude_DD », « Catégorie de déchets », « Quantité estimée »…), dates JJ/MM/AAAA, virgules décimales, une colonne inconnue | 3 lignes acceptées ; rapport : chaque colonne → champ, « Agent » ignorée |
| `2_utm30n.geojson` | coordonnées UTM 30N (EPSG:32630) déclarées dans `crs` | converties en WGS 84, 3 lignes acceptées, système indiqué |
| `3_champs_manquants.csv` | type et date vides, latitude absente, date illisible, type inconnu | 2 acceptées (type « autre » + avertissement), 2 refusées avec la raison |
| `4_doublons.geojson` | même identifiant deux fois, même point/date/type deux fois | 3 acceptées, 2 refusées « Doublon de la ligne N » ; réimport : « Déjà importé » |
| `5_hors_commune.csv` | Bobo-Dioulasso, Accra, (0, 0) | les 4 lignes entrent ; 3 signalements rejetés par la règle R5 (comme depuis Salubri Go, pour que le jury les retrouve « rejetés »), avec l'avertissement « Hors de la commune : à X km » |

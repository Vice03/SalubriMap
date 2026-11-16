# Extrait OpenStreetMap

- Fichier attendu : `ouaga.osm.pbf` (emprise : `bbox.geojson`, −1,70/12,25 → −1,35/12,50).
- Produit par `scripts/prepare_osm_extract.sh` à partir de Geofabrik (`africa/burkina-faso-latest.osm.pbf`) et `osmium extract`.
- Utilisé par le seed (voies, cours d'eau, plans d'eau, écoles, marchés, centres de santé, cimetières) et par OSRM.
- Licence : ODbL 1.0, © contributeurs OpenStreetMap. Noter la date de l'extrait dans `EXTRACT_DATE.txt`.

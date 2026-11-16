# Utiliser Salubri dans une autre commune

```bash
python scripts/new_commune.py koudougou --name Koudougou --bbox=-2.40,12.22,-2.33,12.29 --depot=-2.36,12.27
```

Le script crée `data/communes/koudougou/` avec des gabarits à remplir :

| Fichier | Contenu |
|---|---|
| `commune.json` | nom, emprise (`bbox`), dépôt des camions, scénarios de départ |
| `quartiers.geojson` | un polygone par quartier/secteur avec `name` et `population` |
| `params_default.json` | paramètres fixés avec la mairie + seuils de validation |
| `vehicles.csv` | la flotte : `label,kind,capacity_t,cost_per_km,fixed_cost_day,shift_start,shift_end` |
| `reports_field.geojson` | (facultatif) signalements collectés sur le terrain |

Préparer les données ouvertes de la zone (adapter `data/osm/bbox.geojson`) : `scripts/prepare_osm_extract.sh` et `python scripts/prepare_open_buildings.py`, puis :

```bash
SALUBRI_COMMUNE=koudougou docker compose run --rm seed python -m salubri_api.seed.run
SALUBRI_COMMUNE=koudougou docker compose up -d
```

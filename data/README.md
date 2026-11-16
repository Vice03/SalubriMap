# Données

| Dossier | Contenu | Licence |
|---|---|---|
| `communes/<slug>/` | commune, quartiers, paramètres, flotte, signalements de démonstration | CC0 (démonstration) |
| `osm/` | extrait OpenStreetMap de la zone (`ouaga.osm.pbf`) et son emprise | ODbL 1.0, © contributeurs OpenStreetMap |
| `open_buildings/` | bâtiments Google Open Buildings v3 filtrés (`ouaga_buildings.csv.gz`) | CC-BY-4.0 / ODbL |
| `photos_demo/` | photos de démonstration (générées à la volée par le seed, rien à stocker) | CC0 |
| `jury/` | exemples de fichiers d'import et leur format | CC0 |
| `rehearsal/` | jeu de signalements piégés et séquence de changements pour la répétition | CC0 |

## Charger les vraies données (avant la finale, avec Internet)

```bash
./scripts/prepare_osm_extract.sh                 # nécessite osmium-tool
python scripts/prepare_open_buildings.py         # ~ quelques centaines de Mo téléchargés, quelques Mo gardés
docker compose run --rm seed python -m salubri_api.seed.run --force
make gen-traps                                   # régénère les pièges à partir des vraies données
```

Sans ces fichiers, le seed génère une **ville synthétique** (voies, marigot, barrages, bâtiments, écoles, marchés, centres de santé) pour que l'application fonctionne de bout en bout. Les deux sources sont indépendantes : on peut charger les vraies voies OSM et garder des bâtiments synthétiques, ou l'inverse.

Régénérer les données de démonstration : `python scripts/gen_demo_data.py` (déterministe, graine 42).

#!/usr/bin/env sh
# SPDX-License-Identifier: AGPL-3.0-or-later
# Download Burkina Faso from Geofabrik and clip it to the Ouagadougou work area (run ONCE, with Internet,
# BEFORE the final; commit data/osm/ouaga.osm.pbf). Needs osmium-tool (apt install osmium-tool / brew install osmium-tool).
set -e
cd "$(dirname "$0")/.."
mkdir -p data/osm
SRC=data/osm/burkina-faso-latest.osm.pbf
if [ ! -f "$SRC" ]; then
  curl -L --fail -o "$SRC" https://download.geofabrik.de/africa/burkina-faso-latest.osm.pbf
fi
osmium extract --overwrite -p data/osm/bbox.geojson "$SRC" -o data/osm/ouaga.osm.pbf
date -u +"Extrait du %Y-%m-%d (Geofabrik, © contributeurs OpenStreetMap, ODbL)" > data/osm/EXTRACT_DATE.txt
ls -lh data/osm/ouaga.osm.pbf
echo "Ensuite : docker compose run --rm seed python -m salubri_api.seed.run --force"

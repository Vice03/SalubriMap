#!/bin/sh
# SPDX-License-Identifier: AGPL-3.0-or-later
# Build the OSRM graph from data/osm/ouaga.osm.pbf on first start (kept in the /osrm volume), then serve it.
# Without the extract the container waits instead of failing: the API falls back to straight-line distances.
set -e
PROFILE="${OSRM_PROFILE:-/opt/car.lua}"
PBF_SRC="/data/osm/${OSRM_PBF:-ouaga.osm.pbf}"
NAME="$(basename "$PROFILE" .lua)"
WORK="/osrm/$NAME"
mkdir -p "$WORK"
while [ ! -s "$PBF_SRC" ]; do
  echo "[osrm] $PBF_SRC absent : lancer scripts/prepare_osm_extract.sh. Nouvelle tentative dans 60 s."
  sleep 60
done
STAMP="$WORK/source.sha"
NEW_SHA="$(sha1sum "$PBF_SRC" "$PROFILE" | sha1sum | cut -c1-40)"
if [ ! -f "$WORK/ouaga.osrm.mldgr" ] || [ "$(cat "$STAMP" 2>/dev/null)" != "$NEW_SHA" ]; then
  echo "[osrm] construction du graphe ($NAME)…"
  cp "$PBF_SRC" "$WORK/ouaga.osm.pbf"
  osrm-extract -p "$PROFILE" "$WORK/ouaga.osm.pbf"
  osrm-partition "$WORK/ouaga.osrm"
  osrm-customize "$WORK/ouaga.osrm"
  echo "$NEW_SHA" > "$STAMP"
fi
exec osrm-routed --algorithm mld --max-table-size 1000 "$WORK/ouaga.osrm"

#!/usr/bin/env sh
# Efface la base et repart de zéro (utile avant chaque répétition)
cd "$(dirname "$0")/.." && docker compose --profile osrm down -v && rm -f data/osm/.seeded_osm && exec "$(dirname "$0")/start.sh"

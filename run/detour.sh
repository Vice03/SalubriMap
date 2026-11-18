#!/usr/bin/env bash
# Salubri - cale le facteur de détour du repli sans OSRM contre OSRM (saison sèche et saison des pluies).
# Le script tourne dans le conteneur de l'API (qui joint osrm et osrm_rain) ; les résultats reviennent dans docs/.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose ps --status running -q api | grep -q . || { echo "Salubri ne tourne pas : ./run/start.sh d'abord"; exit 1; }
docker compose exec -T api sh -c "mkdir -p /tmp/cal/scripts /tmp/cal/docs"
docker compose cp scripts/calibrer_detour.py api:/tmp/cal/scripts/calibrer_detour.py
[ -f docs/detour_calibration.json ] && docker compose cp docs/detour_calibration.json api:/tmp/cal/docs/detour_calibration.json
docker compose exec -T api python /tmp/cal/scripts/calibrer_detour.py --osrm http://osrm:5000 --saison dry
docker compose exec -T api python /tmp/cal/scripts/calibrer_detour.py --osrm http://osrm_rain:5000 --saison rain
docker compose cp api:/tmp/cal/docs/DETOUR_CALIBRATION.md docs/DETOUR_CALIBRATION.md
docker compose cp api:/tmp/cal/docs/detour_calibration.json docs/detour_calibration.json
echo "Résultat : docs/DETOUR_CALIBRATION.md"

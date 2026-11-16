#!/usr/bin/env sh
# Salubri — démarrage (Linux / macOS)
cd "$(dirname "$0")/.." || exit 1
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker n'est pas installé : https://docs.docker.com/get-docker/"; exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker est installé mais ne tourne pas : démarrez Docker Desktop puis relancez."; exit 1
fi
if [ ! -f apps/web/dist/index.html ]; then
  if command -v pnpm >/dev/null 2>&1; then
    echo "Construction de l'interface web…"; pnpm install && pnpm --filter web build
  else
    echo "Interface web non construite et pnpm absent : la page d'attente sera affichée."
  fi
fi
PROFILES=""
[ -s data/osm/ouaga.osm.pbf ] && PROFILES="--profile osrm"
docker compose $PROFILES up --build -d || exit 1
if [ -s data/osm/ouaga.osm.pbf ] && [ ! -f data/osm/.seeded_osm ]; then
  echo "Premier chargement des vraies rues OpenStreetMap (1 à 2 minutes)..."
  docker compose run --rm seed python -m salubri_api.seed.run --force && echo charge > data/osm/.seeded_osm
fi
printf "Attente de l'API"
i=0
until curl -fs http://localhost/api/health >/dev/null 2>&1; do
  i=$((i+1)); [ $i -gt 120 ] && { echo; echo "L'API ne répond pas : docker compose logs api seed"; exit 1; }
  printf "."; sleep 2
done
echo; echo "Salubri est prêt : http://localhost  (API : http://localhost/api/docs)"
( command -v xdg-open >/dev/null && xdg-open http://localhost ) || ( command -v open >/dev/null && open http://localhost ) || true

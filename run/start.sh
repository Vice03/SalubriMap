#!/usr/bin/env sh
# Salubri — démarrage (Linux / macOS)
cd "$(dirname "$0")/.." || exit 1
# Diagnostic (Docker, ports, disque, carte) : arrêt avec un message clair si quelque chose manque
sh "$(dirname "$0")/doctor.sh" || { echo; echo "Corrigez le point en ÉCHEC ci-dessus puis relancez run/start.sh"; exit 1; }
# Vraies rues par défaut quand c'est possible : proposer l'extrait OSM si Internet et osmium sont là
if [ ! -s data/osm/ouaga.osm.pbf ] && command -v osmium >/dev/null 2>&1 && curl -fsI -m 5 https://download.geofabrik.de >/dev/null 2>&1; then
  printf "Télécharger les vraies rues de Ouagadougou (OpenStreetMap, ~100 Mo) ? [o/N] "
  read -r rep
  case "$rep" in o|O|oui) sh scripts/prepare_osm_extract.sh || echo "Téléchargement impossible : ville synthétique.";; esac
fi
# Hors démonstration (SALUBRI_DEMO_MODE=false dans .env) : secrets générés une fois dans .env
sh "$(dirname "$0")/secrets.sh" || exit 1
# Les interfaces sont construites dans l'image Docker « web » : pas besoin de Node ici.
PROFILES=""
[ -s data/osm/ouaga.osm.pbf ] && PROFILES="--profile osrm"
# On ne reconstruit que nos images (API, interfaces) : OSRM et PostGIS viennent de registres (ghcr.io, Docker Hub)
# parfois injoignables ; déjà présentes, elles servent telles quelles (compose ne construit que celles qui manquent).
docker compose build seed api web || echo "Attention : reconstruction impossible (réseau ?) — démarrage avec les images déjà présentes."
docker compose $PROFILES up -d || exit 1
if [ -s data/osm/ouaga.osm.pbf ] && [ ! -f data/osm/.seeded_osm ]; then
  echo "Premier chargement des vraies rues OpenStreetMap (1 à 2 minutes)..."
  docker compose run --rm seed python -m salubri_api.seed.run --force && echo charge > data/osm/.seeded_osm
  # jeu de pièges de la répétition propre à cette carte (scripts/rehearse.py le choisit tout seul)
  docker compose run --rm -v "$PWD/scripts:/app/scripts:ro" -v "$PWD/data/rehearsal:/app/data/rehearsal" seed \
    python scripts/gen_traps.py || echo "Jeu de pièges non généré : la répétition utilisera le jeu par défaut."
fi
printf "Attente de l'API"
i=0
until curl -fs "http://localhost:${WEB_PORT:-80}/api/health" >/dev/null 2>&1; do
  i=$((i+1)); [ $i -gt 120 ] && { echo; echo "L'API ne répond pas : docker compose logs api seed"; exit 1; }
  printf "."; sleep 2
done
echo; echo "Salubri est prêt : http://localhost  (Salubri Go : http://localhost/go/ , API : http://localhost/api/docs)"
echo "Compte de démonstration (SALUBRI_DEMO_MODE=true) : demo / ouaga2026. Production : voir .env.example"
( command -v xdg-open >/dev/null && xdg-open http://localhost ) || ( command -v open >/dev/null && open http://localhost ) || true

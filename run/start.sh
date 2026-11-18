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
# Module « Assistant » (optionnel) : trouver un modèle local, ou en proposer un adapté à la machine (run/llm_detect.py)
if grep -Eq '^SALUBRI_ASSISTANT_ENABLED=(true|1)' .env 2>/dev/null; then
  if command -v python3 >/dev/null 2>&1; then python3 run/llm_detect.py "$@" || true
  else echo "Assistant : Python 3 absent, détection du modèle local sautée."; fi
  grep -q '^SALUBRI_LLM_URL=http://ollama:' .env 2>/dev/null && PROFILES="$PROFILES --profile assistant"
fi
# On ne reconstruit que nos images (API, interfaces) : OSRM et PostGIS viennent de registres (ghcr.io, Docker Hub)
# parfois injoignables ; déjà présentes, elles servent telles quelles (compose ne construit que celles qui manquent).
docker compose build seed api web || echo "Attention : reconstruction impossible (réseau ?) — démarrage avec les images déjà présentes."
# rues OSM chargees AVANT le demarrage de l'API (sinon blocage mutuel sur la base)
if [ -s data/osm/ouaga.osm.pbf ] && [ ! -f data/osm/.seeded_osm ]; then
  echo "Premier chargement des vraies rues OpenStreetMap (3 à 6 minutes selon la machine : ne pas interrompre)..."
  # libère la base : une ancienne API ou un ancien seed encore actifs tiennent des verrous
  docker compose stop api web seed >/dev/null 2>&1 || true
  docker compose run --rm seed python -m salubri_api.seed.run --force && echo charge > data/osm/.seeded_osm
  # jeu de pièges de la répétition propre à cette carte (scripts/rehearse.py le choisit tout seul)
  docker compose run --rm -v "$PWD/scripts:/app/scripts:ro" -v "$PWD/data/rehearsal:/app/data/rehearsal" seed \
    python /app/scripts/gen_traps.py || echo "Jeu de pièges non généré : la répétition utilisera le jeu par défaut."
fi
docker compose $PROFILES up -d || exit 1
printf "Attente de l'API"
i=0
WEBP=$(grep -E '^WEB_PORT=' .env 2>/dev/null | tail -1 | cut -d= -f2-); WEBP=${WEBP:-80}
URL="http://localhost"; [ "$WEBP" = 80 ] || URL="http://localhost:$WEBP"
until curl -fs "$URL/api/health" >/dev/null 2>&1; do
  i=$((i+1)); [ $i -gt 120 ] && { echo; echo "L'API ne répond pas : docker compose logs api seed"; exit 1; }
  printf "."; sleep 2
done
echo; echo "Salubri est prêt : $URL  (Salubri Go : $URL/go/ , API : $URL/api/docs)"
if grep -q '^SALUBRI_DEMO_MODE=false' .env 2>/dev/null; then
  echo "Connexion mairie : identifiant admin, mot de passe $(grep -E '^SALUBRI_BOOTSTRAP_ADMIN_PASSWORD=' .env | tail -n 1 | cut -d= -f2-) (gardé dans .env)"
else
  echo "Comptes démo : admin / Salubri2026 (administrateur) ou demo / ouaga2026."
fi
# Adresse(s) du serveur pour l'application Android (même réseau Wi-Fi)
IPS=$( (hostname -I 2>/dev/null | tr ' ' '\n'; ifconfig 2>/dev/null | awk '/inet /{print $2}') | grep -E '^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)' | grep -v '^172\.17\.' | sort -u)
PSUF=""; [ "$WEBP" = 80 ] || PSUF=":$WEBP"
for ip in $IPS; do echo "Sur le téléphone, adresse du serveur : http://$ip$PSUF"; done
echo "Si le téléphone n'atteint pas le serveur, autorisez le port $WEBP sur le pare-feu de cet ordinateur."
echo "Windows (PowerShell en administrateur) : New-NetFirewallRule -DisplayName \"Salubri\" -Direction Inbound -Protocol TCP -LocalPort $WEBP -Action Allow -Profile Private"
( command -v xdg-open >/dev/null && xdg-open http://localhost ) || ( command -v open >/dev/null && open http://localhost ) || true
#!/usr/bin/env sh
# SPDX-License-Identifier: AGPL-3.0-or-later
# Salubri — diagnostic avant démarrage (Linux / macOS) : Docker, ports, disque, carte utilisée.
cd "$(dirname "$0")/.." || exit 1
ok=0
say() { printf '%-28s %s\n' "$1" "$2"; }
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then say "Docker" "OK ($(docker version -f '{{.Server.Version}}' 2>/dev/null))"
  else say "Docker" "ÉCHEC : installé mais arrêté — démarrez Docker Desktop"; ok=1; fi
else say "Docker" "ÉCHEC : absent — https://docs.docker.com/get-docker/"; ok=1; fi
mine=$(docker compose ps -q web 2>/dev/null)
# ports web lus dans .env (seuls ports publiés ; la base, l'API et Ollama restent sur le réseau interne de Docker)
envv() { v=$(grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2-); echo "${v:-$2}"; }
portbad=0
for spec in "$(envv WEB_PORT 80):WEB_PORT:8080" "$(envv WEB_TLS_PORT 8443):WEB_TLS_PORT:9443"; do
  p=${spec%%:*}; rest=${spec#*:}; var=${rest%%:*}; alt=${rest#*:}
  if (command -v ss >/dev/null && ss -ltn "sport = :$p" | grep -q LISTEN) || (command -v lsof >/dev/null && lsof -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1); then
    if [ -n "$mine" ]; then say "Port $p" "utilisé par Salubri (déjà lancé)"
    else
      say "Port $p" "ÉCHEC : déjà utilisé par un autre programme (Apache, nginx, Skype…)"
      say "" "Trouver le programme : sudo lsof -iTCP:$p -sTCP:LISTEN   (ou : sudo ss -ltnp | grep :$p)"
      say "" "Ou changer de port : ajouter $var=$alt dans le fichier .env, puis relancer"
      ok=1; portbad=1
    fi
  else say "Port $p" "libre"; fi
done
free_gb=$(df -Pk . | awk 'NR==2 {print int($4/1048576)}')
if [ "${free_gb:-0}" -lt 5 ]; then say "Disque" "ÉCHEC : ${free_gb} Go libres, 5 Go nécessaires (images Docker)"; ok=1
else say "Disque" "${free_gb} Go libres"; fi
if [ -s data/osm/ouaga.osm.pbf ]; then
  say "Carte" "vraies rues OpenStreetMap ($(cat data/osm/EXTRACT_DATE.txt 2>/dev/null | head -c 40)) + itinéraires OSRM"
else
  say "Carte" "ville synthétique (pas d'extrait data/osm/ouaga.osm.pbf)"
  if command -v osmium >/dev/null 2>&1 && curl -fsI -m 5 https://download.geofabrik.de >/dev/null 2>&1; then
    say "" "→ vraies rues possibles : scripts/prepare_osm_extract.sh (Internet et osmium présents)"
  fi
fi
[ -f .env ] && grep -Eq '^SALUBRI_DEMO_MODE=false' .env && say "Mode" "production (.env)" || say "Mode" "démonstration (comptes admin / demo)"
# module « Assistant » (optionnel) : moteur, modèle et palier de la machine ; jamais bloquant
command -v python3 >/dev/null 2>&1 && python3 run/llm_detect.py --doctor 2>/dev/null
exit $ok

#!/usr/bin/env sh
# Salubri — purge des signalements (garde les données de référence) ; demande de taper PURGER
cd "$(dirname "$0")/.." || exit 1
exec docker compose exec api python -m salubri_api.purge signalements "$@"

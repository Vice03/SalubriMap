#!/usr/bin/env sh
# Salubri — reconstruit le dossier livrable/ (les 6 livrables du défi) depuis les sources
cd "$(dirname "$0")/.." || exit 1
exec python3 scripts/livrable.py "$@"

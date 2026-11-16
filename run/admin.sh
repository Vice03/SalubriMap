#!/usr/bin/env sh
# SPDX-License-Identifier: AGPL-3.0-or-later
# Crée un compte administrateur (le mot de passe est demandé au clavier). Usage : run/admin.sh <login>
cd "$(dirname "$0")/.." || exit 1
[ -n "$1" ] || { echo "Usage : run/admin.sh <login>"; exit 1; }
exec docker compose run --rm seed python -m salubri_api.users add "$1" --role admin --name "$1"

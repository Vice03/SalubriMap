#!/usr/bin/env sh
# SPDX-License-Identifier: AGPL-3.0-or-later
# Hors démonstration (SALUBRI_DEMO_MODE=false dans .env) : génère une fois le code de service et la clé de session
# manquants ou laissés à leur valeur de démonstration, les écrit dans .env et les affiche une seule fois.
cd "$(dirname "$0")/.." || exit 1
[ -f .env ] || exit 0
grep -Eq '^[[:space:]]*SALUBRI_DEMO_MODE[[:space:]]*=[[:space:]]*false[[:space:]]*$' .env || exit 0
secret() { od -An -N32 -tx1 /dev/urandom | tr -d ' \n'; }
created=""
for name in SALUBRI_ADMIN_TOKEN SALUBRI_SECRET_KEY; do
  v=$(grep -E "^[[:space:]]*$name[[:space:]]*=" .env | tail -n 1 | cut -d= -f2- | tr -d '[:space:]')
  if [ -z "$v" ] || [ "$v" = "ouaga2026" ] || [ ${#v} -lt 16 ]; then
    new=$(secret)
    grep -Ev "^[[:space:]]*$name[[:space:]]*=" .env > .env.tmp && mv .env.tmp .env
    echo "$name=$new" >> .env
    created="$created  $name=$new
"
  fi
done
if [ -n "$created" ]; then
  echo
  echo "Mode production : secrets générés et enregistrés dans .env (affichés une seule fois) :"
  printf "%s" "$created"
  echo "Gardez le fichier .env privé. Créez le premier compte admin : run/admin.sh <login>"
  echo
fi

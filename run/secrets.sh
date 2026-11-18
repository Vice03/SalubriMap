#!/usr/bin/env sh
# SPDX-License-Identifier: AGPL-3.0-or-later
# Hors démonstration (défaut ; SALUBRI_DEMO_MODE=true dans .env l'active) : génère une fois le code de service, la clé de
# session et le mot de passe du premier admin (compte « admin ») manquants, les écrit dans .env.
cd "$(dirname "$0")/.." || exit 1
[ -f .env ] || touch .env
grep -Eq '^[[:space:]]*SALUBRI_DEMO_MODE[[:space:]]*=[[:space:]]*true[[:space:]]*$' .env && exit 0
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
bp=$(grep -E "^[[:space:]]*SALUBRI_BOOTSTRAP_ADMIN_PASSWORD[[:space:]]*=" .env | tail -n 1 | cut -d= -f2- | tr -d '[:space:]')
if [ ${#bp} -lt 8 ]; then
  newp=$(od -An -N12 -tx1 /dev/urandom | tr -d ' \n' | cut -c1-12)
  grep -Ev "^[[:space:]]*SALUBRI_BOOTSTRAP_ADMIN_PASSWORD[[:space:]]*=" .env > .env.tmp && mv .env.tmp .env
  echo "SALUBRI_BOOTSTRAP_ADMIN_PASSWORD=$newp" >> .env
  created="$created  SALUBRI_BOOTSTRAP_ADMIN_PASSWORD=$newp
"
fi
if [ -n "$created" ]; then
  echo
  echo "Premier lancement : secrets générés et enregistrés dans .env :"
  printf "%s" "$created"
  echo "Connexion mairie : identifiant admin, mot de passe SALUBRI_BOOTSTRAP_ADMIN_PASSWORD (relisible dans .env)."
  echo "Gardez le fichier .env privé."
  echo
fi

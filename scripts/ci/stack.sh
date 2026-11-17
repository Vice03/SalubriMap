#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Job « stack » de .github/workflows/ci.yml, en local : clone neuf → docker compose up --build → interfaces
# servies → répétition → tests navigateur → arrêt. Efface la base de la pile (docker compose down -v) à la fin :
# ne pas lancer sur la machine de démonstration. KEEP=1 pour garder la pile.
set -euo pipefail
cd "$(dirname "$0")/../.."
PY="${PYTHON:-python}"
start=$(date +%s)
docker compose up --build -d
for _ in $(seq 1 120); do curl -fs http://localhost/api/health >/dev/null && break; sleep 5; done
curl -fs http://localhost/api/health
echo "Démarrage à froid : $(( $(date +%s) - start )) s"
curl -fs http://localhost/ | grep -q '/assets/index-'
curl -fs http://localhost/go/ | grep -q '/go/assets/index-'
curl -fsI http://localhost/ | grep -qi 'content-security-policy'
trap '[ "${KEEP:-0}" = 1 ] || docker compose down -v' EXIT
PYTHONPATH=apps/api SALUBRI_ADMIN_TOKEN=ouaga2026 $PY scripts/rehearse.py --api http://localhost
SALUBRI_URL=http://localhost $PY -m pytest -q tests/e2e

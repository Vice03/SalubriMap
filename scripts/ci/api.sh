#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Job « api » de .github/workflows/ci.yml, en local. Base PostGIS de test : SALUBRI_TEST_DATABASE_URL
# (défaut : salubri_test sur localhost). Outils : ceux de apps/api [dev] (versions épinglées).
set -euo pipefail
cd "$(dirname "$0")/../../apps/api"
export SALUBRI_TEST_DATABASE_URL="${SALUBRI_TEST_DATABASE_URL:-postgresql+psycopg://salubri:salubri@localhost:5432/salubri_test}"
PY="${PYTHON:-python}"
want=$(grep -o 'ruff==[0-9.]*' pyproject.toml | cut -d= -f3)
have=$($PY -m ruff --version | awk '{print $2}')
[ "$want" = "$have" ] || { echo "ruff $have installé, $want attendu : pip install ruff==$want"; exit 1; }
$PY -m ruff check salubri_api tests ../../scripts
$PY -m ruff format --check salubri_api tests ../../scripts
$PY -m pytest -q -p no:cacheprovider --cov=salubri_api --cov-report=term --cov-fail-under=91

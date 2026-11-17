#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Job « audit » de .github/workflows/ci.yml, en local : dépendances vulnérables (Python et JavaScript).
set -euo pipefail
cd "$(dirname "$0")/../.."
PY="${PYTHON:-python}"
req=$(mktemp)
$PY -c "import tomllib;print('\n'.join(tomllib.load(open('apps/api/pyproject.toml','rb'))['project']['dependencies']))" > "$req"
$PY -m pip_audit -r "$req"
pnpm audit --prod

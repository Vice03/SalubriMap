#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Job « front » de .github/workflows/ci.yml, en local (pnpm 9.12.0, Node 22).
set -euo pipefail
cd "$(dirname "$0")/../.."
pnpm install --frozen-lockfile
pnpm typecheck
pnpm lint
pnpm -r test
pnpm -r build

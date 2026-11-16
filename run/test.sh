#!/usr/bin/env sh
cd "$(dirname "$0")/.." || exit 1
docker compose up -d db && docker compose run --rm --no-deps api sh -c \
  "SALUBRI_TEST_DATABASE_URL=postgresql+psycopg://salubri:salubri@db:5432/salubri_test pytest -q"

#!/usr/bin/env sh
cd "$(dirname "$0")/.." || exit 1
docker compose run --rm --no-deps -v "$(pwd)/docs:/app/docs" api python /app/scripts/rehearse.py --api http://api:8000

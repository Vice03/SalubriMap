# SPDX-License-Identifier: AGPL-3.0-or-later
# Everything runs inside Docker: only Docker is needed on the machine.
COMPOSE ?= docker compose
API_RUN = $(COMPOSE) run --rm --no-deps api
TEST_DB = postgresql+psycopg://salubri:salubri@db:5432/salubri_test

.PHONY: up down reset logs seed reseed test test-api lint format traps rehearse bench gen-data gen-traps osm ci-api ci-front ci-audit ci-stack

up:            ## build and start everything (http://localhost)
	$(COMPOSE) up --build -d
	@echo "Salubri : http://localhost  —  API : http://localhost/api/docs"

down:          ## stop (data kept)
	$(COMPOSE) down

reset:         ## stop, wipe the database and start from scratch
	$(COMPOSE) down -v
	$(COMPOSE) up --build -d

logs:
	$(COMPOSE) logs -f --tail=100 api seed

seed:          ## (re)run the idempotent seed
	$(COMPOSE) run --rm seed

reseed:        ## force a full reload of the demo data
	$(COMPOSE) run --rm seed python -m salubri_api.seed.run --force

test: test-api ## all tests

test-api:      ## API tests against the PostGIS test database
	$(COMPOSE) up -d db
	$(API_RUN) sh -c "SALUBRI_TEST_DATABASE_URL=$(TEST_DB) pytest -q"

lint:
	$(API_RUN) ruff check salubri_api tests /app/scripts

format:
	$(API_RUN) ruff format salubri_api tests

gen-data:      ## regenerate data/communes/ouagadougou (synthetic demo set)
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/data:/app/data api python /app/scripts/gen_demo_data.py

gen-traps:     ## regenerate data/rehearsal/traps*.json from the loaded database
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/data:/app/data api python /app/scripts/gen_traps.py

traps:         ## import the trap set and check every expected verdict
	$(API_RUN) python /app/scripts/rehearse.py --api http://api:8000 --traps-only

rehearse:      ## full live-test rehearsal (traps + parameter changes), writes docs/REHEARSAL_REPORT.md
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/docs:/app/docs api python /app/scripts/rehearse.py --api http://api:8000

bench:         ## recompute timings per event type
	$(API_RUN) python /app/scripts/bench_pipeline.py --api http://api:8000

osm:           ## download + clip the OSM extract (needs Internet and osmium-tool)
	./scripts/prepare_osm_extract.sh

# --- Reproduire la CI en local (sans Docker sauf ci-stack ; outils épinglés de apps/api [dev], pnpm 9.12.0) ---
ci-api:        ## job « api » : ruff check + format, pytest avec couverture ≥ 91 % (PostGIS : SALUBRI_TEST_DATABASE_URL)
	bash scripts/ci/api.sh

ci-front:      ## job « front » : pnpm install, typecheck, lint, tests, builds
	bash scripts/ci/front.sh

ci-audit:      ## job « audit » : pip-audit et pnpm audit --prod
	bash scripts/ci/audit.sh

ci-stack:      ## job « stack » : docker compose up --build, répétition, e2e, puis down -v (efface la base de la pile)
	bash scripts/ci/stack.sh

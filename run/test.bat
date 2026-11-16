@echo off
cd /d "%~dp0\.."
docker compose up -d db
docker compose run --rm --no-deps api sh -c "SALUBRI_TEST_DATABASE_URL=postgresql+psycopg://salubri:salubri@db:5432/salubri_test pytest -q"
pause

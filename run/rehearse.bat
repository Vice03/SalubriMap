@echo off
cd /d "%~dp0\.."
docker compose run --rm --no-deps -v "%cd%\docs:/app/docs" api python /app/scripts/rehearse.py --api http://api:8000
pause

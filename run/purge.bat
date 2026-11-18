@echo off
REM Salubri - purge des signalements (garde les donnees de reference) ; demande de taper PURGER
cd /d "%~dp0\.."
docker compose exec api python -m salubri_api.purge signalements %*
exit /b %errorlevel%

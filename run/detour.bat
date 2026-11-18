@echo off
REM Salubri - cale le facteur de detour du repli sans OSRM contre OSRM (saison seche et saison des pluies).
REM Lance le script dans le conteneur de l'API (qui joint les conteneurs osrm et osrm_rain), puis
REM recupere docs\DETOUR_CALIBRATION.md et docs\detour_calibration.json. Salubri doit tourner.
cd /d "%~dp0\.."
docker compose ps --status running -q api >nul 2>nul
for /f %%i in ('docker compose ps --status running -q api 2^>nul') do set api=%%i
if not defined api ( echo Salubri ne tourne pas : lancez-le d'abord ^(choix 1 ou 2^). & exit /b 1 )
docker compose exec -T api sh -c "mkdir -p /tmp/cal/scripts /tmp/cal/docs"
docker compose cp scripts\calibrer_detour.py api:/tmp/cal/scripts/calibrer_detour.py
if exist docs\detour_calibration.json docker compose cp docs\detour_calibration.json api:/tmp/cal/docs/detour_calibration.json
echo Saison seche ^(OSRM osrm^) ...
docker compose exec -T api python /tmp/cal/scripts/calibrer_detour.py --osrm http://osrm:5000 --saison dry
if errorlevel 1 ( echo ECHEC : OSRM saison seche injoignable ou plan absent. & exit /b 1 )
echo Saison des pluies ^(OSRM osrm_rain^) ...
docker compose exec -T api python /tmp/cal/scripts/calibrer_detour.py --osrm http://osrm_rain:5000 --saison rain
docker compose cp api:/tmp/cal/docs/DETOUR_CALIBRATION.md docs\DETOUR_CALIBRATION.md
docker compose cp api:/tmp/cal/docs/detour_calibration.json docs\detour_calibration.json
echo.
echo Resultat : docs\DETOUR_CALIBRATION.md ^(recopier les facteurs cales dans params_default.json si besoin^).
exit /b 0

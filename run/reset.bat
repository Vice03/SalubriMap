@echo off
REM Efface la base et repart de zero (avant chaque repetition)
cd /d "%~dp0\.."
docker compose --profile osrm down -v
if exist "data\osm\.seeded_osm" del "data\osm\.seeded_osm"
call "%~dp0start.bat"

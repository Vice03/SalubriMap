@echo off
REM Salubri - demarrage (Windows). Double-cliquer.
cd /d "%~dp0\.."
where docker >nul 2>nul
if errorlevel 1 (
  echo Docker n'est pas installe : https://docs.docker.com/desktop/install/windows-install/
  pause & exit /b 1
)
docker info >nul 2>nul
if errorlevel 1 (
  echo Docker est installe mais ne tourne pas : demarrez Docker Desktop puis relancez.
  pause & exit /b 1
)
rem Les interfaces (apps/web, apps/go) sont construites dans l'image Docker "web" : pas besoin de Node ici.
rem Avec l'extrait OSM (scripts/prepare_osm_extract.sh) : vraies rues + calcul d'itineraires OSRM
set PROFILES=
if exist "data\osm\ouaga.osm.pbf" set PROFILES=--profile osrm
docker compose %PROFILES% up --build -d
if errorlevel 1 ( pause & exit /b 1 )
if exist "data\osm\ouaga.osm.pbf" if not exist "data\osm\.seeded_osm" (
  echo Premier chargement des vraies rues OpenStreetMap ^(1 a 2 minutes^)...
  docker compose run --rm seed python -m salubri_api.seed.run --force
  if not errorlevel 1 echo charge> "data\osm\.seeded_osm"
)
echo Attente de l'API...
set /a n=0
:wait
set /a n+=1
if %n% equ 15 echo (si http://localhost s ouvre deja dans le navigateur, Salubri tourne : vous pouvez fermer cette fenetre)
if %n% gtr 120 (
  echo L'API ne repond pas : docker compose logs api seed
  pause & exit /b 1
)
rem curl.exe (inclus dans Windows 10+) sur 127.0.0.1 sans proxy : PowerShell passait par le proxy systeme / IPv6 et ne voyait jamais l API
curl.exe -s -f -o nul -m 3 --noproxy "*" http://127.0.0.1/api/health >nul 2>nul || powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1/api/health -TimeoutSec 3) | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 ( timeout /t 2 /nobreak >nul & goto wait )
echo Salubri est pret : http://localhost   (Salubri Go : http://localhost/go/ , API : http://localhost/api/docs)
echo Code d acces mairie par defaut : ouaga2026  (a changer dans un fichier .env : SALUBRI_ADMIN_TOKEN=...)
start "" http://localhost

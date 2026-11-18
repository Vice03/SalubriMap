@echo off
setlocal EnableExtensions
REM Salubri - demarrage (Windows). Double-cliquer.
cd /d "%~dp0\.."
where docker >nul 2>nul
if errorlevel 1 (
  echo Docker n'est pas installe : https://docs.docker.com/desktop/install/windows-install/
  call :pauser & exit /b 1
)
docker info >nul 2>nul
if errorlevel 1 (
  echo Docker est installe mais ne tourne pas : demarrez Docker Desktop puis relancez.
  call :pauser & exit /b 1
)
rem Diagnostic (ports, disque, carte) : affiche un ECHEC lisible ; Docker est deja verifie ci-dessus
call "%~dp0doctor.bat"
if errorlevel 2 (
  echo.
  echo Un port web est deja utilise : voir ci-dessus ^(netstat -ano ^| findstr :PORT^), puis relancez.
  call :pauser & exit /b 1
)
if errorlevel 1 echo Attention : un point du diagnostic est en ECHEC ci-dessus, le demarrage peut echouer.
set "WEBP=80"
for /f "tokens=2 delims==" %%a in ('findstr /b /c:"WEB_PORT=" ".env" 2^>nul') do set "WEBP=%%a"
if "%WEBP%"=="80" ( set "URL=http://localhost" & set "LOC=http://127.0.0.1" ) else ( set "URL=http://localhost:%WEBP%" & set "LOC=http://127.0.0.1:%WEBP%" )
rem Les interfaces (apps/web, apps/go) sont construites dans l'image Docker "web" : pas besoin de Node ici.
rem Hors demonstration (SALUBRI_DEMO_MODE=false dans .env) : secrets generes une fois dans .env
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0secrets.ps1"
if errorlevel 1 ( echo Generation des secrets impossible : voir .env.example & call :pauser & exit /b 1 )
rem Avec l'extrait OSM (scripts/prepare_osm_extract.sh) : vraies rues + calcul d'itineraires OSRM
set PROFILES=
if exist "data\osm\ouaga.osm.pbf" set PROFILES=--profile osrm
rem Module "Assistant" (optionnel) : trouver un modele local, ou en proposer un adapte a la machine
findstr /b /r /c:"SALUBRI_ASSISTANT_ENABLED=true" .env >nul 2>nul
if not errorlevel 1 (
  where python >nul 2>nul && ( python run\llm_detect.py %* ) || echo Assistant : Python absent, detection du modele local sautee.
  findstr /b /c:"SALUBRI_LLM_URL=http://ollama:" .env >nul 2>nul && set PROFILES=%PROFILES% --profile assistant
)
rem On ne reconstruit que nos images (API, interfaces) : celles d'OSRM et de PostGIS viennent de registres
rem (ghcr.io, Docker Hub) parfois injoignables ; deja presentes, elles servent telles quelles.
docker compose build seed api web
if errorlevel 1 echo Attention : reconstruction impossible (reseau ?) - demarrage avec les images deja presentes.
rem Chargement des rues AVANT le demarrage de l'API (sinon les deux se bloquent mutuellement sur la base)
if exist "data\osm\ouaga.osm.pbf" if not exist "data\osm\.seeded_osm" (
  echo Premier chargement des vraies rues OpenStreetMap ^(3 a 6 minutes selon la machine : NE PAS INTERROMPRE^)...
  rem libere la base : une ancienne API ou un ancien seed encore actifs tiennent des verrous et bloquent le rechargement
  docker compose stop api web seed >nul 2>nul
  docker compose run --rm seed python -m salubri_api.seed.run --force
  if errorlevel 1 (
    echo Chargement des rues interrompu ou en echec : il sera retente au prochain lancement.
  ) else (
    echo charge> "data\osm\.seeded_osm"
    rem jeu de pieges de la repetition propre a cette carte
    docker compose run --rm -v "%CD%\scripts:/app/scripts:ro" -v "%CD%\data\rehearsal:/app/data/rehearsal" seed python /app/scripts/gen_traps.py
  )
)
docker compose %PROFILES% up -d
if errorlevel 1 ( call :pauser & exit /b 1 )
echo Attente de l'API...
set /a WAITN=0
:wait
set /a WAITN+=1
if %WAITN% equ 15 echo (si %URL% s ouvre deja dans le navigateur, Salubri tourne : vous pouvez fermer cette fenetre)
if %WAITN% gtr 120 (
  echo L'API ne repond pas : docker compose logs api seed
  call :pauser & exit /b 1
)
rem curl.exe (inclus dans Windows 10+) sur 127.0.0.1 sans proxy : PowerShell passait par le proxy systeme / IPv6 et ne voyait jamais l API
curl.exe -s -f -o nul -m 3 --noproxy "*" %LOC%/api/health >nul 2>nul || powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing %LOC%/api/health -TimeoutSec 3) | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 ( timeout /t 2 /nobreak >nul & goto wait )
echo Salubri est pret : %URL%   (Salubri Go : %URL%/go/ , API : %URL%/api/docs)
for /f "tokens=2 delims==" %%a in ('findstr /b /c:"SALUBRI_BOOTSTRAP_ADMIN_PASSWORD=" ".env" 2^>nul') do echo Connexion mairie : identifiant admin, mot de passe %%a ^(garde dans .env^)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0adresses.ps1" -Port %WEBP%
echo.
start "" %URL%
exit /b 0

:pauser
rem lance seul : on attend une touche ; depuis SALUBRI.bat (SALUBRI_NOPAUSE), le lanceur gere l'erreur
if not defined SALUBRI_NOPAUSE pause
exit /b 0

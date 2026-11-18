@echo off
setlocal EnableExtensions
REM Salubri - diagnostic avant demarrage (Windows) : Docker, ports, disque, carte utilisee.
cd /d "%~dp0\.."
set ok=0
where docker >nul 2>nul
if errorlevel 1 ( echo Docker            : ECHEC, absent - https://docs.docker.com/desktop/install/windows-install/ & set ok=1 & goto ports )
docker info >nul 2>nul
if errorlevel 1 ( echo Docker            : ECHEC, installe mais arrete - demarrez Docker Desktop & set ok=1 ) else ( echo Docker            : OK )
:ports
set mine=
for /f %%i in ('docker compose ps -q web 2^>nul') do set mine=%%i
rem ports web lus dans .env (seuls ports publies ; la base, l'API et Ollama restent sur le reseau interne de Docker)
set "WEBP=80"
set "TLSP=8443"
for /f "tokens=2 delims==" %%a in ('findstr /b /c:"WEB_PORT=" ".env" 2^>nul') do set "WEBP=%%a"
for /f "tokens=2 delims==" %%a in ('findstr /b /c:"WEB_TLS_PORT=" ".env" 2^>nul') do set "TLSP=%%a"
set portbad=
call :port %WEBP% WEB_PORT 8080
call :port %TLSP% WEB_TLS_PORT 9443
set free=
for /f %%g in ('powershell -NoProfile -Command "[math]::Floor((Get-PSDrive ((Get-Location).Drive.Name)).Free/1GB)" 2^>nul') do set free=%%g
if not defined free set free=99
if %free% LSS 5 ( echo Disque            : ECHEC, %free% Go libres, 5 Go necessaires & set ok=1 ) else ( echo Disque            : %free% Go libres )
if exist "data\osm\ouaga.osm.pbf" (
  echo Carte             : vraies rues OpenStreetMap + itineraires OSRM
) else (
  echo Carte             : ville synthetique ^(pas d'extrait data\osm\ouaga.osm.pbf, voir data\osm\README.md^)
)
findstr /r /c:"^SALUBRI_DEMO_MODE=true" .env >nul 2>nul && echo Mode              : demonstration ouverte (comptes demo et admin publics) || echo Mode              : production (compte admin, mot de passe dans .env)
rem module "Assistant" (optionnel) : moteur, modele et palier de la machine ; jamais bloquant
where python >nul 2>nul && python run\llm_detect.py --doctor
if defined portbad exit /b 2
exit /b %ok%

:port
netstat -ano | findstr /r /c:"TCP.*:%1 .*LISTENING" >nul
if errorlevel 1 ( echo Port %1           : libre & goto :eof )
if defined mine ( echo Port %1           : utilise par Salubri ^(deja lance^) & goto :eof )
echo Port %1           : ECHEC, deja utilise par un autre programme ^(Skype, IIS, Apache...^)
echo                     Trouver le programme : netstat -ano ^| findstr :%1
echo                     ^(derniere colonne = numero du programme ; puis : tasklist /fi "PID eq ce_numero"^)
echo                     Ou changer de port : ajouter %2=%3 dans le fichier .env, puis relancer
set ok=1
set portbad=1
goto :eof

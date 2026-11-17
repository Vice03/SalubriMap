@echo off
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
for %%p in (80 8443) do call :port %%p
set free=
for /f %%g in ('powershell -NoProfile -Command "[math]::Floor((Get-PSDrive ((Get-Location).Drive.Name)).Free/1GB)" 2^>nul') do set free=%%g
if not defined free set free=99
if %free% LSS 5 ( echo Disque            : ECHEC, %free% Go libres, 5 Go necessaires & set ok=1 ) else ( echo Disque            : %free% Go libres )
if exist "data\osm\ouaga.osm.pbf" (
  echo Carte             : vraies rues OpenStreetMap + itineraires OSRM
) else (
  echo Carte             : ville synthetique ^(pas d'extrait data\osm\ouaga.osm.pbf, voir data\osm\README.md^)
)
findstr /r /c:"^SALUBRI_DEMO_MODE=false" .env >nul 2>nul && echo Mode              : production (.env) || echo Mode              : demonstration (compte demo / ouaga2026)
exit /b %ok%

:port
netstat -ano | findstr /r /c:"TCP.*:%1 .*LISTENING" >nul
if errorlevel 1 ( echo Port %1           : libre & goto :eof )
if defined mine ( echo Port %1           : utilise par Salubri ^(deja lance^) & goto :eof )
echo Port %1           : ECHEC, occupe par un autre programme ^(Skype, IIS...^) - fermez-le ou WEB_PORT=8080 dans .env
set ok=1
goto :eof

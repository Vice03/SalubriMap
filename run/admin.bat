@echo off
REM Cree un compte administrateur (le mot de passe est demande au clavier). Usage : run\admin <login>
cd /d "%~dp0\.."
if "%~1"=="" ( echo Usage : run\admin ^<login^> & exit /b 1 )
docker compose run --rm seed python -m salubri_api.users add %1 --role admin --name "%~1"

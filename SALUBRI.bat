@echo off
setlocal EnableExtensions
rem ==========================================================================
rem  SALUBRI - lanceur unique (Windows). Double-cliquer ce fichier.
rem  Tout se fait depuis ce menu. Le lanceur corrige seul les problemes
rem  courants : Docker arrete (il le demarre), port 80/8443 deja pris (il
rem  choisit un port libre), .env absent, anciens conteneurs (nettoyage et
rem  nouvel essai). Livrables et guide : dossier livrable\ (option G).
rem ==========================================================================
cd /d "%~dp0"
title Salubri - Assainissement de Ouaga
set "SALUBRI_NOPAUSE=1"
rem couleurs (Windows 10 et plus) ; sans elles le texte reste lisible
for /f %%a in ('echo prompt $E^| cmd') do set "E=%%a"
set "N=%E%[0m"
set "G=%E%[92m"
set "Y=%E%[93m"
set "RD=%E%[91m"
set "C=%E%[96m"
set "W=%E%[97m"
set "D=%E%[90m"
if not exist ".env" if exist ".env.example" copy /y ".env.example" ".env" >nul
if not exist ".env" type nul > ".env"

:menu
call :url
call :state
cls
echo.
echo   %G%=================================================================%N%
echo   %W%  SALUBRI%N%  -  cartographier, verifier, planifier, simuler
echo   %D%  Hackathon des Universites 2026 - Assainissement de Ouaga%N%
echo   %G%=================================================================%N%
echo     Docker  : %DOCKER_TXT%
echo     Salubri : %SAL_TXT%
echo     Version : %MODE%
echo   %G%-----------------------------------------------------------------%N%
echo.
echo   %C%DEMARRER%N%
echo    %Y% 1%N%  Version DEMO         %D%(recommandee pour le jury)%N%
echo    %Y% 2%N%  Version COMPLETE     %D%(donnees de reference, sans signalement fictif + Saisons + Assistant IA)%N%
echo.
echo   %C%OUVRIR%N%
echo    %Y% 3%N%  Salubri Map   %D%carte, moderation, plan, simulation%N%
echo    %Y% 4%N%  Salubri Go    %D%appli citoyenne de signalement%N%
echo    %Y% 5%N%  Documentation de l'API
echo    %Y% G%N%  Livrables du defi + guide d'utilisation %D%(dossier livrable)%N%
echo.
echo   %C%VERIFIER%N%
echo    %Y% 6%N%  Etat des services
echo    %Y% 7%N%  Diagnostic de la machine (Docker, ports, disque)
echo    %Y% 8%N%  Repetition generale (pieges du jury, changements de parametres)
echo    %Y% 9%N%  Tests automatiques de l'API
echo.
echo   %C%OUTILS%N%
echo    %Y%10%N%  Remettre la demo a zero (efface les donnees, recharge)
echo    %Y%11%N%  Demo sur telephone Android (cable USB)
echo    %Y%12%N%  Assistant IA : installer un modele local (avec accord)
echo    %Y%13%N%  Journal de l'API en direct (Ctrl+C puis N pour revenir)
echo    %Y%14%N%  Arreter Salubri
echo    %Y%15%N%  Caler le facteur de detour contre OSRM
echo    %Y% P%N%  Purger les signalements %D%(garder les donnees de reference)%N%
echo    %Y% R%N%  Reparer : nettoyer les conteneurs et relancer
echo.
echo    %Y% 0%N%  Quitter %D%(Salubri continue de tourner)%N%
echo.
set "choix="
set /p "choix=   Votre choix : "
if not defined choix goto menu
if /i "%choix%"=="1" goto demo
if /i "%choix%"=="2" goto complete
if /i "%choix%"=="3" ( start "" "%URL%/" & goto menu )
if /i "%choix%"=="4" ( start "" "%URL%/go/" & goto menu )
if /i "%choix%"=="5" ( start "" "%URL%/api/docs" & goto menu )
if /i "%choix%"=="G" goto guide
if /i "%choix%"=="6" goto etat
if /i "%choix%"=="7" ( call run\doctor.bat & echo. & pause & goto menu )
if /i "%choix%"=="8" goto rehearse
if /i "%choix%"=="9" goto tests
if /i "%choix%"=="10" goto reset
if /i "%choix%"=="11" ( call run\telephone.bat & pause & goto menu )
if /i "%choix%"=="12" goto modele
if /i "%choix%"=="13" ( docker compose logs -f --tail 50 api & goto menu )
if /i "%choix%"=="14" goto stop
if /i "%choix%"=="15" goto detour
if /i "%choix%"=="R" goto repair
if /i "%choix%"=="P" goto purge
if /i "%choix%"=="0" goto fin
echo   %RD%Choix inconnu : %choix%%N%
call :sleep 2
goto menu

rem ----------------------------------------------------------------- demarrage
:demo
echo.
echo   %W%Version DEMO%N% : comptes admin / Salubri2026 et demo / ouaga2026, modules optionnels eteints.
call :setenv SALUBRI_DEMO_MODE true
call :setenv SALUBRI_DATA_MODE demo
call :setenv SALUBRI_SEASONS_ENABLED false
call :setenv SALUBRI_ASSISTANT_ENABLED false
set "ARGS="
goto launch

:complete
echo.
echo   %W%Version COMPLETE%N% : donnees de reference seulement ^(aucun signalement fictif^), Saisons et Assistant IA.
echo   Seuls les signalements envoyes par Salubri Go seront enregistres.
echo   Compte : %W%admin%N% / %W%Salubri2026%N%  ^(administrateur, sans badge demo^).
call :setenv SALUBRI_DEMO_MODE true
call :setenv SALUBRI_DATA_MODE reference
call :setenv SALUBRI_SEASONS_ENABLED true
call :setenv SALUBRI_ASSISTANT_ENABLED true
set "ARGS=--llm=no"
goto launch

:launch
call :ensure_docker
if errorlevel 1 goto launch_fail
call :fix_ports
if errorlevel 1 goto launch_fail
call :url
echo   %D%Demarrage (premiere fois : plusieurs minutes, les images se construisent)...%N%
call run\start.bat %ARGS%
if not errorlevel 1 goto launch_ok
echo.
echo   %Y%Premier essai en echec : nettoyage des anciens conteneurs et nouvel essai...%N%
docker compose down --remove-orphans >nul 2>nul
call :fix_ports
call :url
call run\start.bat %ARGS%
if not errorlevel 1 goto launch_ok
:launch_fail
echo.
echo   %RD%Salubri n'a pas pu demarrer.%N% Dernieres lignes du journal :
docker compose logs --tail 25 api seed 2>nul
echo.
echo   %Y%Pistes%N% : option 7 ^(diagnostic^), option R ^(reparer^), redemarrer Docker Desktop,
echo   ou dans PowerShell : wsl --update  ^(si Docker signale un probleme WSL^).
pause
goto menu
:launch_ok
call :ready
goto menu

rem ----------------------------------------------------------------- actions
:etat
echo.
docker compose ps
echo.
call :health
if errorlevel 1 ( echo   %RD%API : ne repond pas sur %URL%/api/health%N% ) else ( echo   %G%API : OK sur %URL%%N% )
echo.
pause
goto menu

:rehearse
call :need_running
if errorlevel 1 goto menu
call run\rehearse.bat
pause
goto menu

:purge
call :need_running
if errorlevel 1 goto menu
call run\purge.bat
pause
goto menu

:tests
call :ensure_docker
if errorlevel 1 ( pause & goto menu )
call run\test.bat
pause
goto menu

:reset
echo.
echo   %RD%ATTENTION%N% : toutes les donnees ^(signalements, scenarios, plans^) seront effacees et rechargees.
set "ok="
set /p "ok=   Taper OUI pour confirmer : "
if /i not "%ok%"=="OUI" goto menu
call :ensure_docker
if errorlevel 1 ( pause & goto menu )
call :fix_ports
call :url
call run\reset.bat
call :ready
goto menu

:modele
echo.
where python >nul 2>nul
if errorlevel 1 (
  echo   %Y%Python est necessaire pour cette option%N% : https://www.python.org/downloads/ ^(cocher "Add to PATH"^)
  start "" "https://www.python.org/downloads/"
  pause & goto menu
)
echo   Recherche d'un modele deja installe ^(Ollama, LM Studio...^), sinon proposition de telechargement
echo   adapte a cette machine. Taille et espace libre affiches avant toute question.
call :setenv SALUBRI_ASSISTANT_ENABLED true
set "SALUBRI_LLM_DURING_DEMO=on"
python run\llm_detect.py --force
set "SALUBRI_LLM_DURING_DEMO="
echo.
echo   Relancez ensuite la version COMPLETE ^(option 2^). Si Ollama est installe, ouvrez-le : l'assistant le trouve seul.
pause
goto menu

:stop
call run\stop.bat
echo   %G%Salubri est arrete%N% ^(donnees conservees^).
call :sleep 2
goto menu

:detour
call :need_running
if errorlevel 1 goto menu
call run\detour.bat
pause
goto menu

:repair
echo.
echo   %W%Reparation%N% : arret propre, suppression des conteneurs orphelins, nouveau demarrage ^(donnees conservees^).
call :ensure_docker
if errorlevel 1 ( pause & goto menu )
docker compose down --remove-orphans
call :fix_ports
call :url
call run\start.bat
call :ready
goto menu

:guide
rem Ouvre le dossier livrable (les 6 livrables + GUIDE_JURY.pdf) ; le guide s'ouvre aussi tout de suite.
if exist "livrable\README.md" ( start "" "livrable" & if exist "livrable\GUIDE_JURY.pdf" start "" "livrable\GUIDE_JURY.pdf" ) else ( echo   dossier livrable introuvable : lancer run\livrable.bat & pause )
goto menu

:fin
endlocal
exit /b 0

rem ----------------------------------------------------------------- outils
:ensure_docker
rem Docker installe et demarre ; s'il est arrete, on demarre Docker Desktop et on attend (3 min au plus).
where docker >nul 2>nul
if errorlevel 1 goto nodocker
docker info >nul 2>nul
if not errorlevel 1 exit /b 0
echo   %Y%Docker Desktop est arrete : demarrage automatique, patientez...%N%
set "DD="
if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" set "DD=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
if not defined DD if exist "%LocalAppData%\Programs\Docker\Docker\Docker Desktop.exe" set "DD=%LocalAppData%\Programs\Docker\Docker\Docker Desktop.exe"
if not defined DD if exist "%LocalAppData%\Programs\DockerDesktop\frontend\Docker Desktop.exe" set "DD=%LocalAppData%\Programs\DockerDesktop\frontend\Docker Desktop.exe"
if not defined DD if exist "%ProgramFiles%\Docker\Docker\frontend\Docker Desktop.exe" set "DD=%ProgramFiles%\Docker\Docker\frontend\Docker Desktop.exe"
if not defined DD for /f "delims=" %%x in ('where "Docker Desktop.exe" 2^>nul') do set "DD=%%x"
if defined DD start "" "%DD%"
set /a T=0
:wait_docker
call :sleep 3
docker info >nul 2>nul
if not errorlevel 1 goto docker_ok
set /a T+=3
<nul set /p "=."
if %T% LSS 180 goto wait_docker
echo.
echo   %RD%Docker ne demarre pas.%N% Ouvrez Docker Desktop a la main ; s'il parle de WSL, dans PowerShell : wsl --update
exit /b 1
:docker_ok
echo.
echo   %G%Docker est pret.%N%
exit /b 0
:nodocker
echo   %RD%Docker Desktop n'est pas installe.%N% La page de telechargement s'ouvre ; installez-le, redemarrez, relancez SALUBRI.bat.
start "" "https://docs.docker.com/desktop/install/windows-install/"
exit /b 1

:fix_ports
rem Port web pris par un autre programme (Skype, IIS, Apache...) : on passe seul sur un port libre (note dans .env).
set "OURS="
for /f %%i in ('docker compose ps -q web 2^>nul') do set "OURS=1"
if defined OURS exit /b 0
call :fix_port WEB_PORT 80 "8080 8081 8088 8888 8090 3080"
if errorlevel 1 exit /b 1
call :fix_port WEB_TLS_PORT 8443 "9443 8444 10443 18443"
exit /b %errorlevel%

:fix_port
set "FP_CUR="
for /f "tokens=2 delims==" %%a in ('findstr /b /c:"%~1=" ".env" 2^>nul') do set "FP_CUR=%%a"
if not defined FP_CUR set "FP_CUR=%~2"
call :busy %FP_CUR%
if errorlevel 1 exit /b 0
for %%p in (%~3) do (
  call :busy %%p
  if errorlevel 1 (
    call :setenv %~1 %%p
    echo   %Y%Port %FP_CUR% deja pris par un autre programme : Salubri utilise le port %%p ^(%~1 dans .env^).%N%
    exit /b 0
  )
)
echo   %RD%Port %FP_CUR% occupe et aucun port de secours libre.%N% Trouver le programme : netstat -ano ^| findstr :%FP_CUR%
exit /b 1

:busy
rem errorlevel 0 = port en ecoute (occupe), 1 = libre
netstat -ano | findstr /r /c:":%~1 .*LISTENING" >nul
exit /b %errorlevel%

:need_running
call :health
if not errorlevel 1 exit /b 0
echo   %Y%Salubri ne tourne pas : lancez d'abord l'option 1 ou 2.%N%
pause
exit /b 1

:setenv
rem Remplace (ou ajoute) la ligne CLE=valeur de .env, sans toucher aux autres lignes.
if not exist ".env" type nul > ".env"
findstr /v /b /c:"%~1=" ".env" > ".env.tmp"
>> ".env.tmp" echo %~1=%~2
move /y ".env.tmp" ".env" >nul
exit /b 0

:url
set "WEBP="
for /f "tokens=2 delims==" %%a in ('findstr /b /c:"WEB_PORT=" ".env" 2^>nul') do set "WEBP=%%a"
if not defined WEBP set "WEBP=80"
if "%WEBP%"=="80" ( set "URL=http://localhost" ) else ( set "URL=http://localhost:%WEBP%" )
exit /b 0

:health
rem curl.exe (Windows 10+) sur 127.0.0.1 sans proxy, sinon PowerShell
curl.exe -s -f -o nul -m 3 --noproxy "*" "%URL:localhost=127.0.0.1%/api/health" <nul >nul 2>nul && exit /b 0
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing '%URL:localhost=127.0.0.1%/api/health' -TimeoutSec 3) | Out-Null; exit 0 } catch { exit 1 }" <nul >nul 2>nul
exit /b %errorlevel%

:state
set "MODE=demo"
findstr /b /c:"SALUBRI_SEASONS_ENABLED=true" ".env" >nul 2>nul && set "MODE=complete, donnees de reference (Saisons + Assistant IA)"
findstr /b /c:"SALUBRI_DEMO_MODE=false" ".env" >nul 2>nul && set "MODE=production"
set "DOCKER_TXT=%RD%absent ou arrete%N% %D%- demarre seul aux options 1 et 2%N%"
docker info >nul 2>nul && set "DOCKER_TXT=%G%pret%N%"
call :health
set "SAL_TXT=%G%EN MARCHE%N% sur %URL%"
if errorlevel 1 set "SAL_TXT=%Y%arrete%N% %D%- ou en demarrage%N%"
exit /b 0

:ready
echo.
call :health
if errorlevel 1 (
  echo   %Y%Salubri ne repond pas encore%N% : option 6 ^(etat^) ou 7 ^(diagnostic^).
) else (
  echo   %G%=================================================================%N%
  echo   %G%Pret.%N%  Salubri Map : %W%%URL%/%N%    Salubri Go : %W%%URL%/go/%N%
  echo          Connexion mairie : %W%admin%N% / %W%Salubri2026%N%   %D%^(ou demo / ouaga2026^)%N%
  echo   %G%=================================================================%N%
)
rem adresse a saisir dans l'APK (reaffichee ici : la fenetre reste ouverte grace a pause)
if defined WEBP powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run\adresses.ps1" -Port %WEBP%
pause
exit /b 0

:sleep
ping -n %~1 127.0.0.1 >nul
exit /b 0

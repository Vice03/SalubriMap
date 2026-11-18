@echo off
setlocal EnableExtensions
rem ==========================================================================
rem  SALUBRI - lanceur unique (Windows). Double-cliquer ce fichier.
rem  Tout se fait depuis ce menu : demarrer la demo ou la version complete,
rem  ouvrir les applications, diagnostiquer, repeter, tester, arreter.
rem  Guide : docs\GUIDE_JURY.pdf  (option G du menu)
rem ==========================================================================
cd /d "%~dp0"
title Salubri - Assainissement de Ouaga
if not exist ".env" if exist ".env.example" copy /y ".env.example" ".env" >nul

:menu
call :url
cls
echo.
echo   ==============================================================
echo      SALUBRI  -  cartographier, verifier, planifier, simuler
echo      Hackathon des Universites 2026 - Assainissement de Ouaga
echo   ==============================================================
call :status_line
echo.
echo    DEMARRER
echo     1  Version DEMO        (recommandee pour le jury)
echo     2  Version COMPLETE    (demo + modules Saisons et Assistant)
echo.
echo    OUVRIR
echo     3  Salubri Map  - carte, moderation, plan, simulation  (navigateur)
echo     4  Salubri Go   - appli citoyenne de signalement
echo     5  Documentation de l'API
echo     G  Guide d'utilisation (PDF)
echo.
echo    VERIFIER
echo     6  Etat des services
echo     7  Diagnostic de la machine (Docker, ports, disque)
echo     8  Repetition generale (pieges du jury, changements de parametres)
echo     9  Tests automatiques de l'API
echo.
echo    OUTILS
echo    10  Remettre la demo a zero (efface les donnees, redemarre)
echo    11  Demo sur telephone Android (cable USB)
echo    12  Assistant : installer un modele local (telechargement, avec accord)
echo    13  Journal de l'API en direct (Ctrl+C puis N pour revenir)
echo    14  Arreter Salubri
echo    15  Caler le facteur de detour contre OSRM (Salubri doit tourner)
echo.
echo     0  Quitter (Salubri continue de tourner)
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
if /i "%choix%"=="8" ( call run\rehearse.bat & goto menu )
if /i "%choix%"=="9" ( call run\test.bat & goto menu )
if /i "%choix%"=="10" goto reset
if /i "%choix%"=="11" ( call run\telephone.bat & goto menu )
if /i "%choix%"=="12" goto modele
if /i "%choix%"=="13" ( docker compose logs -f --tail 50 api & goto menu )
if /i "%choix%"=="14" ( call run\stop.bat & goto menu )
if /i "%choix%"=="15" ( call run\detour.bat & echo. & pause & goto menu )
if /i "%choix%"=="0" goto fin
echo   Choix inconnu : %choix%
timeout /t 2 /nobreak >nul
goto menu

:demo
echo.
echo   Version DEMO : compte demo / ouaga2026, modules optionnels eteints.
call :setenv SALUBRI_DEMO_MODE true
call :setenv SALUBRI_SEASONS_ENABLED false
call :setenv SALUBRI_ASSISTANT_ENABLED false
call run\start.bat
call :ready
goto menu

:complete
echo.
echo   Version COMPLETE : compte demo / ouaga2026 + module Saisons (routes coupees en saison des pluies)
echo   + module Assistant (modele de langue local, lecture seule ; s'il n'y a pas de modele : option 12).
call :setenv SALUBRI_DEMO_MODE true
call :setenv SALUBRI_SEASONS_ENABLED true
call :setenv SALUBRI_ASSISTANT_ENABLED true
call run\start.bat --llm=no
call :ready
goto menu

:reset
echo.
echo   ATTENTION : toutes les donnees (signalements, scenarios, plans) seront effacees.
set "ok="
set /p "ok=   Taper OUI pour confirmer : "
if /i not "%ok%"=="OUI" goto menu
call run\reset.bat
call :ready
goto menu

:modele
echo.
where python >nul 2>nul
if errorlevel 1 (
  echo   Python est necessaire pour cette option : https://www.python.org/downloads/ ^(cocher "Add to PATH"^)
  pause & goto menu
)
echo   Recherche d'un modele deja installe (Ollama, LM Studio, llama.cpp, Jan...), sinon proposition de
echo   telechargement adapte a cette machine. La taille et l'espace libre sont affiches avant toute question.
call :setenv SALUBRI_ASSISTANT_ENABLED true
set "SALUBRI_LLM_DURING_DEMO=on"
python run\llm_detect.py --force
set "SALUBRI_LLM_DURING_DEMO="
echo.
echo   Relancez ensuite la version COMPLETE (option 2) pour utiliser l'assistant.
pause
goto menu

:etat
echo.
docker compose ps
echo.
call :health
if errorlevel 1 ( echo   API : ne repond pas sur %URL%/api/health ) else ( echo   API : OK sur %URL% )
echo.
pause
goto menu

:guide
if exist "docs\GUIDE_JURY.pdf" ( start "" "docs\GUIDE_JURY.pdf" ) else ( echo   docs\GUIDE_JURY.pdf introuvable & pause )
goto menu

:fin
endlocal
exit /b 0

rem ----------------------------------------------------------------- outils
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

:status_line
set "MODE=demo"
findstr /b /c:"SALUBRI_SEASONS_ENABLED=true" ".env" >nul 2>nul && set "MODE=complete"
findstr /b /c:"SALUBRI_DEMO_MODE=false" ".env" >nul 2>nul && set "MODE=production"
call :health
if errorlevel 1 ( echo      Etat : arrete ^(ou en demarrage^)          Version choisie : %MODE% ) else ( echo      Etat : EN MARCHE sur %URL%     Version : %MODE% )
exit /b 0

:ready
echo.
call :health
if errorlevel 1 (
  echo   Salubri ne repond pas encore : option 6 ^(etat^) ou 7 ^(diagnostic^).
) else (
  echo   Pret. Salubri Map : %URL%/    Salubri Go : %URL%/go/
  echo   Connexion mairie : demo / ouaga2026
)
pause
exit /b 0

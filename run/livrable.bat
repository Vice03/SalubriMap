@echo off
REM Salubri - reconstruit le dossier livrable (les 6 livrables du defi) depuis les sources, puis l ouvre
cd /d "%~dp0\.."
where py >nul 2>nul && ( py -3 scripts\livrable.py & goto ouvrir )
where python >nul 2>nul && ( python scripts\livrable.py & goto ouvrir )
echo   Python introuvable : le dossier livrable deja present est ouvert tel quel.
:ouvrir
start "" "livrable"
exit /b 0

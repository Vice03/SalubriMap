@echo off
REM Demo telephone par cable USB : le telephone ouvre http://localhost/go/ qui est relaye vers ce PC.
REM "localhost" compte comme connexion securisee : GPS, installation de l'appli et mode hors ligne fonctionnent.
where adb >nul 2>nul
if errorlevel 1 (
  echo adb introuvable. Installez "Android SDK Platform-Tools" : https://developer.android.com/tools/releases/platform-tools
  echo puis ajoutez le dossier platform-tools au PATH.
  echo Sur le telephone : Parametres ^> A propos ^> appuyer 7 fois sur "Numero de build", puis Options pour les developpeurs ^> Debogage USB.
  pause & exit /b 1
)
adb reverse tcp:80 tcp:80
if errorlevel 1 (
  echo Telephone non detecte : branchez-le en USB et acceptez "Autoriser le debogage USB" sur l'ecran du telephone.
  pause & exit /b 1
)
echo.
echo OK. Sur le telephone, ouvrez Chrome a l'adresse :  http://localhost/go/
echo  - Hors ligne : debranchez le cable (le mode avion ne coupe pas l'USB), signalez : "En attente".
echo  - Retour du reseau : rebranchez le cable et relancez ce script ; l'envoi part tout seul.
pause

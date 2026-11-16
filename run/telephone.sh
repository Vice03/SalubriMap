#!/usr/bin/env bash
# Démo téléphone par câble USB : le téléphone ouvre http://localhost/go/ relayé vers ce PC (contexte sécurisé :
# GPS, installation et mode hors ligne fonctionnent). Nécessite adb (Android SDK Platform-Tools) et le débogage USB.
set -e
command -v adb >/dev/null || { echo "adb introuvable : installez Android SDK Platform-Tools"; exit 1; }
adb reverse tcp:80 tcp:80 || { echo "Téléphone non détecté : branchez-le et autorisez le débogage USB"; exit 1; }
echo "OK. Sur le téléphone, ouvrez Chrome : http://localhost/go/"
echo " - Hors ligne : débranchez le câble (le mode avion ne coupe pas l'USB)."
echo " - Retour du réseau : rebranchez et relancez ce script."

# Tests de bout en bout (navigateur)

Vérifient dans un vrai navigateur (Chrome/Chromium via Playwright) ce que les tests de l'API ne voient pas :

- `test_go_offline.py` : Salubri Go s'ouvre **hors ligne dès la première visite**, un signalement fait hors ligne
  reste « en attente », puis part tout seul au retour du réseau ;
- `test_web_smoke.py` : chaque page de Salubri Map/Sim s'affiche sans erreur JavaScript, y compris en largeur téléphone.

Salubri doit tourner (`run/start`), puis :

    pip install playwright pytest pillow && playwright install chromium
    SALUBRI_URL=http://localhost pytest tests/e2e -q

`SALUBRI_CHROME=/chemin/vers/chrome` utilise un navigateur déjà installé.

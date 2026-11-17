<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Rapport de la version 0.3 — sécurité, démarrage, tests, interfaces

Chaque ligne cite la preuve qui l'établit. « Après » est l'auto-évaluation de ce travail : la note
« avant » vient de la revue v3 ; une revue indépendante reste à faire.

| Axe | Avant | Après | Preuve (test ou commande) |
|---|---|---|---|
| Sécurité — comptes et rôles (A1) | 6 | 9 | `tests/test_accounts.py` : les 21 routes d'écriture lues dans le schéma OpenAPI, 401 anonyme / 403 mauvais rôle / 2xx bon rôle ; journal signé « identifiant (rôle) » |
| Sécurité — secrets hors démo (A2) | | | `tests/test_security_config.py` ; production avec `ouaga2026` : l'API refuse de démarrer |
| Sécurité — force brute, pourriel (A3) | | | `tests/test_ratelimit.py` ; nginx : 429 en français vérifié sur le PC ; e2e « 429 garde le signalement en attente » |
| Sécurité — données personnelles (A4) | | | `tests/test_privacy.py` : un visiteur ne reçoit ni `device_id` ni signalement non vérifié, photo publique sans EXIF, journal 401 |
| Sécurité — téléversements (A5) | | | `tests/test_uploads.py` : faux JPEG, GIF/BMP, image de 48 Mpx, ZIP `..`, bombe, en-tête mensonger |
| Sécurité — en-têtes, TLS (A6) | | | `curl -I` : CSP, nosniff, Referrer-Policy, HSTS sur 8443 seulement ; aucune violation CSP sur les 6 pages ; `pip-audit` et `pnpm audit --prod` : 0 vulnérabilité (MapLibre 6.18, React Router 7.18) |
| Sécurité — connexion web (A7) | | | `tests/e2e/test_web_login.py` ; `apps/web/src/__tests__/client.test.ts` |
| Démarrage en une commande (B) | 8 | 9 | `run/doctor`, healthchecks sur tous les services, job CI « stack » (clone neuf → répétition + e2e) — **job écrit mais pas encore exécuté sur GitHub** |
| Tests et reproductibilité (C) | 9 | 9,5 | API : 130 tests, couverture 91 % (plancher en CI) ; Vitest : 8 (Go) + 7 (Map) ; e2e : 15 ; ESLint + tsc propres ; « 2 camions en panne » : cause trouvée, `test_breakdown_after_import.py` (20 pannes) |
| Salubri Go (D) | 8,5 | 9 | `tests/e2e/test_go_citizen.py` (verdict en mots, suivi, doublon de photo expliqué, icônes PNG) |
| Salubri Map/Sim (E) | 8 | 8,5 | `tests/e2e/test_web_smoke.py` à 390/820/1440 px sans erreur JS ni débordement ; MapLibre absent du HTML initial |
| Backend (F) | 9,5 | 9,5 | `tests/test_health.py` (version unique, file de recalculs, `X-Request-ID`, journaux JSON, pagination du journal) ; migration 0004 rejouée sur une base existante (555 signalements conservés), plan de requête : `Index Scan using ix_reports_commune_status_reported` |

Les lignes A2 à A7 n'ont pas de note séparée : la revue note la sécurité d'un seul bloc (6 avant).

## Ce qui n'est pas fait (à reprendre)

- **D** : boutons « Toujours là » / « C'est nettoyé » dans « Autour de moi » (avec vignette, distance et petite carte) ; rapport Lighthouse PWA/accessibilité ≥ 95 dans `docs/`.
- **E** : barres côte à côte dans Comparer, vignette photo par ligne, puces de règles en mots, sélection multiple et raccourcis clavier de modération, curseurs du scénario bornés par `params-schema` avec bandeau avant/après, bouton « Simuler avec N camions », « ? » sur chaque indicateur, Lighthouse ≥ 85 / 95.
- **F** : table de tâches persistante avec un seul worker et un verrou PostgreSQL par scénario, `GET /api/jobs` (la reprise au redémarrage de `services/plan/recovery.py` reste le mécanisme actuel).
- **B** : temps de démarrage à froid sur une machine neuve. Il est chronométré par le job CI « stack », qui n'a pas encore tourné ; l'essai local de ce job a été bloqué par la limite de téléchargements de Docker Hub.

## Ce qui n'est pas vérifié

- **Vrai téléphone** : GPS, appareil photo, installation de la PWA, avis de mise à jour, HTTPS auto-signé sur le Wi-Fi.
- **Vraies rues OSM + OSRM sur une machine neuve** : vérifié sur le PC de développement (carte réelle, OSRM « ok ») ; le jeu de pièges des vraies rues est généré depuis la base locale.
- **TLS de production** (Let's Encrypt) : procédure écrite dans `docs/SECURITY.md`, pas jouée.
- **Windows** : `run/doctor.bat` et le chemin production de `run/secrets.ps1` ne sont pas exécutés ici (pas de PowerShell / cmd dans l'environnement de test) ; `run/start.bat` est vérifié sur le PC.
- **CI GitHub** : les jobs `api`, `front`, `audit` et `stack` reproduisent des commandes lancées ici, mais aucun n'a encore tourné sur GitHub.

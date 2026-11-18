<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Sécurité de Salubri

Ce document décrit ce que Salubri protège, contre qui, et ce qu'il ne protège pas. Il dit aussi comment
passer d'une démonstration sur un PC à un serveur de la mairie avec un vrai nom de domaine.

## Qui utilise Salubri

| Acteur | Ce qu'il fait | Ce qu'il peut faire |
|---|---|---|
| **Citoyen** (Salubri Go, sans compte) | signale un dépôt avec photo et GPS | envoyer des signalements (limités par téléphone et par adresse), voir les dépotoirs et les signalements **vérifiés** sans donnée personnelle |
| **Modérateur** (compte mairie) | vérifie, rejette, fusionne | tout ce que fait le citoyen + voir les signalements non vérifiés, l'appareil, le commentaire, la photo d'origine, le journal |
| **Admin** (compte mairie) | imports, scénarios, plans, quartiers | tout ce que fait le modérateur + les actions qui changent les données de référence |
| **Attaquant** | n'importe qui sur Internet ou le Wi-Fi | voir « Menaces » ci-dessous |

Les rôles sont vérifiés par l'API pour chaque écriture (tests : `apps/api/tests/test_accounts.py`, qui
parcourt toutes les routes du schéma OpenAPI pour n'en oublier aucune).

## Menaces et protections

| Menace | Protection | Où |
|---|---|---|
| Deviner un mot de passe | argon2id ; blocage 15 min après 5 échecs pour une paire (identifiant, adresse) et après 20 échecs par adresse ; sur un identifiant seul, jamais de blocage (un attaquant ne peut pas verrouiller le compte d'un autre) mais un délai de 1 à 8 s sur chaque échec au-delà de 20 ; levée : `python -m salubri_api.users unlock <login>` ; nginx : 10 tentatives/min/IP | `services/auth.py`, `services/ratelimit.py`, `services/nginx/` |
| Voler une session | jeton signé HMAC-SHA256, 8 h, révoqué à la déconnexion (`session_version`) ; gardé en mémoire + `sessionStorage`, jamais dans une URL | `services/auth.py`, `apps/web/src/api/` |
| Laisser le code de démonstration en production | hors mode démo, l'API **refuse de démarrer** si un secret est vide, faible ou égal à `ouaga2026`, si aucun admin n'existe ou si le compte `demo` est actif | `services/security_config.py` |
| Inonder la mairie de faux signalements | 13 Mo par requête, 60 POST/min/IP (nginx), 30 signalements/h par téléphone (429), puis les 14 règles anti-pièges | `routers/reports.py`, `services/validation/` |
| Fichier piégé (faux JPEG, bombe de pixels, ZIP malveillant) | contenu reconnu par Pillow, 40 Mpx max, réencodage, nom aléatoire ; ZIP lu en mémoire, chemins `..` refusés, tailles et taux de compression bornés | `services/validation/photo.py`, `services/importers/run.py` |
| Exposer la vie privée des citoyens | le public ne voit que les signalements vérifiés ou nettoyés, sans appareil, commentaire, EXIF ni modérateur ; photos sans EXIF ; journal réservé à la mairie | `routers/serializers.py`, `routers/reports.py` |
| Injection de script (XSS), clic piégé | CSP stricte (`script-src 'self'`, `frame-ancestors 'none'`), `X-Content-Type-Options`, `Referrer-Policy`, React échappe le texte | `services/nginx/security_headers.conf` |
| Écoute du réseau | HTTPS (HSTS sur le serveur TLS) ; voir « Production » | `services/nginx/nginx.conf` |
| Accès direct à la base ou à l'API | ports 5432 et 8000 ouverts sur `127.0.0.1` seulement ; le reste passe par nginx | `docker-compose.yml` |
| Contestation d'une décision | journal de toutes les actions, signé « identifiant (rôle) » | `models/audit.py` |

## Ce qui n'est pas protégé (à savoir)

- **Par défaut** : production. `run/start` génère les secrets et le mot de passe du compte `admin` dans `.env` ; l'API l'applique au démarrage (`SALUBRI_BOOTSTRAP_ADMIN_PASSWORD`) tant qu'aucun admin propre n'existe. **Démonstration** (`SALUBRI_DEMO_MODE=true`) : le mode démo est public par construction (code `ouaga2026`, comptes `demo` et `admin` / `Salubri2026`, recréés ou réparés à chaque démarrage en mode démo : réactivés, mot de passe d'origine, blocages levés). Ne jamais l'exposer sur Internet. Hors démonstration, l'API refuse de démarrer tant que `admin` garde son mot de passe par défaut (le changer : `python -m salubri_api.users passwd admin`, ou le désactiver ; login et mot de passe par défaut réglables par `SALUBRI_DEFAULT_ADMIN_LOGIN` et `SALUBRI_DEFAULT_ADMIN_PASSWORD`).
- **Certificat local** : en démonstration, le HTTPS de `:8443` est auto-signé ; le téléphone affiche un avertissement. Ce n'est pas une protection contre un attaquant sur le même Wi-Fi.
- **Plusieurs processus API** : les échecs de connexion sont en base (partagés) ; les compteurs anti-pourriel des signalements restent en mémoire d'un seul processus (voir `docs/HYPOTHESES.md`).
- **Un téléphone qui change d'identifiant** contourne la limite par appareil ; la limite par adresse et les règles restent.
- **Sauvegardes** : la base (`pgdata`) et les photos (`photos`) sont des volumes Docker ; leur sauvegarde et leur chiffrement sont à la charge de l'hébergeur.
- **Dépendances** : `pip-audit` et `pnpm audit --prod` tournent en CI ; les exceptions sont listées dans `.github/workflows/ci.yml`.

## Production : vrai domaine et Let's Encrypt

1. Un serveur Linux avec Docker, un nom de domaine (ex. `salubri.mairie-ouaga.bf`) qui pointe vers lui, ports 80 et 443 ouverts.
2. Secrets et premier admin :
   ```sh
   cp .env.example .env
   ./run/secrets.sh        # complète .env : secrets aléatoires et mot de passe du premier admin (affichés)
   ./run/admin.sh chef     # (facultatif) compte personnel, mot de passe demandé au clavier
   ./run/start.sh          # l'API vérifie les secrets et l'admin avant de démarrer
   ```
3. Certificat (certbot, mode webroot ou standalone pendant une minute d'arrêt de nginx) :
   ```sh
   docker compose stop web
   sudo certbot certonly --standalone -d salubri.mairie-ouaga.bf
   ```
4. Monter le certificat à la place du certificat auto-signé, dans un fichier `docker-compose.override.yml` :
   ```yaml
   services:
     web:
       ports: ["80:80", "443:443"]
       volumes:
         - /etc/letsencrypt/live/salubri.mairie-ouaga.bf/fullchain.pem:/etc/nginx/salubri/cert.pem:ro
         - /etc/letsencrypt/live/salubri.mairie-ouaga.bf/privkey.pem:/etc/nginx/salubri/key.pem:ro
   ```
   puis `docker compose up -d web`. Le serveur HTTPS envoie déjà `Strict-Transport-Security`.
5. Rediriger HTTP vers HTTPS : ajouter dans l'override un `nginx.conf` dont le serveur `listen 80` ne contient que `return 301 https://$host$request_uri;`.
6. Renouvellement : `certbot renew` (tâche cron), puis `docker compose restart web`.

## Changer les secrets (rotation)

| Secret | Effet du changement | Comment |
|---|---|---|
| `SALUBRI_SECRET_KEY` | toutes les sessions sont déconnectées | nouvelle valeur (≥ 32 caractères) dans `.env`, `docker compose up -d api` |
| `SALUBRI_ADMIN_TOKEN` (identifiant de service, scripts) | les scripts doivent utiliser le nouveau | nouvelle valeur (≥ 16 caractères) dans `.env`, `docker compose up -d api` |
| Mot de passe d'un compte | ses sessions sont déconnectées | `docker compose run --rm seed python -m salubri_api.users passwd <login>` |
| Compte compromis | coupé immédiatement | `... users disable <login>` |
| Mot de passe PostgreSQL | — | changer `POSTGRES_PASSWORD` et `SALUBRI_DATABASE_URL` ensemble, puis `ALTER USER` dans la base |

Après une rotation, `GET /api/health` doit répondre `ok` ; sinon le journal de l'API (`docker compose logs api`) dit quel contrôle a échoué.

## Signaler une faille

Écrire aux mainteneurs du dépôt (issue privée « Security advisory » sur GitHub). Ne pas publier la faille avant correctif.

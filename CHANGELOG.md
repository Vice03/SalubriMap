# Journal des versions

## 0.3.0 — en cours

- **Comptes et rôles (lot A1)** : comptes de la mairie (`moderateur`, `admin`), connexion `POST /api/auth/login` avec session signée de 8 h, `GET /api/auth/me`, `POST /api/auth/logout` ; chaque route d'écriture exige le bon rôle (modération pour les signalements et dépotoirs, admin pour imports, scénarios, flotte, quartiers, recalculs) ; le journal signe chaque action « login (rôle) » au lieu de « system » ; outil `python -m salubri_api.users add|passwd|disable|list` ; `X-Salubri-Token` reste l'identifiant de service des scripts. Mots de passe en argon2id.
- **Pas de secret par défaut hors démonstration (lot A2)** : `SALUBRI_DEMO_MODE` (vrai dans `docker-compose.yml`) ; en démonstration, compte `demo` / `ouaga2026` créé tout seul et badge « Mode démonstration » dans l'interface ; hors démonstration, l'API refuse de démarrer avec un code vide ou `ouaga2026`, une clé de session courte, sans admin actif ou avec `demo` actif ; `run/start` génère les secrets dans `.env` au premier lancement ; `run/admin <login>` crée le premier admin.
- **Force brute et pourriel (lot A3)** : connexion bloquée 15 min après 5 échecs pour un même identifiant ou une même adresse (429 avec `Retry-After` et message en français) ; un téléphone qui dépasse `spam_per_hour × spam_block_factor` signalements par heure (10 × 3 par défaut, seuils de `params_default.json`) reçoit 429, sans casser le renvoi idempotent ; nginx limite les POST de connexion (10/min par IP) et de signalement (60/min par IP) et plafonne un signalement à 13 Mo ; Salubri Go garde un signalement refusé pour 429 « En attente » avec le motif affiché, et n'arrête plus de compter un 5xx comme envoyé.
- **Données personnelles (lot A4)** : sans compte, la liste et la fiche des signalements ne montrent que les signalements vérifiés ou nettoyés, sans appareil, commentaire, EXIF, règles ni nom du modérateur ; les modérateurs voient tout. Les photos ne sont plus servies en direct (`/photos/` retiré de nginx et de l'API) : `GET /api/reports/{id}/photo` sert une copie sans EXIF au public pour un signalement vérifié, l'original à la mairie, 404 sinon. Le journal est réservé aux modérateurs et admins. Salubri Map affiche « Vue publique » avec un bouton « Se connecter » ; « Autour de moi » (Salubri Go) est inchangé : il lit les dépotoirs, déjà sans donnée personnelle.
- **Téléversements (lot A5)** : une photo n'est acceptée que si Pillow la reconnaît comme JPEG, PNG ou WebP (l'extension ne compte pas), 12 Mo et 40 millions de pixels au plus (bombe de décompression refusée sans décodage) ; elle est réencodée en JPEG sans EXIF, réduite à 2560 px de côté, et enregistrée sous un nom aléatoire jamais choisi par l'appareil. Le GPS et la date EXIF restent en base pour les règles. Imports : archive ZIP lue en mémoire seulement, chemins `..` ou absolus refusés, 2 000 fichiers, 50 Mo par fichier, 200 Mo décompressés, taux de compression borné, taille annoncée contrôlée ; 60 Mo maximum par import côté API comme côté nginx.
- **Transport et en-têtes (lot A6)** : nginx envoie une CSP stricte compatible MapLibre et service worker (`script-src 'self'`, `frame-ancestors 'none'`), `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`, `Permissions-Policy` ; HSTS seulement sur le serveur HTTPS ; TLS 1.2+ ; version de nginx masquée. Base et API n'écoutent plus que sur `127.0.0.1` (le téléphone passe par nginx). Nouveau `docs/SECURITY.md` : acteurs, menaces, ce qui n'est pas protégé, mise en production avec Let's Encrypt, rotation des secrets. CI : `pip-audit` et `pnpm audit --prod` ; MapLibre 4 → 6.18 (faille XSS critique) et React Router 6 → 7.18 (deux failles modérées), plus aucune vulnérabilité connue.
- **Connexion web (lot A7)** : la fenêtre `window.prompt` du code d'accès est remplacée par un panneau « Connexion mairie » (identifiant + mot de passe, erreurs en français) ; la barre du haut affiche le compte connecté et son rôle, avec « Se déconnecter » (elle affichait toujours « Modérateur ») ; les boutons d'import, de scénario, de flotte et de modération sont grisés avec la raison (« Connectez-vous avec un compte administrateur », « Réservé aux administrateurs (vous êtes modérateur) ») ; une écriture refusée (401) ouvre le panneau puis réessaie. Le jeton reste en mémoire et dans `sessionStorage` (onglet), jamais dans une URL ; l'ancien code en `localStorage` est effacé.

## 0.2.1 — 16 novembre 2026

- Tournées : sur une grande zone (ville entière, 1 000+ points), la limite de temps du solveur s'adapte à la taille et le meilleur de OR-Tools et de l'heuristique de repli est retenu. Avant, un recalcul pouvait rendre un plan à 0 tournée.
- Reprise après redémarrage : les recalculs interrompus repartent tout seuls, les simulations interrompues sont marquées en échec avec un message clair.
- Pièges de répétition rangés par carte chargée (`data/rehearsal/traps/<carte>/`) : `rehearse` choisit le jeu qui correspond à la carte de l'API, fini les rapports rouges pour cause de jeu généré sur une autre carte.
- Salubri Go : le cache hors ligne ignore l'en-tête `Vary` (page blanche hors ligne derrière certains relais).
- Salubri Map/Sim : pages chargées à la demande, carte dans un fichier séparé (premier fichier 1 065 ko → 70 ko + bibliothèques en cache) ; affichage téléphone (barre d'onglets en bas) ; bouton « Ajouter un camion » qui ne déborde plus.
- Tests navigateur (`tests/e2e`) : hors ligne de Salubri Go de bout en bout, affichage de chaque page sur ordinateur et téléphone.

## 0.2.0 — 16 novembre 2026

- **Salubri Go** : application mobile (PWA) de signalement — photo (EXIF conservé), GPS avec badge de précision, type et volume, outbox hors ligne avec envoi idempotent, verdict des règles, dépotoirs autour de soi.
- L'image Docker `web` construit elle-même les deux interfaces : un clone neuf + `docker compose up` suffit (Node non requis).
- Code d'accès mairie (`X-Salubri-Token`) sur toutes les écritures sauf l'envoi d'un signalement ; CORS limité à la même origine.
- Démo téléphone : `run/telephone` (câble USB, `http://localhost/go/` sécurisé) et HTTPS local sur le port 8443 ; l'appli entière est mise en cache dès la première visite ; position manuelle vide par défaut et signalée ; la photo envoyée ne reste sur le téléphone qu'en vignette.
- Scénario sous-dimensionné : estimation du nombre de camions nécessaires.
- Pièges de répétition régénérés pour le réseau OSM réel (rapport vert).
- Tâches de fond suivies (plus de blocage des tests) ; 28 fichiers vides du squelette supprimés.

- Brigade Laabal remodelée : police civique (contrôles, dissuasion, abonnements forcés, évacuation par les riverains), sans ramassage. Le nettoyage des dépotoirs passe aux services techniques de la mairie.
- Flotte : ajout de camions par type (benne 8 t, benne 12 t, tracteur 4 t) et retrait sans perte d'historique, depuis le tableau de bord et la page Simulation.

## 0.1.0 — 16 novembre 2026

- API complète : signalements, 12 règles anti-pièges et score de confiance, consolidation en dépotoirs, import GeoJSON/CSV/ZIP avec rapport et annulation, exports GeoJSON/CSV/OSM.
- Plan de gestion : îlots, placement contraint des points de regroupement, tournées OR-Tools (repli Clarke-Wright), distances OSRM (repli haversine).
- Simulation multi-agents journalière (ménages, pré-collecteurs, points, mairie, brigade Laabal en contrôle civique, nettoyage par la mairie), réplications.
- Chaîne de recalcul événementielle avec cache par étape, versions immuables, progression en SSE, différences entre versions.
- Ville synthétique de démonstration, jeu de pièges et script de répétition de l'épreuve.
- Docker Compose, scripts de lancement Windows/Linux, CI.

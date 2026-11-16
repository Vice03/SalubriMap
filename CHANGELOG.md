# Journal des versions

## 0.3.0 — en cours

- **Comptes et rôles (lot A1)** : comptes de la mairie (`moderateur`, `admin`), connexion `POST /api/auth/login` avec session signée de 8 h, `GET /api/auth/me`, `POST /api/auth/logout` ; chaque route d'écriture exige le bon rôle (modération pour les signalements et dépotoirs, admin pour imports, scénarios, flotte, quartiers, recalculs) ; le journal signe chaque action « login (rôle) » au lieu de « system » ; outil `python -m salubri_api.users add|passwd|disable|list` ; `X-Salubri-Token` reste l'identifiant de service des scripts. Mots de passe en argon2id.

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

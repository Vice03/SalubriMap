# Journal des versions

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

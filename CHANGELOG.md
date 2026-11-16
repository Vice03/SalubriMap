# Journal des versions

## 0.2.0 — 16 novembre 2026

- Brigade Laabal remodelée : police civique (contrôles, dissuasion, abonnements forcés, évacuation par les riverains), sans ramassage. Le nettoyage des dépotoirs passe aux services techniques de la mairie.
- Flotte : ajout de camions par type (benne 8 t, benne 12 t, tracteur 4 t) et retrait sans perte d'historique, depuis le tableau de bord et la page Simulation.

## 0.1.0 — 16 novembre 2026

- API complète : signalements, 12 règles anti-pièges et score de confiance, consolidation en dépotoirs, import GeoJSON/CSV/ZIP avec rapport et annulation, exports GeoJSON/CSV/OSM.
- Plan de gestion : îlots, placement contraint des points de regroupement, tournées OR-Tools (repli Clarke-Wright), distances OSRM (repli haversine).
- Simulation multi-agents journalière (ménages, pré-collecteurs, points, mairie, brigade Laabal en contrôle civique, nettoyage par la mairie), réplications.
- Chaîne de recalcul événementielle avec cache par étape, versions immuables, progression en SSE, différences entre versions.
- Ville synthétique de démonstration, jeu de pièges et script de répétition de l'épreuve.
- Docker Compose, scripts de lancement Windows/Linux, CI.

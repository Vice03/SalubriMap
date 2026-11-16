# Salubri Go (PWA)

Application mobile du citoyen : photo + GPS + type de déchets, **fonctionne hors ligne** (outbox IndexedDB, envoi automatique au retour du réseau, envoi idempotent via `client_id`), liste des dépotoirs autour de soi.

- Servie par nginx sous `/go/` (build : `pnpm --filter go build`, fait automatiquement par l'image Docker `web`).
- Dev : `pnpm --filter go dev` → http://localhost:5174/go/ (API relayée vers `localhost:8000`).
- **GPS sur téléphone** : les navigateurs n'autorisent la géolocalisation qu'en HTTPS (ou sur `localhost`). Sur le réseau local en HTTP, la position se saisit à la main (signalement « à revoir » par la mairie).

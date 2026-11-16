# Salubri Map + Sim (interface web)

Tableau de bord de la mairie : carte, signalements et modération, import du jeu du jury, scénarios et recalcul en direct, comparaison, journal.

```bash
pnpm install                 # à la racine du dépôt
pnpm --filter web dev        # http://localhost:5173 (l'API doit tourner sur http://localhost:8000)
pnpm --filter web build      # produit apps/web/dist, servi par nginx sur http://localhost
```

Contrat avec l'API : [`docs/FRONTEND_CONTEXT.md`](../../docs/FRONTEND_CONTEXT.md). Stack : React 18, TypeScript strict, Vite, MapLibre GL, lucide-react, Inter (locale).

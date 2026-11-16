# Architecture

```
 Salubri Go (PWA)        Salubri Map + Sim (web)
        \                       /
         \   HTTPS / JSON / SSE /
          v                    v
      ┌──────────── nginx (port 80) ─────────────┐
      │ /  /go/            →  fichiers statiques │
      │ /api/  →  api:8000 (SSE non bufferisé)    │
      └──────────────────┬───────────────────────┘
                         v
      ┌──────────── salubri-api (FastAPI) ───────────────┐
      │ routers/  reports imports dumps scenarios plans  │
      │           quartiers export audit validation sim  │
      │ services/ validation (R1–R12)  consolidation     │
      │           demand  planning (points, distances,   │
      │           VRP)  simulation (ABM)  plan/pipeline  │
      │           importers  export                      │
      └──────┬───────────────────────┬───────────────────┘
             v                       v
   PostgreSQL 16 + PostGIS 3.4    OSRM (sec) / OSRM (pluie)
```

Services Docker : `db`, `seed` (une fois, idempotent), `api`, `web` (nginx), `osrm`, `osrm_rain` (facultatifs : sans extrait OSM ils attendent et l'API calcule des distances à vol d'oiseau × 1,35).

## Chaîne de recalcul

Tout changement crée un événement (`plan_events`) et une nouvelle version de plan (`plan_versions`, immuable). Un seul calcul à la fois par scénario ; les demandes arrivées pendant un calcul sont fusionnées en un seul calcul suivant (les versions intermédiaires passent en `superseded`). En cas d'erreur, la version `failed` est conservée pour diagnostic et la version prête précédente reste servie.

| Étape | Rôle | Recalculée quand |
|---|---|---|
| E1 | Consolider les signalements vérifiés en dépotoirs (DBSCAN 30 m) | l'ensemble des signalements vérifiés change |
| E2 | Îlots actifs et demande (kg/jour) | quartiers, population, déchets/hab., saison |
| E3 | Points de regroupement | fréquences et capacités ; nouveau quartier (mode incrémental : points existants figés) |
| E4 | Matrice des distances (OSRM ou haversine) | positions des points, saison |
| E5 | Tournées (OR-Tools CVRPTW, multi-rotations, points abandonnables) | flotte, charges, matrice |
| E6 | Simulation 90 jours | tout ce qui précède, budget, abonnements |
| E7 | Différences avec la version précédente | toujours |

Chaque étape a une clé (hachage de ses entrées) : si la clé n'a pas changé, le résultat est réutilisé (`cache_hit`). La progression est poussée en Server-Sent Events sur `/api/plans/{id}/events`.

## Algorithmes

- **Validation** : 12 règles pures sur un contexte préparé par des requêtes PostGIS (voisins, bâtiment contenant, eau, POI, historique de l'appareil). Score = 100 + Σ pénalités. Détails : [RULES.md](RULES.md).
- **Îlots** : bâtiments regroupés par k-moyennes (≈ 30 bâtiments), population du quartier répartie au prorata de la surface bâtie ; sans bâtiments, grille de 250 m.
- **Points de regroupement** : k-moyennes pondérées par la demande, projection sur la voie praticable la plus proche, évitement des exclusions (bâtiments, eau + 15 m, écoles/marchés + 50 m, cimetières, zones militaires) par recherche en grille élargie, ajout de points si un point dépasse 120 % de sa capacité.
- **Tournées** : OR-Tools, dimensions capacité et temps, fenêtres horaires (marchés 05 h–08 h, reste 07 h–17 h), 2 rotations par camion, pénalité de non-desserte (le modèle reste faisable quand la flotte manque) ; repli Clarke-Wright + 2-opt.
- **Simulation** : pas journalier, ménages agrégés par îlot, pré-collecteurs, points, mairie (pannes aléatoires, budget mensuel), services techniques de la mairie (nettoyage par priorité ; la brigade Laabal agit par contrôles dissuasifs, sans ramassage) (priorité volume × proximité de l'eau × âge). Flux en valeur espérée, conservation de la masse vérifiée à chaque exécution.

## Choix techniques

| Couche | Choix | Pourquoi |
|---|---|---|
| API | FastAPI, Pydantic v2, SQLAlchemy 2, GeoAlchemy2 | validation stricte des imports, OpenAPI automatique |
| Base | PostgreSQL 16 + PostGIS 3.4 | requêtes spatiales indexées |
| Optimisation | OR-Tools | référence libre (Apache-2.0), limite de temps garantie |
| Itinéraires | OSRM sur extrait OSM local | matrice n×n en une requête, aucun appel externe |
| Simulation | moteur maison numpy | déterministe, < 1 s, lisible |

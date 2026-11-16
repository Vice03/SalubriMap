# Salubri — contexte pour construire le front-end

Ce document est tout ce qu'il faut pour construire **Salubri Map + Sim** (`apps/web`) et **Salubri Go** (`apps/go`) contre le backend qui existe déjà dans `apps/api`. Les exemples de réponses ci-dessous ont été copiés depuis l'API réelle lancée sur les données de démonstration ; seuls les tableaux ont été raccourcis (`…`).

Le contrat machine complet est dans [`docs/openapi.json`](openapi.json) (et en direct sur `http://localhost/api/docs`). Si une réponse de ce document et l'OpenAPI divergent, l'API qui tourne fait foi : signale-le pour qu'on corrige ce fichier.

---

## 1. Le produit en 30 secondes

Ouagadougou a des dépotoirs sauvages. Salubri :

1. **collecte des signalements** (photo + GPS) depuis un téléphone, même hors ligne → **Salubri Go** ;
2. **vérifie** chaque signalement avec 12 règles anti-pièges (R1–R12), donne un **score de confiance 0–100** et un **statut** → affiché dans **Salubri Map** ;
3. regroupe les signalements vérifiés en **dépotoirs** ;
4. calcule un **plan de collecte** (points de regroupement + tournées de camions) et **simule 90 jours** de la ville (ménages, pré-collecteurs, brigade Laabal, mairie) → **Salubri Sim** ;
5. **recalcule en direct** quand on change un paramètre (camion en panne, saison des pluies, nouveau quartier, budget…). C'est le cœur de l'épreuve du jury : il faut **montrer la progression** (étapes E1→E7) et **le résumé des changements**.

Tout le texte visible est en **français**.

---

## 2. Lancer le backend sur ta machine

Seul Docker est nécessaire.

```bash
docker compose up --build        # ou double-clic run/start.bat sous Windows
```

- Le premier démarrage charge la ville de démonstration (24 quartiers, ~50 000 bâtiments synthétiques, 380 signalements, 2 scénarios) puis calcule les premiers plans : compter ~1 min.
- API : `http://localhost/api/...` (via nginx) ou `http://localhost:8000/api/...` (direct).
- Documentation interactive : `http://localhost/api/docs`.
- Repartir de zéro : `docker compose down -v && docker compose up --build`.

### Développer le front avec Vite

Lance le backend avec Docker, puis ton front en `pnpm dev` avec un proxy :

```ts
// vite.config.ts (apps/web) — même chose pour apps/go avec base: '/go/'
export default defineConfig({
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/photos': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
```

Le CORS est ouvert (`*`) par défaut, donc appeler `http://localhost:8000` directement marche aussi.

### Où mettre tes builds

nginx sert déjà :

| URL | Dossier servi | Remarque |
|---|---|---|
| `/` | `apps/web/dist/` | Salubri Map + Sim (SPA : toute URL inconnue renvoie `index.html`) |
| `/go/` | `apps/go/dist/` | Salubri Go (PWA, `base: '/go/'` dans Vite) |
| `/api/` | API FastAPI | SSE non bufferisé |
| `/photos/` | photos téléversées | URLs fournies par l'API (`photo_url`) |

Tant que `dist/` est vide, nginx affiche une page d'attente. Il suffit donc de faire `pnpm build` : les dossiers sont montés dans le conteneur, pas besoin de reconstruire l'image.

---

## 3. Conventions de l'API

| Sujet | Règle |
|---|---|
| Préfixe | Tout est sous `/api`. |
| Identifiants | UUID en chaîne (`"07815c72-3dc4-…"`). |
| Coordonnées | **GeoJSON : `[longitude, latitude]`** (attention à l'ordre), WGS84. Les formulaires d'envoi utilisent des champs séparés `lat` / `lon`. |
| Cartes | Les listes géographiques sont des **FeatureCollection** GeoJSON, directement utilisables comme `source` MapLibre ou couche Leaflet. Les attributs sont dans `feature.properties`. |
| Dates | ISO 8601 avec fuseau (`2026-11-16T18:03:00+00:00`). Afficher en heure locale (Ouagadougou = UTC+0). |
| Heures de tournée | En **minutes après minuit** (`arrival_min: 430.8` = 07 h 10). `time_window: [420, 1020]` = 07 h 00–17 h 00. |
| Montants | Francs CFA (FCFA), nombres. Formater avec espaces : `25 000 000 FCFA`. |
| Masses | tonnes (`_t`), kilogrammes (`_kg`). Volumes en m³ (`_m3`). |
| Paramètres multiples | Répéter la clé : `?status=to_review&status=rejected`. |
| `bbox` | `minLon,minLat,maxLon,maxLat` (ex. `map.getBounds().toArray().flat().join(',')`). |
| Pagination | `limit` (≤ 5000, défaut 1000) et `offset` ; la réponse donne `total`. |
| Erreurs | Format RFC 7807, `Content-Type: application/problem+json` (voir §9). |

---

## 4. Vocabulaire et libellés à afficher

### Types de déchet (`waste_type`) — une icône illustrée par type

| Valeur API | Libellé | Icône proposée |
|---|---|---|
| `household` | Ménager | sac poubelle |
| `plastic` | Plastique | bouteille |
| `rubble` | Gravats | briques |
| `organic` | Organique | feuille / épluchure |
| `medical` | Biomédical | seringue barrée |
| `mixed` | Mixte | tas mélangé |
| `other` | Autre | point d'interrogation |

### Volume (`volume_class`)

| Valeur | Libellé | Volume utilisé pour l'estimation |
|---|---|---|
| `bag` | Sac | 0,05 m³ |
| `wheelbarrow` | Brouette | 0,1 m³ |
| `cart` | Charrette | 0,6 m³ |
| `truck` | Camion | 6 m³ |
| `more` | Plus | 12 m³ |

### Statut d'un signalement (`status`)

| Valeur | Libellé | Couleur conseillée | Sens |
|---|---|---|---|
| `pending` | En attente | gris | Pas encore évalué (rare, transitoire) |
| `probable` | Probable | bleu | Score ≥ 70, pas encore confirmé |
| `verified` | Vérifié | vert `#2F7D3E` | Confirmé par un modérateur ou par 2 appareils indépendants |
| `to_review` | À revoir | orange `#F28C28` | Score 40–69 |
| `rejected` | Rejeté | terre rouge `#B7410E` | Score < 40 ou rejet d'office (R5, R7 grand plan d'eau, R8 0,0) |
| `cleaned` | Nettoyé | gris-vert | Le dépotoir a été nettoyé par la brigade |

Seuls les `verified` entrent dans les dépotoirs et donc dans le plan.

### Statut d'un dépotoir (`dump_sites[].status`)

| Valeur | Libellé |
|---|---|
| `active` | Actif |
| `recurring` | Récidive (réapparu moins de 15 jours après un nettoyage) |
| `cleaned` | Nettoyé |

### Règles anti-pièges

La liste officielle (codes, titres, descriptions, pénalités) vient de `GET /api/validation/rules` : **ne pas la recopier en dur**, l'afficher depuis l'API (le jury doit pouvoir la lire à l'écran). Codes : `R1` à `R12`, plus `MOD` pour une action de modérateur (fusion).

### Événements de recalcul (`event`)

| Valeur | Libellé |
|---|---|
| `reports_changed` | Nouveaux signalements |
| `fleet_changed` | Flotte modifiée |
| `season_changed` | Changement de saison |
| `zone_changed` | Nouveau quartier |
| `budget_changed` | Budget modifié |
| `frequency_changed` | Fréquences / capacités modifiées |
| `subscription_changed` | Abonnements modifiés |
| `manual` | Recalcul complet |

### Étapes du pipeline (`stage`)

`E1` Consolidation des signalements · `E2` Demande par îlot · `E3` Points de regroupement · `E4` Matrice des distances · `E5` Tournées · `E6` Simulation 90 jours · `E7` Différences. Le nom français est fourni dans chaque événement (`name`). `cache_hit: true` = étape réutilisée (afficher en gris « réutilisé »), `false` = recalculée (en couleur, avec la durée).

### Statut d'une version de plan

`pending` (en file) → `running` → `ready` ; ou `failed` (l'ancienne version reste affichée) ; ou `superseded` (fusionnée dans une version plus récente : suivre la plus récente).

---

## 5. Identité visuelle (rappel)

Le design doit être riche et contrasté, pas fade : icônes illustrées, tuiles KPI en couleurs pleines, cartes vivantes.

| Jeton | Couleur |
|---|---|
| Vert latérite (primaire, en-tête) | `#2F6B3A` |
| Terre rouge (rejet, dépotoirs) | `#B7410E` |
| Orange alerte (à revoir, points de regroupement) | `#F28C28` |
| Sable (fond) | `#F3E9D2` |
| Charbon (texte) | `#1F1D1A` |
| Blanc cassé (panneaux) | `#FBF8F2` |

Police : Inter, incluse localement (pas de CDN : la salle n'aura peut-être pas Internet). Trois directions d'interface ont été proposées (A « Terre et Carte », B « Poste de commande », C « Faso Danfani ») : la maquette retenue fait foi.

Fond de carte : tuiles raster OSM `https://tile.openstreetmap.org/{z}/{x}/{y}.png` avec l'attribution obligatoire « © contributeurs OpenStreetMap ». Prévoir un repli hors ligne (voir §12).

---

## 6. Écrans et endpoints, écran par écran

### 6.1 En-tête / tableau de bord — compteurs

`GET /api/reports/stats`

```json
{
  "total": 434,
  "by_status": {"rejected": 8, "verified": 351, "probable": 62, "to_review": 13},
  "by_type": {"organic": 57, "mixed": 78, "plastic": 51, "medical": 15, "rubble": 45, "household": 177, "other": 11},
  "by_rule": {"R7": 3, "R10": 3, "R5": 4, "R2": 3, "R12": 16, "R11": 2, "R3": 1, "R1": 3, "R9": 1, "R6": 4, "R8": 7, "R4": 1},
  "dump_sites": {"active": 123}
}
```

Les clés absentes valent 0.

### 6.2 Carte (Salubri Map)

Au chargement :

1. `GET /api/communes/ouagadougou` → centre, emprise, dépôt des camions :

```json
{
  "id": "…", "slug": "ouagadougou", "name": "Ouagadougou",
  "bbox": [-1.62, 12.28, -1.42, 12.46],
  "center": [-1.52, 12.37],
  "depot": [-1.5, 12.47],
  "params_default": {"…": "…"}
}
```

2. `GET /api/quartiers` → FeatureCollection de MultiPolygon. Propriétés : `id, name, arrondissement, population, active, source, n_ilots`.
3. `GET /api/reports?bbox=…` → signalements (voir 6.3).
4. `GET /api/dump-sites` → dépotoirs consolidés, triés par priorité décroissante.
5. Le plan du scénario sélectionné : `GET /api/plans/{latest_ready_plan_id}/points` et `/routes` (voir 6.6).

Couches recommandées : quartiers (contour vert), signalements (icône du type + halo de la couleur du statut, taille selon le volume), dépotoirs (cercle terre rouge, rayon ∝ `volume_est_m3`), points de regroupement (losange orange), tournées (une couleur par camion), dépôt (pictogramme camion).

Dépotoir (`GET /api/dump-sites`, une Feature) :

```json
{
  "type": "Feature",
  "geometry": {"type": "Point", "coordinates": [-1.4662565, 12.3104987]},
  "properties": {
    "id": "e808c14c-…", "status": "active", "waste_type": "plastic", "volume_est_m3": 12.0,
    "n_reports": 3, "first_reported_at": "2026-10-11T07:11:41.126845+00:00", "last_reported_at": "2026-10-13T16:30:27.073033+00:00",
    "near_water": false, "priority": 26.476, "confidence": 100.0, "osm_id": null
  },
  "id": "e808c14c-…"
}
```

Filtres de `GET /api/dump-sites` : `status` (répétable), `bbox`.

### 6.3 Liste et filtres des signalements

`GET /api/reports` — filtres (tous optionnels, combinables) :

| Paramètre | Exemple | Effet |
|---|---|---|
| `status` (répétable) | `status=to_review&status=rejected` | |
| `type` (répétable) | `type=plastic` | type de déchet |
| `quartier` | UUID | |
| `since`, `until` | ISO 8601 | sur `reported_at` |
| `bbox` | `-1.6,12.3,-1.4,12.45` | |
| `min_score`, `max_score` | `max_score=69` | |
| `rule` | `R2` | signalements où cette règle s'est déclenchée |
| `device_id` | | tous les envois d'un appareil (pour montrer un spam) |
| `import_batch` | UUID | les lignes d'un import (ex. le fichier du jury) |
| `limit`, `offset` | | pagination |

Réponse (réelle, piège R9 de la répétition) :

```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [-1.4541067, 12.3896032]},
    "properties": {
      "id": "d14c7429-81d6-4c4e-a6fe-420111c392f6",
      "status": "to_review",
      "score": 60,
      "rule_hits": [{"rule": "R9", "delta": -40, "detail": "16.1 km en 3 min, soit 322 km/h"}],
      "waste_type": "household",
      "volume_class": "cart",
      "comment": null,
      "reported_at": "2026-11-16T18:03:00+00:00",
      "received_at": "2026-11-16T11:46:33.836132+00:00",
      "gps_accuracy_m": 8.0,
      "device_id": "trap-r9",
      "external_id": "trap-032-r9-jump",
      "duplicate_of": null,
      "dump_site_id": null,
      "quartier_id": "5bf66512-c7f7-4ce7-a074-8e18cbfe59f3",
      "import_batch_id": "21a8c6d0-2573-4854-ad7a-89641343a5e1",
      "photo_url": "/photos/b79af5a98db33cd0a0bcebe383f6fb2e.jpg",
      "forced_status": false,
      "moderated_by": null,
      "moderated_at": null
    },
    "id": "d14c7429-81d6-4c4e-a6fe-420111c392f6"
  }],
  "total": 13, "limit": 1, "offset": 0
}
```

`photo_url` est relatif : l'utiliser tel quel derrière nginx, ou préfixer avec l'origine de l'API en développement. `rule_hits` peut contenir `"reject": true` (rejet d'office).

### 6.4 Fiche d'un signalement (tiroir)

`GET /api/reports/{id}` → la même Feature, avec en plus dans `properties` :

```json
"related": [{"id": "…", "status": "probable", "score": 100, "relation": "original"}],
"dump_site": {"id": "…", "status": "active", "n_reports": 3},
"photo": {"width": 640, "height": 480, "bytes": 118342, "exif_lat": null, "exif_lon": null, "exif_taken_at": null}
```

`relation` vaut `original` (ce signalement est un doublon de celui-ci) ou `duplicate` (celui-ci a été copié par…).

À afficher : photo, mini-carte, jauge du score (0–100, couleur du statut), **la liste des règles avec leur pénalité et le détail** (`R2 −70 : Photo identique à celle du signalement 4f1c2a9b`), les signalements liés cliquables.

Actions du modérateur :

| Action | Appel | Réponse |
|---|---|---|
| Vérifier / Rejeter / Remettre à revoir | `PATCH /api/reports/{id}` `{"status": "verified" \| "rejected" \| "to_review" \| "probable" \| "cleaned", "note": "vu sur place", "actor": "moderateur"}` | la Feature mise à jour (`forced_status: true`) |
| Rejouer les règles | `POST /api/reports/{id}/revalidate` | la Feature recalculée (annule un forçage) |
| Fusionner dans un autre | `POST /api/reports/{id}/merge` `{"into": "<id du signalement cible>"}` | la Feature (statut `rejected`, règle `MOD`) |

Toutes ces actions sont journalisées et déclenchent (2 s plus tard) un recalcul `reports_changed` des plans.

### 6.5 Import (fichier du jury)

`POST /api/imports` en `multipart/form-data` :

| Champ | Valeur |
|---|---|
| `file` | `.geojson`, `.json`, `.csv` ou `.zip` (le fichier + ses photos) |
| `format` | `auto` (défaut), `geojson`, `csv` |
| `dry_run` | `true` pour **prévisualiser sans enregistrer** |
| `uploaded_by` | optionnel |

Réponse :

```json
{
  "batch_id": "21a8c6d0-…",
  "dry_run": false,
  "format": "csv",
  "rows_total": 10,
  "accepted": 8,
  "rejected": 2,
  "report": [
    {"row": 1, "status": "accepted", "errors": [], "warnings": [], "report_id": "…", "external_id": null,
     "score": 100, "report_status": "probable", "rule_hits": []},
    {"row": 9, "status": "rejected", "errors": ["Coordonnées manquantes (lat/lon)"], "warnings": [],
     "report_id": null, "external_id": null, "score": null, "report_status": null, "rule_hits": []},
    {"row": 10, "status": "rejected", "errors": ["Date invalide : « 31/02/2026 » (attendu ISO 8601 ou JJ/MM/AAAA)"],
     "warnings": [], "report_id": null, "external_id": null, "score": null, "report_status": null, "rule_hits": []}
  ]
}
```

Attention : `status` d'une ligne = la ligne a-t-elle été **lue** (`accepted`/`rejected`) ; `report_status` = le **verdict des règles** sur le signalement créé. Une ligne peut être `accepted` avec `report_status: "rejected"` (c'est un piège détecté). Avertissements possibles : `coords_swapped : …` (lat/lon inversées puis corrigées), photo absente de l'archive, type inconnu.

UI conseillée : glisser-déposer → appel avec `dry_run=true` → tableau ligne par ligne → bouton « Importer pour de vrai » (même fichier, `dry_run=false`) → bouton « Annuler l'import » (`POST /api/imports/{batch_id}/rollback` → `{"reverted": 8, "already": false}`).

Historique : `GET /api/imports` (liste) et `GET /api/imports/{id}` (rapport). Formats de fichier : `docs/IMPORT.md`.

### 6.6 Scénario (Salubri Sim)

**Liste et détail** — `GET /api/scenarios` (tableau) / `GET /api/scenarios/{id}` :

```json
{
  "id": "256ed43a-8661-44d9-8226-95cbbeebff63",
  "name": "Zone pilote",
  "parent_id": null,
  "is_baseline": true,
  "params": {
    "population_factor": 1.0, "waste_kg_per_person_day": 0.6, "subscription_rate": 0.35,
    "subscription_fee_fcfa_month": 1500.0, "precollector_capacity_t": 1.2, "precollector_frequency_per_week": 2.0,
    "precollector_cost_fcfa_month": 60000.0, "collection_point_capacity_t": 2.5, "collection_point_max": 80,
    "pickup_frequency_per_week": 2.0, "walk_distance_max_m": 300.0, "season": "dry", "flood_speed_factor": 0.7,
    "truck_breakdown_rate_per_day": 0.02, "budget_fcfa_month": 25000000.0, "fuel_cost_fcfa_per_km": 450.0,
    "cleanup_capacity_t_day": 12.0, "laabal_operations_per_week": 3, "laabal_deterrence": 0.5, "active_quartier_ids": ["6f153a3c-d5b3-468e-9890-dea40d6d8a54"],
    "horizon_days": 90, "seed": 42, "vrp_time_limit_s": 1.0, "ilot_size_buildings": 30
  },
  "vehicles": [
    {"id": "80221311-…", "label": "BF-01", "kind": "truck_8t", "capacity_t": 8.0, "cost_per_km": 450.0,
     "fixed_cost_day": 20000.0, "out_of_service": false, "shift_start": 300, "shift_end": 1080}
  ],
  "latest_ready_plan_id": "07815c72-3dc4-4506-9237-dffd6eccdab9",
  "latest_plan_id": "07815c72-3dc4-4506-9237-dffd6eccdab9",
  "latest_plan_status": "ready",
  "updated_at": "2026-11-16T11:39:02.789117+00:00"
}
```

`active_quartier_ids: null` = tous les quartiers actifs. **Toujours afficher `latest_ready_plan_id`** sur la carte ; `latest_plan_id` peut être en cours de calcul.

**Formulaire de paramètres** — ne pas coder les champs en dur : `GET /api/scenarios/params-schema` renvoie le JSON Schema avec, pour chaque champ, `type`, `minimum`/`maximum`, `default`, `enum` (pour `season`), un **libellé français** (`label`) et l'événement qu'il déclenche (`event`). Groupes suggérés : Population et abonnements · Pré-collecte · Points et enlèvement · Flotte · Budget · Saison · Quartiers. Masquer par défaut `seed`, `vrp_time_limit_s`, `ilot_size_buildings`, `horizon_days` (onglet « Avancé »).

**Modifier** — `PATCH /api/scenarios/{id}` avec seulement ce qui change :

```json
{"params": {"season": "rain"}}
{"params": {"budget_fcfa_month": 17500000}}
{"vehicles": [{"id": "80221311-…", "out_of_service": true}, {"id": "7d430392-…", "out_of_service": true}]}
```

Réponse : `{"scenario": {…}, "plan_version_id": "…", "event": "season_changed"}` (`plan_version_id: null` si rien n'a changé). Plusieurs camions d'un coup : **un seul PATCH** (un seul recalcul). Paramètre invalide → 422.

Raccourcis :

| Action | Appel |
|---|---|
| Camion en panne / réparé | `POST /api/scenarios/{id}/vehicles/{vehicle_id}/breakdown` `{"out_of_service": true}` → `{"plan_version_id", "vehicle", "event"}` |
| Recalcul complet | `POST /api/scenarios/{id}/recompute` `{"reason": "…"}` → `{"plan_version_id", "event": "manual"}` |
| Nouveau scénario (copie) | `POST /api/scenarios` `{"name": "Saison des pluies", "parent_id": "<id>", "params": {"season": "rain"}}` → le scénario + `plan_version_id` (201) |
| Supprimer | `DELETE /api/scenarios/{id}` → 204 (409 pour le scénario de base) |

**Nouveau quartier (épreuve du jury)** — l'utilisateur dessine un polygone sur la carte, saisit un nom et une population :

```http
POST /api/quartiers
{"type": "Feature",
 "geometry": {"type": "Polygon", "coordinates": [[[-1.555, 12.284], [-1.525, 12.284], [-1.525, 12.298], [-1.555, 12.298], [-1.555, 12.284]]]},
 "properties": {"name": "Secteur nouveau", "population": 45000, "scenario_id": "<optionnel>"}}
```

Réponse (201) : `{"quartier": <Feature>, "plans": [{"scenario_id": "…", "plan_version_id": "…"}]}`. Sans `scenario_id`, tous les scénarios sont recalculés. Les points existants **ne bougent pas** (`frozen: true`) : seuls des points sont ajoutés pour couvrir la nouvelle zone. `DELETE /api/quartiers/{id}` retire un quartier ajouté depuis l'interface.

### 6.7 Suivre un recalcul en direct (SSE)

Chaque modification renvoie un `plan_version_id`. Ouvrir immédiatement :

```ts
const es = new EventSource(`/api/plans/${planVersionId}/events`)
es.addEventListener('running', e => { /* {version, event} */ })
es.addEventListener('stage_started', e => { const {stage, name} = JSON.parse(e.data) /* étape en cours */ })
es.addEventListener('stage_done', e => { const {stage, name, duration_ms, cache_hit} = JSON.parse(e.data) })
es.addEventListener('ready', e => { const {version, summary} = JSON.parse(e.data); es.close(); /* recharger points, tournées, KPI */ })
es.addEventListener('failed', e => { const {error} = JSON.parse(e.data); es.close(); /* toast rouge, garder l'ancien plan */ })
es.addEventListener('superseded', e => { const {by} = JSON.parse(e.data); es.close(); /* rouvrir sur `by` */ })
```

Flux réel :

```
event: running
data: {"version": 10, "event": "reports_changed"}

event: stage_started
data: {"stage": "E1", "name": "Consolidation des signalements"}

event: stage_done
data: {"stage": "E1", "name": "Consolidation des signalements", "duration_ms": 369, "cache_hit": false}

event: stage_started
data: {"stage": "E2", "name": "Demande par îlot"}

event: stage_done
data: {"stage": "E2", "name": "Demande par îlot", "duration_ms": 0, "cache_hit": true}
…
event: ready
data: {"version": 10, "summary": {…}}
```

Règles d'affichage :

- Afficher **les 7 étapes** dès l'ouverture (grises), les colorer au fil de l'eau : recalculée = couleur + durée, réutilisée = gris « réutilisé ».
- **Ne basculer la carte qu'à `ready`** : jusque-là, continuer d'afficher l'ancien plan (`latest_ready_plan_id`).
- Après `ready`, afficher `summary.diff.text` en toast (ex. « 2 tournées refaites, +3 points non desservis, +14 % de km »).
- Si l'événement est déjà terminé quand tu te connectes, le serveur rejoue les étapes puis `ready`/`failed` immédiatement.
- Plan B sans SSE : interroger `GET /api/plans/{id}` toutes les 300 ms jusqu'à `status` ∈ `ready`/`failed`/`superseded`.
- Durées typiques sur la démo (sans OSRM) : panne 1,1 s · pluie 1,2 s · nouveau quartier 1,4 s · budget 0,2 s.

### 6.8 Plan : points, tournées, résumé

`GET /api/plans/{id}` :

```json
{
  "id": "07815c72-…", "scenario_id": "256ed43a-…", "version": 10, "status": "ready",
  "event": "reports_changed", "distance_mode": "approx",
  "stages": [{"stage": "E1", "name": "Consolidation des signalements", "duration_ms": 369, "cache_hit": false}, "…"],
  "summary": {
    "ilots": 80, "population": 59900, "demand_t_week": 251.58, "points": 55, "points_constraint_relaxed": 0,
    "routes": 13, "vehicles_available": 8, "km_day": 489.8, "cost_day_fcfa": 336738,
    "unserved_points": 0, "unserved_t_per_pickup": 0.0, "distance_mode": "approx", "solver": "ortools", "notes": [],
    "dump_sites": 123, "duration_ms": 369,
    "diff": {"first_version": false, "points_added": 0, "points_removed": 0, "points_moved": 0, "routes_changed": 0,
             "km_delta": 0.0, "km_delta_pct": 0.0, "cost_delta": 0, "unserved_delta": 0, "text": "Aucun changement"},
    "sim": {"produced_t": 3234.6, "collected_t": 2711.92, "precollected_t": 186.43, "wild_dump_t": 411.4,
            "wild_dumps_active_final": 0, "wild_dumps_active_mean": 0.3, "cleanup_t": 411.4, "laabal_controls": 234, "laabal_cleared_t": 35.2,
            "mean_cleanup_delay_days": 1.0, "overflow_point_days": 519, "truck_km": 12546.6, "cost_total_fcfa": 10125989.0,
            "cost_per_t": 3734.0, "coverage_rate": 0.839, "subscription_rate_final": 0.3064, "precollectors_dropped": 0,
            "recurring_dumps": 59, "mass_balance_error": 1.4e-16}
  },
  "error": null, "created_at": "…", "started_at": "…", "finished_at": "…"
}
```

- `distance_mode: "approx"` → **bandeau orange** « Distances approximatives (OSRM indisponible) ». `"osrm"` → rien.
- `?daily=true` ajoute `summary.sim_daily` : séries journalières pour les graphiques (clés : `produced_t, precollected_t, voluntary_t, truck_collected_t, wild_new_t, wild_stock_t, wild_dumps_active, cleanup_t, laabal_controls, laabal_cleared_t, overflow_points, truck_km, cost_fcfa, household_stock_t, coverage_rate, subscription_rate`, un nombre par jour).

`GET /api/plans/{id}/points` — FeatureCollection de Point :

```json
{"type": "Feature", "geometry": {"type": "Point", "coordinates": [-1.5229011, 12.3689328]},
 "properties": {"id": "728fc946-…", "key": "P001", "label": "P001", "capacity_t": 2.5, "demand_t_week": 3.042,
                "fill_ratio_per_pickup": 0.608, "n_ilots": 1, "frozen": false, "time_window": [420, 1020], "unserved": false}}
```

`key` est **stable d'une version à l'autre** (utile pour animer un point qui bouge). `unserved: true` → afficher en rouge. `fill_ratio_per_pickup > 1` = point qui déborde.

`GET /api/plans/{id}/routes` — FeatureCollection de LineString (une par rotation de camion) :

```json
{"type": "Feature",
 "geometry": {"type": "LineString", "coordinates": [[-1.5, 12.47], [-1.52619, 12.37049], [-1.52788, 12.36893], "…"]},
 "properties": {"id": "…", "vehicle_id": "80221311-…", "vehicle_label": "BF-01", "vehicle_kind": "truck_8t",
                "capacity_t": 8.0, "rotation": 1, "distance_km": 34.672, "duration_min": 206.2, "load_t": 7.55,
                "cost_fcfa": 35602.0,
                "stops": [{"seq": 1, "point_key": "P023", "point_id": "b7ecea22-…", "arrival_min": 420.0, "load_t_after": 1.6},
                          {"seq": 2, "point_key": "P042", "point_id": "68733b6f-…", "arrival_min": 430.8, "load_t_after": 4.1}]}}
```

En mode `approx`, les tracés sont des segments droits entre les arrêts ; avec OSRM, ils suivent les routes.

Autres : `GET /api/plans/{id}/unserved` → `[{"point_id", "point_key", "demand_t_week", "reason"}]` ; `GET /api/plans/{id}/diff?against=<autre id>` → l'objet `diff` (par défaut contre la version prête précédente).

**Réplications (bande d'incertitude)** — `POST /api/plans/{id}/simulate` `{"replications": 5}` → 202 `{"sim_run_id", "status": "pending"}`, puis interroger `GET /api/sim-runs/{sim_run_id}` jusqu'à `status: "ready"` : `metrics_summary[indicateur] = {median, p10, p90}` et `metrics_daily[série] = {median: [...], p10: [...], p90: [...]}`.

### 6.9 Comparer deux scénarios

`GET /api/scenarios/compare?a=<id>&b=<id>` :

```json
{
  "a": {"scenario_id": "…", "name": "Zone pilote", "plan_id": "…", "summary": {"…": "…"}, "wild_dumps_daily": [0, 1, 1, "…"]},
  "b": {"scenario_id": "…", "name": "Pannes + pluie", "plan_id": "…", "summary": {"…": "…"}, "wild_dumps_daily": ["…"]},
  "delta": {
    "km_day": {"a": 489.8, "b": "…", "value": "…", "pct": "…"},
    "sim.wild_dump_t": {"a": 411.4, "b": "…", "value": "…", "pct": "…"},
    "…": "…"
  },
  "better_when_lower": ["km_day", "cost_day_fcfa", "unserved_points", "sim.wild_dump_t", "…"]
}
```

Colorer chaque delta : si la clé est dans `better_when_lower`, une baisse est verte et une hausse terre rouge ; sinon l'inverse (ex. `sim.coverage_rate`, `sim.collected_t`). `pct` vaut `null` si la valeur A est 0. `wild_dumps_daily` sert au graphique superposé.

Libellés des indicateurs : `points` Points de regroupement · `routes` Tournées · `km_day` km par jour de collecte · `cost_day_fcfa` Coût d'une journée de collecte · `unserved_points` Points non desservis · `demand_t_week` Déchets à collecter (t/semaine) · `sim.collected_t` Tonnage collecté (90 j) · `sim.wild_dump_t` Tonnage parti en dépôt sauvage · `sim.wild_dumps_active_final` Dépotoirs actifs à J+90 · `sim.wild_dumps_active_mean` Dépotoirs actifs (moyenne) · `sim.overflow_point_days` Débordements (points × jours) · `sim.cost_total_fcfa` Coût total · `sim.cost_per_t` Coût par tonne · `sim.coverage_rate` Couverture (part de la population desservie) · `sim.subscription_rate_final` Taux d'abonnement final · `sim.mean_cleanup_delay_days` Délai moyen de nettoyage (jours).

Raccourcis de scénario à proposer (boutons) : « 2 camions en panne », « Saison des pluies », « Abonnement +20 pts », « Budget −30 % » — chacun = `POST /api/scenarios` avec `parent_id` puis `PATCH` (ou `params` directement à la création).

### 6.10 Exports et journal

| Bouton | Lien (téléchargement direct) |
|---|---|
| GeoJSON | `/api/export/geojson` |
| CSV (Excel) | `/api/export/csv` |
| OSM (JOSM) | `/api/export/osm` |

Paramètres optionnels : `status` (`active`, `recurring`, `cleaned` ; défaut actifs + récidives), `since` (ISO). Aucun identifiant d'appareil ni commentaire n'est exporté.

Journal : `GET /api/audit?entity=report&limit=200` → `[{"id", "actor", "action", "entity", "entity_id", "before", "after", "at"}]`. Actions : `moderate`, `merge`, `import`, `rollback`, `cleaned`, `osm_id`, `create`, `update`, `breakdown`, `repair`, `delete`.

---

## 7. Salubri Go (PWA mobile)

### 7.1 Envoyer un signalement

`POST /api/reports` en `multipart/form-data` :

| Champ | Obligatoire | Valeur |
|---|---|---|
| `lat`, `lon` | oui | nombres (≥ 6 décimales : des coordonnées arrondies sont pénalisées par R8) |
| `photo` | conseillé | fichier image (JPEG, ≤ 12 Mo ; garder l'EXIF, redimensionner à 1 280 px max) |
| `waste_type` | non (défaut `other`) | voir §4 |
| `volume_class` | non (défaut `bag`) | voir §4 |
| `accuracy` | conseillé | précision GPS en mètres (`coords.accuracy`) |
| `comment` | non | ≤ 1 000 caractères |
| `reported_at` | conseillé | ISO 8601, **heure de la prise**, pas de l'envoi |
| `device_id` | oui en pratique | UUID généré une fois et gardé dans IndexedDB |
| `client_id` | **oui** | UUID généré à la création du signalement : rend l'envoi **idempotent** |

Réponse :

```json
{"id": "…", "status": "probable", "score": 100, "rule_hits": [], "duplicate_of": null, "already_received": false}
```

- **201** = créé ; **200** + `already_received: true` = déjà reçu avec ce `client_id` (renvoi après coupure réseau : marquer comme envoyé, pas d'erreur).
- **422** = champ invalide ou photo illisible ; **413** = photo trop lourde.
- Afficher le verdict : statut + score + règles déclenchées (`rule_hits[].detail` est déjà en français).

### 7.2 Hors ligne (outbox)

1. À l'enregistrement : stocker `{clientId, payload, photoBlob, createdAt, state: 'pending'}` dans IndexedDB (Dexie), **même avec du réseau**.
2. `syncOutbox()` : pour chaque `pending`, envoyer en multipart avec `client_id = clientId`. Succès (200/201) → `state: 'sent'` + réponse stockée. Erreur réseau ou 5xx → réessayer plus tard (backoff). 4xx → `state: 'error'` avec le message.
3. Déclencher `syncOutbox()` au démarrage, sur l'événement `online`, et via un bouton « Synchroniser ».
4. Le `client_id` garantit qu'un double envoi ne crée jamais de doublon.

### 7.3 Autour de moi et mode brigade

- `GET /api/dump-sites?bbox=…&status=active&status=recurring` → dépotoirs à moins de 2 km (calculer la bbox côté client). Tri par `priority` déjà fait par l'API.
- Mode brigade (code agent saisi dans les réglages, `LAABAL` en démo, vérifié côté client uniquement) : bouton « Nettoyé » → `POST /api/dump-sites/{id}/cleaned` en multipart (`device_id`, `photo` optionnelle) → la Feature avec `status: "cleaned"`. À mettre aussi dans l'outbox si hors ligne.
- Lien de navigation : `geo:<lat>,<lon>` ou `https://www.openstreetmap.org/?mlat=<lat>&mlon=<lon>#map=18/<lat>/<lon>`.

---

## 8. Types TypeScript (point de départ)

Pour tout générer : `npx openapi-typescript docs/openapi.json -o src/api/schema.d.ts`. Les objets GeoJSON sont typés `object` dans l'OpenAPI : utiliser les types ci-dessous.

```ts
export type WasteType = 'household' | 'plastic' | 'rubble' | 'organic' | 'medical' | 'mixed' | 'other'
export type VolumeClass = 'bag' | 'wheelbarrow' | 'cart' | 'truck' | 'more'
export type ReportStatus = 'pending' | 'probable' | 'verified' | 'to_review' | 'rejected' | 'cleaned'
export type DumpStatus = 'active' | 'recurring' | 'cleaned'
export type PlanStatus = 'pending' | 'running' | 'ready' | 'failed' | 'superseded'
export type StageCode = 'E1' | 'E2' | 'E3' | 'E4' | 'E5' | 'E6' | 'E7'

export interface RuleHit { rule: string; delta: number; detail: string; reject?: boolean }

export interface ReportProps {
  id: string; status: ReportStatus; score: number; rule_hits: RuleHit[]
  waste_type: WasteType; volume_class: VolumeClass; comment: string | null
  reported_at: string; received_at: string; gps_accuracy_m: number | null
  device_id: string | null; external_id: string | null; duplicate_of: string | null
  dump_site_id: string | null; quartier_id: string | null; import_batch_id: string | null
  photo_url: string | null; forced_status: boolean; moderated_by: string | null; moderated_at: string | null
}

export interface DumpSiteProps {
  id: string; status: DumpStatus; waste_type: WasteType; volume_est_m3: number; n_reports: number
  first_reported_at: string; last_reported_at: string; near_water: boolean; priority: number
  confidence: number; osm_id: number | null
}

export interface PointProps {
  id: string; key: string; label: string; capacity_t: number; demand_t_week: number
  fill_ratio_per_pickup: number | null; n_ilots: number; frozen: boolean; time_window: [number, number]; unserved: boolean
}

export interface RouteStop { seq: number; point_key: string; point_id: string; arrival_min: number; load_t_after: number }
export interface RouteProps {
  id: string; vehicle_id: string; vehicle_label: string; vehicle_kind: string; capacity_t: number; rotation: number
  distance_km: number; duration_min: number; load_t: number; cost_fcfa: number; stops: RouteStop[]
}

export interface StageRecord { stage: StageCode; name: string; duration_ms: number; cache_hit: boolean }
export interface PlanDiff {
  first_version: boolean; points_added: number; points_removed: number; points_moved: number; routes_changed: number
  km_delta: number; km_delta_pct: number | null; cost_delta: number; unserved_delta: number; text: string
}
export interface Plan {
  id: string; scenario_id: string; version: number; status: PlanStatus; event: string
  distance_mode: 'osrm' | 'approx'; stages: StageRecord[]; summary: Record<string, any> & { diff?: PlanDiff }
  error: string | null; created_at: string; started_at: string | null; finished_at: string | null
}

export interface Vehicle {
  id: string; label: string; kind: string; capacity_t: number; cost_per_km: number; fixed_cost_day: number
  out_of_service: boolean; shift_start: number; shift_end: number
}
export interface Scenario {
  id: string; name: string; parent_id: string | null; is_baseline: boolean; params: Record<string, any>
  vehicles: Vehicle[]; latest_ready_plan_id: string | null; latest_plan_id: string | null
  latest_plan_status: PlanStatus | null; updated_at: string
}

export interface ReportCreated {
  id: string; status: ReportStatus; score: number; rule_hits: RuleHit[]; duplicate_of: string | null; already_received: boolean
}
export interface ImportRow {
  row: number; status: 'accepted' | 'rejected'; errors: string[]; warnings: string[]; report_id: string | null
  external_id: string | null; score: number | null; report_status: ReportStatus | null; rule_hits: RuleHit[]
}
export interface ImportResult {
  batch_id: string | null; dry_run: boolean; format: 'geojson' | 'csv'; rows_total: number; accepted: number
  rejected: number; report: ImportRow[]
}
export interface Problem { type: string; title: string; status: number; detail: unknown; errors?: { loc: (string | number)[]; msg: string }[] }
```

---

## 9. Erreurs

Toutes les erreurs suivent RFC 7807 :

```json
{"type": "about:blank", "title": "Données invalides", "status": 422, "detail": "Certains champs sont invalides",
 "errors": [{"loc": ["body", "lat"], "msg": "Field required"}]}
```

| Code | Quand | Affichage conseillé |
|---|---|---|
| 404 | identifiant inconnu | « Introuvable » |
| 409 | supprimer le scénario de base, répliquer un plan non prêt | message `detail` |
| 413 | photo > 12 Mo | « Photo trop lourde » |
| 422 | données invalides, fichier d'import illisible | `detail` (déjà en français) + `errors` |
| 503 | base pas encore chargée (seed en cours) | « Le serveur démarre, réessayez dans une minute » |

`detail` est presque toujours une phrase en français affichable telle quelle. Les `msg` de validation des champs viennent de Pydantic (en anglais) : afficher plutôt un message générique par champ.

---

## 10. Scénario de démo à rendre possible (5 minutes)

Le front doit permettre ce déroulé, sans recharger la page :

1. **Go**, téléphone en mode avion : prendre une photo, choisir « Plastique », « Charrette », Enregistrer → l'outbox montre « En attente ». Remettre le réseau → « Envoyé, score 100 ».
2. **Map** : le point apparaît (rafraîchir les signalements toutes les 10 s ou au retour de focus). Depuis un autre téléphone, renvoyer **la même photo** → fiche : `R2 −70 Photo identique…`, statut « Rejeté ».
3. Filtrer « Rejetés » + « À revoir » : montrer 3 pièges du jury et leurs règles. Importer le fichier du jury par glisser-déposer (aperçu `dry_run`, puis import réel).
4. **Sim** : basculer 2 camions « en panne » (interrupteurs rouges) → barre E1–E7 : 3 étapes recalculées, 4 réutilisées, ~1 s → toast du diff → points non desservis en rouge.
5. Passer en « Saison des pluies » (picto nuage) → km ↑, bandeau si distances approximatives.
6. « Nouveau quartier » : dessiner un polygone, population 45 000 → nouveaux points, les anciens ne bougent pas.
7. **Comparer** A (base) et B (pannes + pluie) : deltas colorés et courbe des dépotoirs actifs superposée.
8. **Exporter OSM** : télécharger le `.osm`.

---

## 11. Données de démonstration disponibles

- Commune `ouagadougou`, 24 quartiers « Arrondissement N — Nord/Sud » (polygones approximatifs).
- 2 scénarios : **Zone pilote** (`is_baseline`, un quartier, plan complet sans point non desservi) et **Ville entière (démo)** (tous les quartiers : 8 camions ne suffisent pas, beaucoup de points non desservis — c'est voulu, ça montre le manque).
- 8 camions `BF-01` à `BF-08` (5 × 8 t, 3 × 12 t).
- 380 signalements de démo + 54 signalements piégés si la répétition a été lancée (`external_id` commençant par `trap-`).
- Tant que les vrais extraits OSM / Open Buildings ne sont pas dans `data/`, la ville (routes, eau, bâtiments) est **synthétique** : ne pas s'étonner que les routes forment une grille.

---

## 12. Points d'attention

- **Ne jamais afficher un plan `running`** : la carte suit `latest_ready_plan_id`.
- **Rafraîchir après `ready`** : points, tournées, résumé du plan, et `GET /api/scenarios/{id}`.
- Les recalculs `reports_changed` arrivent **2 s après** une modération ou un import (débounce) : le scénario affiché peut recevoir une nouvelle version sans action de l'utilisateur. Interroger `GET /api/scenarios/{id}` toutes les 5–10 s sur la page Scénario et ouvrir le SSE si `latest_plan_status` passe à `pending`/`running`.
- **Hors ligne dans la salle** : prévoir un fond de carte local (PMTiles servi par nginx) ou un fond uni + couches vectorielles de l'API (quartiers, routes non exposées pour l'instant : demander si besoin d'un endpoint `/api/roads`).
- Taille des réponses : `GET /api/reports` sans filtre renvoie jusqu'à 1 000 signalements ; passer `bbox` dès que la carte est zoomée.
- Les coordonnées GeoJSON sont **[lon, lat]** ; Leaflet attend `[lat, lon]`.
- `rule_hits[].detail` utilise le point décimal (`16.1 km`) : reformater si besoin.
- Accessibilité : vrais `<button>`, contraste ≥ 4,5:1 sur les tuiles colorées, cibles tactiles ≥ 44 px dans Go.

## 13. Qui contacter / quoi demander

Le backend est testé (82 tests). S'il manque un champ ou un endpoint pour un écran, demander plutôt que contourner : ajouter un champ côté API prend quelques minutes, alors qu'un calcul dupliqué dans le front risque de diverger du plan réel.

## Ajouts v0.2 — flotte et brigade Laabal

- `GET /api/scenarios/meta/vehicle-kinds` : types proposés (`truck_8t`, `truck_12t`, `tractor_4t`) avec capacité et coûts par défaut.
- `POST /api/scenarios/{id}/vehicles` `{kind, label?, capacity_t?…}` → 201 `{plan_version_id, vehicle}` (libellé auto `BF-NN`).
- `DELETE /api/scenarios/{id}/vehicles/{vid}` → `{plan_version_id}` ; le camion est **retiré** (pas effacé, l'historique des plans reste intact) ; 409 sur le dernier camion.
- `POST /api/dump-sites/{id}/laabal` : transmet un dépotoir à la brigade Laabal (police civique : contrôle et sensibilisation, **pas de ramassage**). Le nettoyage reste `POST /api/dump-sites/{id}/cleaned` (services techniques de la mairie).
- Paramètres : `laabal_capacity_t_day` est remplacé par `cleanup_capacity_t_day` (ancienne clé acceptée), plus `laabal_operations_per_week` et `laabal_deterrence`.

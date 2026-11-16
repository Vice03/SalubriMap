# Salubri — prompts pour construire le front-end

À envoyer à Opus **dans l'ordre**, un prompt à la fois, dans une conversation neuve. Joindre `docs/FRONTEND_CONTEXT.md` au premier message (prompt F0). Ne passer au prompt suivant que quand la section « Vérification » du prompt courant passe, puis commiter.

Deux personnes peuvent travailler en parallèle : l'une sur **Salubri Map + Sim** (F1 → F7, dossier `apps/web`), l'autre sur **Salubri Go** (G1 → G3, dossier `apps/go`). Chacune ouvre sa propre conversation et envoie F0 en premier.

Avant de commencer : `docker compose up --build` (ou `run/start.bat`) doit tourner. L'API répond sur `http://localhost:8000/api/docs`.

À compléter avant envoi : **[DIRECTION]** = la direction visuelle retenue (A « Terre et Carte », B « Poste de commande » ou C « Faso Danfani »).

## Vue d'ensemble : prompt → fichiers

| Prompt | Fichiers créés ou remplis |
|---|---|
| F0 | aucun (cadre) |
| F1 | `apps/web/package.json`, `vite.config.ts`, `index.html`, `tsconfig.json`, `src/main.tsx`, `src/App.tsx`, `src/router.tsx`, `src/theme/tokens.css`, `src/theme/typography.css`, `src/components/ui/{Button,Badge,Tile,Drawer}.tsx`, `public/fonts/`, `tests/setup.ts`, `tests/App.test.tsx` |
| F2 | `src/api/types.ts`, `src/api/client.ts`, `src/api/sse.ts`, `src/lib/format.ts`, `src/lib/colors.ts`, `src/components/map/WasteIcon.tsx`, `public/icons/waste/*.svg`, `tests/format.test.ts`, `tests/sse.test.ts` |
| F3 | `src/pages/MapPage.tsx`, `src/components/map/MapView.tsx`, `src/components/map/Legend.tsx`, `src/components/map/layers/*.ts`, `src/components/reports/ReportFilters.tsx`, `src/components/sim/KpiTiles.tsx`, `tests/ReportFilters.test.tsx` |
| F4 | `src/components/reports/ReportCard.tsx`, `src/components/reports/RuleHits.tsx`, `src/components/reports/ImportDialog.tsx`, `src/pages/ReportsPage.tsx`, `tests/RuleHits.test.tsx`, `tests/ImportDialog.test.tsx` |
| F5 | `src/pages/ScenarioPage.tsx`, `src/components/sim/ParamsForm.tsx`, `src/components/plan/{PointsLayer,RoutesLayer,PlanProgress,PlanDiff}.tsx`, `src/components/sim/Charts.tsx`, `tests/PlanProgress.test.tsx`, `tests/ParamsForm.test.tsx` |
| F6 | `src/pages/ComparePage.tsx`, `src/pages/AuditPage.tsx`, export dans l'en-tête, `tests/Delta.test.tsx` |
| F7 | finitions sur tous les fichiers de `apps/web`, `tests/e2e/smoke.spec.ts`, `playwright.config.ts` |
| G1 | `apps/go/package.json`, `vite.config.ts`, `index.html`, `tsconfig.json`, `public/manifest.webmanifest`, `public/icons/`, `src/main.tsx`, `src/App.tsx`, `src/theme.css`, `src/db.ts`, `src/sync.ts`, `tests/sync.test.ts`, `tests/db.test.ts` |
| G2 | `src/pages/ReportPage.tsx`, `src/pages/OutboxPage.tsx`, `src/components/{CameraInput,GpsBadge,WasteTypePicker,VolumePicker}.tsx`, `tests/ReportPage.test.tsx` |
| G3 | `src/pages/NearbyPage.tsx`, `src/pages/BrigadePage.tsx`, réglages, service worker, `docs/DEMO.md` (section hors ligne) |

Les fichiers `apps/web/Dockerfile` et `apps/go/Dockerfile` restent vides : nginx sert directement `apps/*/dist`, aucune image front n'est nécessaire.

---

## F0 — Prompt maître (à envoyer en premier, avec FRONTEND_CONTEXT.md joint)

```text
Tu es le développeur front-end principal du projet Salubri (Hackathon des Universités 2026, challenge « Assainissement de Ouaga »). Le backend existe déjà et fonctionne : NE MODIFIE RIEN dans apps/api, services/, scripts/ ni data/. Le fichier joint FRONTEND_CONTEXT.md est le contrat d'API : il fait foi pour les routes, les champs, les libellés et le comportement attendu. L'OpenAPI complète est dans docs/openapi.json et sur http://localhost:8000/api/docs.

Tu vas construire deux applications, incrément par incrément, dans le monorepo existant :
- apps/web : Salubri Map + Sim (carte des signalements, modération, import du jury, scénarios, recalcul en direct, comparaison, exports).
- apps/go : Salubri Go (PWA mobile de signalement hors ligne, mode brigade).

Stack imposée :
- React 18, TypeScript strict (pas de any), Vite 5, pnpm (workspace déjà déclaré dans pnpm-workspace.yaml).
- apps/web : TanStack Query, React Router, MapLibre GL JS, Recharts.
- apps/go : vite-plugin-pwa, Dexie (IndexedDB), Leaflet.
- Tests : Vitest + Testing Library ; un test Playwright de fumée pour apps/web.
- Pas d'appel réseau hors de l'API Salubri, sauf les tuiles OSM. Police Inter incluse localement, pas de CDN.

Conventions :
- Toute l'interface en français, sans anglicisme inutile. Code et identifiants en anglais.
- Coordonnées GeoJSON en [lon, lat] (attention à Leaflet, qui attend [lat, lon]).
- En développement, proxy Vite : /api et /photos vers http://localhost:8000. En production, nginx sert apps/web/dist à la racine et apps/go/dist sous /go/.
- La carte suit toujours latest_ready_plan_id : ne jamais afficher un plan en cours de calcul.
- Identité visuelle riche et contrastée, jamais fade : direction [DIRECTION]. Palette : vert latérite #2F6B3A, terre rouge #B7410E, orange alerte #F28C28, sable #F3E9D2, charbon #1F1D1A, blanc cassé #FBF8F2. Icônes SVG illustrées par type de déchet, tuiles KPI en couleurs pleines, états vides illustrés. Contraste du texte ≥ 4,5:1, cibles tactiles ≥ 44 px, vrais <button> et <label>.
- En-tête SPDX « SPDX-License-Identifier: AGPL-3.0-or-later » dans chaque fichier source.
- Commits en Conventional Commits anglais (feat(web): …, feat(go): …), un par étape logique.

Règles d'incrémentation (non négociables) :
1. Tu ne fais que ce que demande le prompt courant.
2. À la fin de chaque incrément, l'application doit démarrer (pnpm dev), compiler (pnpm build, sans erreur TypeScript) et ses tests doivent passer (pnpm test). Tu donnes la liste exacte des fichiers créés ou modifiés et les commandes de vérification.
3. Tu écris les tests en même temps que le code.
4. Pour un fichier long, tu donnes le fichier complet, jamais « … reste inchangé ».
5. S'il manque un champ ou une route dans l'API, tu le signales au lieu de le recalculer côté front.
6. Tu dis clairement ce que tu as vérifié en l'exécutant et ce que tu supposes.

Confirme en une phrase que tu as compris le cadre, puis attends le prompt suivant.
```

---

## F1 — Socle de apps/web

```text
Incrément F1 — Socle de Salubri Map + Sim (apps/web).

Objectif : une application React qui démarre, avec le thème, la navigation et les composants d'interface de base. Aucune donnée réelle encore.

Fichiers :
- apps/web/package.json (nom "web", scripts dev, build, preview, test, lint), tsconfig.json (strict), vite.config.ts (proxy /api et /photos vers http://localhost:8000 ; Vitest avec jsdom et tests/setup.ts), index.html (lang="fr").
- src/main.tsx (QueryClientProvider, RouterProvider), src/App.tsx (mise en page : en-tête + contenu), src/router.tsx (routes /, /signalements, /scenario, /comparer, /journal, avec des pages provisoires).
- src/theme/tokens.css (palette, rayons, ombres, espacements, couleurs des statuts : vérifié, probable, à revoir, rejeté, en attente, nettoyé), src/theme/typography.css (Inter locale dans public/fonts/, @font-face).
- src/components/ui/Button.tsx (variantes primaire, secondaire, danger, fantôme ; tailles ; état chargement), Badge.tsx (couleur par statut), Tile.tsx (tuile KPI : grande valeur, libellé, icône, couleur pleine), Drawer.tsx (tiroir latéral droit accessible : focus piégé, Échap pour fermer).
- En-tête : logo SVG Salubri (épingle de carte verte avec une boucle de tournée), onglets Carte / Signalements / Scénario / Comparer / Journal, emplacement à droite pour les boutons Importer et Exporter (désactivés pour l'instant).
- tests/setup.ts, tests/App.test.tsx (l'en-tête et les 5 onglets s'affichent).

Critères : rendu conforme à la direction [DIRECTION] ; navigation au clavier ; aucune chaîne anglaise visible.

Vérification :
  pnpm install
  pnpm --filter web test
  pnpm --filter web build
  pnpm --filter web dev   # ouvrir http://localhost:5173
  git add -A && git commit -m "feat(web): F1 app shell, theme tokens and base UI components"
```

---

## F2 — Couche d'accès à l'API

```text
Incrément F2 — Client d'API typé, SSE, formatage et icônes (apps/web).

Objectif : tout l'accès à l'API passe par une couche typée et testée, conforme à FRONTEND_CONTEXT.md.

Fichiers :
- src/api/types.ts : reprendre les types de la section 8 du contexte (WasteType, ReportStatus, ReportProps, DumpSiteProps, PointProps, RouteProps, Plan, Scenario, ImportResult, Problem…) et les FeatureCollection typées.
- src/api/client.ts : fetch typé avec gestion des erreurs RFC 7807 (classe ApiError avec title, status, detail, errors) ; une fonction par route utilisée : health, getCommune, getQuartiers, createQuartier, deleteQuartier, getReports(filtres), getReportStats, getReport, patchReport, revalidateReport, mergeReport, importFile(file, dryRun), rollbackImport, listImports, getDumpSites, getScenarios, getScenario, getParamsSchema, patchScenario, createScenario, deleteScenario, breakdown, recompute, getPlan(daily?), getPlanPoints, getPlanRoutes, getPlanUnserved, getPlanDiff, simulatePlan, getSimRun, compareScenarios, getAudit, getValidationRules, exportUrl(format). Les filtres répétables sont envoyés en clés répétées (status=a&status=b).
- Des hooks TanStack Query pour les lectures (useReports, useScenario, usePlanPoints…), avec des clés de cache cohérentes.
- src/api/sse.ts : followPlan(planId, handlers) basé sur EventSource, événements running, stage_started, stage_done, ready, failed, superseded (suivre automatiquement la nouvelle version sur superseded) ; repli par interrogation de GET /api/plans/{id} toutes les 300 ms si EventSource échoue ; retourne une fonction d'annulation.
- src/lib/format.ts : nombres à la française (espaces fines, virgule), FCFA, tonnes, km, pourcentages signés, minutes après minuit vers « 07 h 10 », dates locales relatives (« il y a 3 h »).
- src/lib/colors.ts : couleur par statut, par type de déchet, 8 couleurs contrastées pour les camions.
- src/components/map/WasteIcon.tsx + public/icons/waste/{household,plastic,rubble,organic,medical,mixed,other}.svg : 7 icônes illustrées, lisibles à 20 px, cohérentes avec la palette.
- Tests : tests/format.test.ts, tests/sse.test.ts (EventSource simulé : enchaînement des étapes, ready, superseded suivi, repli par interrogation), tests/client.test.ts (une erreur 422 donne une ApiError avec detail).

Vérification :
  pnpm --filter web test && pnpm --filter web build
  # avec le backend lancé, dans la console du navigateur (pnpm dev) : les appels health et getScenarios répondent
  git add -A && git commit -m "feat(web): F2 typed API client, SSE follower, formatters and waste icons"
```

---

## F3 — Carte principale

```text
Incrément F3 — Carte Salubri Map, filtres et tuiles de compteurs (apps/web).

Objectif : la page Carte affiche toute la ville de démo avec ses couches, filtrable, et les compteurs du tableau de bord.

Fichiers :
- src/components/map/MapView.tsx : MapLibre GL, style raster OSM (tile.openstreetmap.org, attribution « © contributeurs OpenStreetMap »), centrage sur GET /api/communes/ouagadougou (center, bbox), contrôles de zoom et d'échelle.
- src/components/map/layers/*.ts : une couche par type de données :
  quartiers (contour vert latérite, nom au survol) ; signalements (icône du type, halo de la couleur du statut, taille selon volume_class) ; dépotoirs (cercle terre rouge, rayon ∝ volume_est_m3, anneau orange si near_water) ; dépôt des camions (pictogramme).
- src/components/map/Legend.tsx : légende illustrée repliable (statuts, types, dépotoirs, points, tournées).
- src/components/reports/ReportFilters.tsx : barre latérale : statuts (puces colorées), types (puces avec icônes), quartier, période, score minimum, règle déclenchée (liste issue de GET /api/validation/rules). Les filtres vivent dans l'URL (partageables) et pilotent GET /api/reports ; la bbox de la carte est envoyée quand le zoom ≥ 14.
- src/components/sim/KpiTiles.tsx : tuiles en haut de page depuis GET /api/reports/stats (total, vérifiés, à revoir, rejetés, dépotoirs actifs), rafraîchies toutes les 10 s.
- src/pages/MapPage.tsx : assemble carte, filtres, tuiles ; cliquer un signalement ouvre le tiroir (contenu provisoire : identifiant et statut).
- Tests : tests/ReportFilters.test.tsx (sérialisation des filtres dans l'URL, clés répétées).

Critères : les 434 signalements de démo (avec pièges) et les 123 dépotoirs s'affichent ; filtrer « Rejeté » ne montre que les rejetés ; aucun texte anglais.

Vérification :
  pnpm --filter web test && pnpm --filter web build
  pnpm --filter web dev   # carte, filtres, tuiles avec les données réelles
  git add -A && git commit -m "feat(web): F3 map page with layers, URL filters and KPI tiles"
```

---

## F4 — Fiche, modération et import du jury

```text
Incrément F4 — Fiche d'un signalement, modération et import par glisser-déposer (apps/web).

Fichiers :
- src/components/reports/RuleHits.tsx : liste des règles déclenchées (badge du code, pénalité colorée, détail en français), état vide « Aucune règle déclenchée ».
- src/components/reports/ReportCard.tsx (dans le Drawer) : photo (photo_url), mini-carte, jauge du score 0–100 colorée selon le statut, type et volume avec icônes, date relative, précision GPS, appareil, RuleHits, signalements liés cliquables (related), dépotoir rattaché, actions Vérifier / Rejeter / Remettre à revoir / Fusionner (saisie de l'identifiant cible) / Rejouer les règles, avec confirmation et toast. Après chaque action : invalider les requêtes signalements, stats et dépotoirs.
- src/components/reports/ImportDialog.tsx : zone de glisser-déposer (.geojson, .json, .csv, .zip) → envoi avec dry_run=true → tableau ligne par ligne (ligne, lue ou rejetée, erreurs, avertissements, verdict des règles, score) avec compteurs → bouton « Importer pour de vrai » → bouton « Annuler l'import » (rollback). Distinguer clairement « ligne illisible » (status rejected) et « piège détecté » (report_status rejected).
- src/pages/ReportsPage.tsx : tableau paginé des signalements (mêmes filtres que la carte), tri par date ou score, clic qui ouvre la fiche.
- Brancher le bouton Importer de l'en-tête sur ImportDialog.
- Tests : tests/RuleHits.test.tsx (3 règles rendues avec leur pénalité), tests/ImportDialog.test.tsx (rapport affiché à partir d'une réponse simulée, bouton d'annulation présent après import).

Critères : importer data/jury/exemple_import.csv donne 10 lignes dont 2 rejetées avec leurs messages ; le filtre « règle R2 » puis le clic sur un point montre « R2 −70 » dans la fiche.

Vérification :
  pnpm --filter web test && pnpm --filter web build
  pnpm --filter web dev   # importer data/jury/exemple_import.csv en aperçu puis pour de vrai, puis annuler
  git add -A && git commit -m "feat(web): F4 report card with rule hits, moderation actions and jury import dialog"
```

---

## F5 — Scénario et recalcul en direct

```text
Incrément F5 — Page Scénario : paramètres, flotte, nouveau quartier, recalcul en direct, plan et simulation (apps/web).

C'est l'écran de l'épreuve du jury : il doit être impeccable.

Fichiers :
- src/components/sim/ParamsForm.tsx : formulaire généré depuis GET /api/scenarios/params-schema (label, bornes, enum). Groupes : Population et abonnements ; Pré-collecte ; Points et enlèvement ; Budget ; Saison (deux grosses cases illustrées soleil / nuage) ; onglet Avancé (seed, vrp_time_limit_s, ilot_size_buildings, horizon_days). Envoi d'un PATCH par modification validée (pas à chaque frappe).
- Flotte : tableau des camions avec interrupteur « En panne » rouge ; plusieurs camions cochés = un seul PATCH vehicles.
- Nouveau quartier : outil de dessin de polygone sur la carte (clics, double-clic pour fermer), saisie du nom et de la population, POST /api/quartiers avec scenario_id.
- src/components/plan/PlanProgress.tsx : les 7 étapes E1–E7 affichées dès le lancement ; en cours (animation), recalculée (couleur + durée), réutilisée (gris « réutilisé ») ; durée totale ; branché sur followPlan. En cas d'échec : bandeau rouge, l'ancien plan reste affiché.
- src/components/plan/PlanDiff.tsx : toast puis encart avec summary.diff.text et les chiffres (points ajoutés, déplacés, tournées refaites, Δ km, Δ coût, Δ non desservis).
- src/components/plan/PointsLayer.tsx : losanges orange (étiquette clé + remplissage fill_ratio_per_pickup), rouge si unserved, liseré si frozen. RoutesLayer.tsx : une couleur par camion, panneau « Tournées » (camion, rotation, km, charge/capacité, horaires des arrêts formatés).
- Bandeau orange « Distances approximatives (OSRM indisponible) » quand distance_mode = approx.
- src/components/sim/Charts.tsx (Recharts) : aires empilées des flux par jour (collecté, pré-collecté, dépôt sauvage), courbe des dépotoirs actifs, barres des km par camion ; bouton « 5 réplications » qui affiche la bande p10–p90 (POST simulate puis GET sim-runs).
- src/pages/ScenarioPage.tsx : sélecteur de scénario, carte (points, tournées), ParamsForm, flotte, PlanProgress, PlanDiff, KPI de simulation (summary.sim), Charts. La carte ne bascule sur le nouveau plan qu'à l'événement ready. Interroger le scénario toutes les 5 s pour détecter un recalcul déclenché ailleurs (latest_plan_status).
- Tests : tests/PlanProgress.test.tsx (séquence SSE simulée : 3 recalculées, 4 réutilisées, ready), tests/ParamsForm.test.tsx (formulaire généré depuis un schéma simulé, PATCH envoyé avec la bonne clé).

Critères (avec le backend lancé) : deux camions en panne → E5, E6, E7 recalculées, E1–E4 réutilisées, en environ 1 s, toast du diff ; saison des pluies → bandeau et km modifiés ; nouveau quartier dessiné → nouveaux points, les anciens ne bougent pas.

Vérification :
  pnpm --filter web test && pnpm --filter web build
  pnpm --filter web dev   # rejouer les 3 critères ci-dessus
  git add -A && git commit -m "feat(web): F5 scenario page with live recompute progress, fleet, new quartier, plan layers and charts"
```

---

## F6 — Comparaison, journal et exports

```text
Incrément F6 — Comparaison A/B, journal d'audit et exports (apps/web).

Fichiers :
- src/pages/ComparePage.tsx : sélecteurs A et B ; bouton « Créer B à partir de A » ; raccourcis « 2 camions en panne », « Saison des pluies », « Abonnement +20 pts », « Budget −30 % » (POST /api/scenarios avec parent_id puis PATCH, avec suivi SSE) ; deux cartes MapLibre synchronisées (même centre et zoom) ; tableau des indicateurs avec les libellés de la section 6.9 du contexte : colonne A, colonne B, delta coloré selon better_when_lower (vert si amélioration, terre rouge sinon) avec flèche ; graphique superposé des dépotoirs actifs (wild_dumps_daily).
- src/pages/AuditPage.tsx : journal (GET /api/audit) avec filtre par entité, actions traduites en français, avant/après lisibles.
- Menu Exporter de l'en-tête : GeoJSON, CSV, OSM (liens de téléchargement directs).
- Tests : tests/Delta.test.tsx (signe et couleur selon le sens de l'indicateur, pct null géré).

Vérification :
  pnpm --filter web test && pnpm --filter web build
  pnpm --filter web dev   # créer B « 2 camions en panne » et comparer ; télécharger l'export OSM
  git add -A && git commit -m "feat(web): F6 scenario comparison, audit log and export menu"
```

---

## F7 — Finitions et test de bout en bout

```text
Incrément F7 — Finitions visuelles, accessibilité, build servi par nginx, test Playwright (apps/web).

- Passer sur toutes les pages : états de chargement (squelettes), états vides illustrés (SVG), messages d'erreur en français à partir des ApiError (503 : « Le serveur démarre, réessayez dans une minute »), toasts cohérents, responsive jusqu'à 1 280 px et utilisable sur tablette.
- Accessibilité : contraste ≥ 4,5:1 vérifié sur les tuiles colorées, focus visible, aria-label sur les boutons-icônes.
- Fond de carte hors ligne : si les tuiles OSM ne chargent pas, basculer sur un fond uni sable avec les couches vectorielles (quartiers, dépotoirs, points, tournées) et afficher un bandeau discret.
- Build de production : pnpm --filter web build produit apps/web/dist ; vérifier qu'il est servi par nginx sur http://localhost (docker compose up), routes profondes comprises.
- playwright.config.ts et tests/e2e/smoke.spec.ts : ouvrir /, filtrer « Rejeté », ouvrir une fiche et y trouver un code de règle, aller sur Scénario, mettre un camion en panne, attendre le toast du diff.

Vérification :
  pnpm --filter web test && pnpm --filter web build
  docker compose up -d && npx playwright test -c apps/web/playwright.config.ts
  git add -A && git commit -m "feat(web): F7 polish, accessibility, offline basemap fallback and e2e smoke test"
```

---

## G1 — Socle de Salubri Go et file d'envoi

```text
Incrément G1 — Socle de Salubri Go (apps/go) : PWA installable, base locale et synchronisation. Ne touche pas à apps/web.

Fichiers :
- apps/go/package.json (nom "go"), tsconfig.json, vite.config.ts (base '/go/', proxy /api et /photos vers http://localhost:8000, vite-plugin-pwa : registerType autoUpdate, précache de l'application, manifest en français), index.html (lang="fr", viewport mobile).
- public/manifest.webmanifest (nom « Salubri Go », couleurs de la palette), public/icons/ (icônes 192 et 512 px dérivées du logo).
- src/theme.css (mêmes jetons que apps/web, mobile d'abord, cibles ≥ 44 px), src/main.tsx, src/App.tsx (barre d'onglets en bas : Signaler, Envois, Autour de moi, et Brigade si le code agent est saisi).
- src/db.ts (Dexie) : table outbox {clientId (uuid), kind ('report' | 'cleaned'), payload, photoBlob, createdAt, state ('pending' | 'sent' | 'error'), attempts, serverResponse, error}, table settings (deviceId généré une fois, agentCode).
- src/sync.ts : syncOutbox() selon la section 7.2 du contexte : envoi multipart avec client_id, 200/201 → sent (réponse stockée, already_received géré), réseau ou 5xx → nouvel essai avec délai croissant, 4xx → error avec le message. Déclenchement au démarrage, sur l'événement online, et à la demande. Un seul envoi à la fois (verrou).
- Tests : tests/db.test.ts (fake-indexeddb), tests/sync.test.ts (fetch simulé : échec puis succès → pending puis sent ; même clientId renvoyé deux fois → un seul enregistrement « sent » ; 422 → error).

Vérification :
  pnpm --filter go test && pnpm --filter go build
  pnpm --filter go dev   # http://localhost:5174/go/ : les onglets s'affichent
  git add -A && git commit -m "feat(go): G1 installable PWA shell with Dexie outbox and idempotent sync"
```

---

## G2 — Signaler et suivre ses envois

```text
Incrément G2 — Écrans Signaler et Envois (apps/go).

Fichiers :
- src/components/CameraInput.tsx : input capture="environment", aperçu, redimensionnement à 1 280 px max côté client (JPEG qualité 0,8) en conservant l'EXIF si possible, bouton « Reprendre ».
- src/components/GpsBadge.tsx : position (watchPosition, haute précision), précision affichée et colorée (vert ≤ 20 m, orange ≤ 100 m, rouge au-delà), bouton « Relocaliser », option « Placer sur la carte » si pas de GPS.
- src/components/WasteTypePicker.tsx : grille de 7 grosses tuiles illustrées (mêmes icônes que le web). src/components/VolumePicker.tsx : 5 choix illustrés (Sac, Brouette, Charrette, Camion, Plus).
- src/pages/ReportPage.tsx : photo, GPS, type, volume, commentaire, bouton « Enregistrer » toujours actif (même hors ligne) → écrit dans l'outbox avec client_id, reported_at (heure de la prise), accuracy, device_id, puis lance syncOutbox().
- src/pages/OutboxPage.tsx : liste des envois : en attente (orange), envoyé (vert, score et statut), rejeté par les règles (terre rouge, rule_hits[].detail en français), erreur (message, bouton Réessayer) ; bouton « Synchroniser » ; badge réseau en ligne / hors ligne.
- Tests : tests/ReportPage.test.tsx (enregistrement hors ligne → une entrée pending dans l'outbox avec un client_id).

Critère : en mode avion, un signalement reste « En attente » ; au retour du réseau il passe « Envoyé » avec son score, et apparaît dans GET /api/reports.

Vérification :
  pnpm --filter go test && pnpm --filter go build
  pnpm --filter go dev   # tester avec l'onglet Réseau du navigateur en mode « Hors ligne »
  git add -A && git commit -m "feat(go): G2 offline report capture and outbox screen"
```

---

## G3 — Autour de moi, brigade Laabal et PWA réelle

```text
Incrément G3 — Autour de moi, mode brigade et test sur téléphone (apps/go).

Fichiers :
- src/pages/NearbyPage.tsx : Leaflet (attention, Leaflet attend [lat, lon]), tuiles OSM mises en cache par le service worker (cache d'exécution, 500 tuiles max), dépotoirs actifs et récidives à moins de 2 km (bbox calculée côté client), fiche courte au toucher, lien de navigation geo:.
- Réglages : saisie du code agent (LAABAL en démo, vérifié côté client), affichage du device_id.
- src/pages/BrigadePage.tsx : dépotoirs triés par priorité, bouton « Nettoyé » avec photo facultative → entrée kind='cleaned' dans l'outbox → POST /api/dump-sites/{id}/cleaned en multipart (device_id, photo).
- Build de production : pnpm --filter go build produit apps/go/dist, servi par nginx sur http://localhost/go/.
- docs/DEMO.md : compléter la section « Test du mode hors ligne » avec la procédure exacte sur téléphone (même Wi-Fi, http://<ip-du-pc>/go/, installation, mode avion).

Critères : la PWA s'installe sur un téléphone Android (Lighthouse : installable) ; le parcours mode avion → retour réseau fonctionne ; marquer un dépotoir nettoyé le fait passer en « Nettoyé » dans Salubri Map.

Vérification :
  pnpm --filter go test && pnpm --filter go build
  docker compose up -d   # puis sur le téléphone : http://<ip-du-pc>/go/
  git add -A && git commit -m "feat(go): G3 nearby dumps map, Laabal brigade mode and production PWA"
```

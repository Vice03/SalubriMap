<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Modules optionnels

Deux modules s'ajoutent à Salubri sans rien changer quand ils sont éteints, ce qui est leur état par défaut. Ils
sont **hors des livrables exigés par la fiche du défi** : la démonstration et le rapport fonctionnent sans eux.

| Module | Réglage (`.env`) | Dossier | Ce qu'il fait |
|---|---|---|---|
| Saisons | `SALUBRI_SEASONS_ENABLED=true` | `apps/api/salubri_api/modules/seasons/` (+ `apps/web/src/modules/seasons/`, `apps/go/src/modules/seasons/`) | points de regroupement et tournées qui suivent l'état des routes selon la saison |
| Assistant | `SALUBRI_ASSISTANT_ENABLED=true` | `apps/api/salubri_api/modules/assistant/` (+ `apps/web/src/modules/assistant/`, `run/llm_detect.py`) | un modèle de langue local explique plans, simulations et signalements, en lecture seule |

## Ce que garantit « éteint »

- Aucune route `/api/roads/…` ni `/api/assistant/…` ; `/api/health` → `modules` dit ce qui est allumé et les
  interfaces cachent le reste ; la pile par défaut ne lance pas de modèle de langue.
- Le code existant n'appelle un module qu'à une ligne par endroit, derrière `settings.seasons_enabled` ou
  `settings.assistant_enabled`.
- **Vérifié** : `scripts/baseline.py` recalcule tous les scénarios d'une copie de la même base avec des solveurs
  reproductibles (`SALUBRI_DETERMINISTIC_SOLVERS=true`) et compare les plans (résumé sans durées, positions des
  points, tournées). Modules éteints : **identique** à la référence. « Saisons » allumé avec une table vide : plans
  identiques, seule la section vide `summary.saisons` s'ajoute. La suite de tests, la répétition et les tests
  navigateur passent dans les deux états.
- Les tables des modules (migrations `0101_seasons`, `0201_assistant`, chacune sur sa branche Alembic) sont créées
  par `alembic upgrade heads` ; vides, elles ne changent rien.

## Saisons

Détails, approximations et retrait : [`modules/seasons/README.md`](../apps/api/salubri_api/modules/seasons/README.md)
et `docs/HYPOTHESES.md` (section « Module Saisons »).

1. `.env` : `SALUBRI_SEASONS_ENABLED=true`, puis `run/start`.
2. Calendrier de la commune (facultatif) : `data/communes/<commune>/saisons.json`.
3. Salubri Map → Carte → panneau « Routes » : importer les routes coupées connues (CSV ou GeoJSON : `osm_id` ou
   `lat`/`lon`, `saison`, `praticable`), ou cliquer une route pour la couper ; Salubri Go → onglet « Route »
   pour les habitants et les agents (vérifié par un modérateur avant de compter).

Vérifié : 9 tests d’API (table vide = rien ne change, import et annulation, signalement Go → modération → état,
saisie du modérateur, réseau de marche, pénalité des tournées, déplacement en pluie et retour exact en saison
sèche, calendrier) ; répétition « Inondation secteur 12 » verte deux fois de suite ; 2 tests navigateur.
Non vérifié : sur de vraies routes coupées (aucune donnée de terrain) ; facteur de vitesse d'une route ralentie
enregistré mais pas appliqué aux temps de trajet.

## Assistant

Détails et retrait : [`modules/assistant/README.md`](../apps/api/salubri_api/modules/assistant/README.md).

1. `.env` : `SALUBRI_ASSISTANT_ENABLED=true`, puis `run/start` (Windows : `start.bat`). `run/llm_detect.py`
   utilise le modèle local déjà installé s'il y en a un, sinon propose d'en télécharger un (voir ci-dessous).
2. `run/doctor` affiche le moteur détecté, le modèle, le palier de la machine et si l'assistant répond.
3. Salubri Map, connecté en modérateur ou admin : bouton « Assistant ».

Moteurs reconnus (API compatible OpenAI) : Ollama (11434), LM Studio (1234), llama.cpp server (8080, 8081),
Jan (1337), LocalAI (8080), vLLM (8000, sauf si c'est l'API de Salubri). Modèles retenus : familles Qwen 2.5/3,
Llama 3.x, Mistral, version « instruct », la plus grosse que la machine peut faire tourner.

### Paliers quand aucun modèle n'est installé

Étiquettes et tailles relevées sur le registre Ollama le 17 novembre 2026 ; téléchargement dans le conteneur
Ollama du profil Docker `assistant` (volume nommé, rien installé sur la machine), seulement après accord.

| Machine | Modèle | Taille | Licence |
|---|---|---|---|
| < 8 Go de mémoire, sans GPU | aucun : assistant désactivé, rien n'est téléchargé | — | — |
| 8–15 Go, sans GPU | `qwen2.5:1.5b-instruct` (4 bits) | ~1 Go | Apache-2.0 |
| ≥ 16 Go, ou GPU de 6 à 10 Go | `qwen2.5:7b-instruct` (4 bits) | ~4,7 Go | Apache-2.0 |
| ≥ 32 Go, ou GPU ≥ 12 Go | `qwen2.5:14b-instruct` (4 bits) | ~9 Go | Apache-2.0 |

Le palier modeste aurait pu être Qwen2.5 3B, mais sa licence (recherche Qwen) interdit l'usage commercial : le
1,5B (Apache-2.0) est proposé à la place.

Jamais de téléchargement : sans terminal (CI, tâche planifiée), en démonstration tant que
`SALUBRI_LLM_DURING_DEMO` vaut `off` (défaut), pendant `make verify`, la répétition ou les tests ;
`run/start --llm=no` l'interdit, `--llm=yes` l'accepte sans question. Disque insuffisant ou échec : Salubri
démarre sans l'assistant et le dit en une ligne.

Vérifié : 25 tests (modèle simulé en CI : droits, aucune écriture possible, injection dans un commentaire de
signalement, journal, indisponibilité, citation dans chaque réponse, limite de débit, recherche BM25, chaque outil,
client sur un faux serveur ; détection sur de faux serveurs, paliers, accord, « ni modèle ni disque ») ; test
navigateur du bouton. **Non vérifié** : la qualité des réponses d'un vrai modèle (aucun modèle local là où le
module a été développé) ; `start.bat` vérifié par lecture seulement. À lancer sur le PC de démonstration :

```bash
SALUBRI_ADMIN_TOKEN=<code mairie> python scripts/eval_assistant.py --api http://localhost --sortie docs/assistant_eval.json
```

## Réutiliser un module ailleurs

- **Autre commune** : rien de propre à Ouagadougou dans le code ; données dans `data/communes/<commune>/`
  (calendrier des saisons, schéma des paramètres lu par l'assistant).
- **Autre projet FastAPI** : chaque module liste ses seules dépendances envers Salubri dans son `interface.py`.
  Fournir ces noms, monter ses routes, appeler ses fonctions aux endroits équivalents (voir son README).

## Retirer un module

Éteindre le réglage suffit. Pour supprimer le code : suivre le README du module (descendre sa branche de
migration, supprimer ses dossiers et les lignes marquées « module … »).

<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Module « Assistant » — un modèle local explique plans et simulations (lecture seule)

**Optionnel, éteint par défaut.** Éteint : aucune route, aucun panneau, la pile démarre sans modèle. Allumé sans
modèle joignable : il répond « assistant indisponible » et rien d'autre n'est touché.

## Ce qu'il fait

- `POST /api/assistant/ask` (modérateurs et administrateurs) : question en français, réponse diffusée par
  morceaux (NDJSON : outils utilisés, texte, puis sources et proposition éventuelle). `GET /api/assistant/status`.
- Client unique compatible avec l'API de chat d'OpenAI (`llm.py`), que proposent Ollama, LM Studio, llama.cpp
  server, Jan, LocalAI et vLLM : pas de chemin propre à Ollama, rien ne manquait à l'API compatible.
- Outils en lecture seule, liste fermée (`tools.py`) : résumé d'un plan, détail d'un point, ce qui a changé entre
  deux versions, un signalement avec ses règles et son masquage, dépotoirs d'un quartier, paramètres avec leur
  source, résultats simulés avec intervalles et classement de sensibilité, tableaux du plan d'arrondissement,
  points déplacés par saison (si le module « Saisons » est allumé). **Aucun outil n'écrit** ; une simulation
  « et si… » revient comme une proposition que l'agent applique d'un clic (« Appliquer cette simulation »), par
  l'API normale. L'assistant ne juge jamais un signalement.
- Ancrage : passages des documents (`retrieval.py`, BM25, table `assistant_passages` reconstruite au démarrage),
  chaque réponse cite l'outil ou la section ; sans citation du modèle, les sources consultées sont ajoutées.
- Sécurité : sorties d'outils et passages balisés `<donnees>` (chevrons neutralisés) et traités comme des données ;
  6 questions par minute et par utilisateur, réponse de 3 000 caractères au plus, délai du modèle borné
  (`SALUBRI_LLM_TIMEOUT_S`) ; chaque question, appel d'outil et réponse dans le journal, avec l'utilisateur.
- Interface : bouton « Assistant » dans Salubri Map pour les comptes connectés (modérateur, admin), questions
  suggérées, sources sous chaque réponse.

## L'allumer

1. `.env` : `SALUBRI_ASSISTANT_ENABLED=true`.
2. `run/start` (`start.bat` sous Windows) : `run/llm_detect.py` cherche un modèle déjà installé (Ollama,
   LM Studio, llama.cpp, Jan, LocalAI, vLLM) ; sinon il propose, avec accord, le modèle du palier de la machine
   dans le conteneur Ollama du profil `assistant` (tableau des paliers : `docs/MODULES.md`).
   `run/start --llm=no` : jamais de téléchargement ; `--llm=yes` : sans question.
3. Évaluer : `EVALUATION.md` (30 questions).

## Le retirer

Éteindre le réglage suffit. Pour supprimer le code : `alembic downgrade 0006` sur la branche `assistant` (ou
`DROP TABLE assistant_passages` puis `alembic stamp`), supprimer ce dossier, `apps/web/src/modules/assistant/`,
`run/llm_detect.py`, le service `ollama` de `docker-compose.yml` et les lignes marquées « module Assistant ».

## Le copier dans un autre projet FastAPI

Dépendances envers Salubri : `interface.py` (réglages, base SQLAlchemy, session, rôle de l'appelant, journal,
dossier des documents, modèles lus par les outils). Remplacer `tools.py` par les lectures du projet, garder
`llm.py`, `retrieval.py`, `service.py` et `prompt.md`.

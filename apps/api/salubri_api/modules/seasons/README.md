<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Module « Saisons » — points et tournées qui suivent l'état des routes

**Optionnel, éteint par défaut.** Éteint, ou allumé avec une table `road_conditions` vide, il ne change rien
(test `test_flag_on_with_empty_table_changes_nothing`, contrôle `scripts/baseline.py`).

## Ce qu'il fait

- Table `road_conditions` : route (table `roads`), période (`dry`, `rain` ou une phase du calendrier
  `data/communes/<commune>/saisons.json`), praticable, facteur de vitesse, source (`import`, `report`, `manual`),
  confiance, date, note. Remplie par un import CSV/GeoJSON (identifiant OSM ou route la plus proche à moins de
  15 m, rapport ligne par ligne, annulation), par le signalement « Route impraticable » de Salubri Go une fois
  vérifié par un modérateur, ou par un modérateur sur la carte.
- Placement : une paire îlot-site qui traverse une route impraticable est interdite, un site sur la route n'est
  pas utilisable.
- Changement de saison : un point dont la route d'accès devient impraticable est déplacé (même clé) vers le site
  praticable le plus proche qui garde à portée tous ses ménages ; sinon il reste, signalé « inaccessible en saison
  des pluies » avec les ménages touchés, et n'est plus desservi. Retour en saison sèche : positions d'origine.
- Tournées : un arc qui traverse une route impraticable coûte 50 km de plus ; un point inaccessible est abandonné.
- Simulation : les ménages d'un point inaccessible vont au point accessible le plus proche, ou jettent selon la
  règle de choix existante (aucun nouveau paramètre).
- Résumé du plan `summary.saisons`, section « Saison des pluies » du plan d'arrondissement, couche « Routes » et
  panneau « points déplacés » dans Salubri Map, onglet « Route » dans Salubri Go, scénario de répétition
  « Inondation secteur 12 ».

Approximations et limites : `docs/HYPOTHESES.md`, section « Module Saisons ».

## L'allumer (dans cette commune ou une autre)

1. `SALUBRI_SEASONS_ENABLED=true` dans `.env`, puis redémarrer l'API (la migration `0101_seasons` passe au
   démarrage du seed : `alembic upgrade heads`).
2. Optionnel : `data/communes/<commune>/saisons.json` (périodes et mois) ; sans fichier : saison sèche et pluies.
3. Importer les routes coupées connues (Salubri Map → Carte → panneau « Routes »), ou les saisir sur la carte.

## Le retirer

Éteindre le réglage suffit. Pour supprimer le code : `alembic downgrade 0006` sur la branche (ou
`alembic stamp 0006` après `DROP TABLE road_reports, road_conditions, road_import_batches`), puis supprimer
`apps/api/salubri_api/modules/seasons/`, `apps/web/src/modules/seasons/`, `apps/go/src/modules/seasons/` et les
lignes marquées « module « Saisons » » (une par endroit, toutes derrière `settings.seasons_enabled`).

## Le copier dans un autre projet FastAPI

Ses seules dépendances envers Salubri sont listées dans `interface.py` (base SQLAlchemy, tables `roads`,
`reports`, `communes`, dépendances d'authentification, journal, création d'un signalement). Fournir ces noms,
monter `router` et `public`, appeler `service.load_context` / `seasonal_variant` / `penalise_matrix` /
`adjust_snapshot` aux endroits équivalents du calcul de plan.

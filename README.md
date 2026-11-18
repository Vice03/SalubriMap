# Salubri

**Signaler, vérifier, planifier, simuler : l'assainissement de Ouagadougou en logiciel libre.**

Salubri est un outil libre d'aide à la décision, du signalement des dépotoirs sauvages jusqu'au plan de gestion de la ville, avec simulation de tous les acteurs (ménages, pré-collecteurs, brigade Laabal, mairie). Projet du Hackathon des Universités 2026, challenge « Assainissement de Ouaga ».

| Module | Rôle |
|---|---|
| **Salubri Go** | Application mobile (PWA hors ligne) de signalement : photo, GPS, type de déchet, volume |
| **Salubri Map** | Carte des signalements, 12 règles anti-pièges et score de confiance, modération, import du jeu du jury, export OpenStreetMap |
| **Salubri Sim** | Points de regroupement, tournées optimisées des camions, simulation multi-agents sur 90 jours, comparaison de scénarios, recalcul en direct |

## Démarrage

1. Installer [Docker](https://docs.docker.com/get-docker/) et le démarrer.
2. Windows : double-cliquer **`SALUBRI.bat`** à la racine (menu : version démo, version complète, ouverture des applis, diagnostic, répétition, tests, remise à zéro, arrêt ; guide illustré : [`docs/GUIDE_JURY.pdf`](docs/GUIDE_JURY.pdf)), ou `run\start.bat`. Linux/macOS : `./run/start.sh` (ou `docker compose up --build`).
   - Démo (choix 1) : signalements simulés à partir du SDGD 2020. Complète (choix 2) : données de référence seules, aucun signalement fictif.
   - Purger à la demande (garde la référence) : choix **P** du menu, ou `python -m salubri_api.purge signalements` (taper PURGER, ou `--oui`).
3. Ouvrir **http://localhost** (Salubri Map) et **http://localhost/go/** (Salubri Go, téléphone).
4. Se connecter en haut à droite : `demo` / `ouaga2026` (mode démonstration).
5. En cas de souci : `run/doctor` dit ce qui manque (Docker, ports, disque) et quelle carte sera utilisée.

Premier démarrage : construction des images puis chargement de la ville (le job CI « stack » chronomètre un clone neuf et l'affiche dans son résumé). Ensuite, aucun accès Internet n'est nécessaire.

| Commande | Effet |
|---|---|
| `run/stop` | arrêter (données conservées) |
| `run/reset` | effacer la base et repartir de zéro |
| `run/doctor` | diagnostic : Docker, ports 80/8443, disque, carte (vraies rues ou ville synthétique) |
| `run/test` | lancer les tests |
| `run/rehearse` | rejouer l'épreuve du jury (pièges + changements de paramètres) |
| `make bench` | mesurer les temps de recalcul |

Sécurité (comptes, rôles, mise en production) : [docs/SECURITY.md](docs/SECURITY.md). Bilan de la version 0.3 : [docs/RAPPORT_0.3.md](docs/RAPPORT_0.3.md).

## Épreuve en direct : comment la rejouer

```bash
make rehearse        # ou run/rehearse.bat
```

Le script importe 54 signalements piégés (doublons, photos réutilisées, faux GPS, points dans un bâtiment ou dans l'eau, rafales…), vérifie le verdict de chacun, puis applique sur un clone du scénario de base : 2 camions en panne, saison des pluies, nouveau quartier, budget −30 %, réparation, retour en saison sèche, deux modifications quasi simultanées. Il chronomètre chaque recalcul, vérifie les invariants et écrit `docs/REHEARSAL_REPORT.md`.

## Importer le jeu du jury

Glisser-déposer le fichier dans Salubri Map, ou :

```bash
curl -F file=@jeu_du_jury.zip http://localhost/api/imports
```

GeoJSON, CSV (`,` ou `;`) ou ZIP (fichier + photos). Chaque ligne passe par les mêmes règles qu'un signalement mobile. Formats : [docs/IMPORT.md](docs/IMPORT.md).

## Contribuer à OpenStreetMap

`GET /api/export/osm` produit un fichier `.osm` des dépotoirs vérifiés, prêt pour JOSM, sans aucune donnée personnelle. La procédure communautaire est décrite dans [docs/OSM.md](docs/OSM.md).

## Réutiliser Salubri dans une autre commune

Aucune donnée n'est codée en dur : une commune = un dossier `data/communes/<nom>/`. Voir [docs/NOUVELLE_COMMUNE.md](docs/NOUVELLE_COMMUNE.md).

## Architecture

PostgreSQL + PostGIS, FastAPI (Python 3.12), OR-Tools, OSRM, moteur de simulation multi-agents maison (numpy), nginx. Détails : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Règles de validation : [docs/RULES.md](docs/RULES.md). Contrat d'API pour les interfaces : [docs/FRONTEND_CONTEXT.md](docs/FRONTEND_CONTEXT.md) et [docs/openapi.json](docs/openapi.json).

## Données

| Source | Licence | Où |
|---|---|---|
| OpenStreetMap (voies, eau, écoles, marchés, santé) | ODbL 1.0 — © contributeurs OpenStreetMap | `data/osm/` |
| Google Open Buildings v3 (bâtiments) | CC-BY-4.0 / ODbL | `data/open_buildings/` |
| Populations par arrondissement : INSD, 5e RGPH 2019 | publication officielle | `data/communes/ouagadougou/quartiers.geojson` |
| SDGD 2020 (décharges et CCT, enquête 2019) | référence citée | `data/communes/ouagadougou/sdgd2020.geojson` |
| Signalements de démonstration | CC0 | `data/communes/ouagadougou/` |

Bâtiments : `python scripts/prepare_open_buildings.py` (1,35 Go téléchargés, 150 Mo gardés pour Ouagadougou, fichier hors git), puis recharger les données (choix 10 du lanceur). Tant que les extraits OSM et Open Buildings ne sont pas présents, Salubri génère une **ville synthétique** plausible pour que tout fonctionne. Voir [data/README.md](data/README.md) pour charger les vraies données.

## Licence

Code sous **AGPL-3.0-or-later** ([LICENSE](LICENSE)) : toute version modifiée et proposée en ligne doit publier ses sources, pour que le commun grandisse. Données dérivées d'OSM sous ODbL.

<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Matrice de contribution

## 1. Équipe (partie manuelle, à remplir par l'équipe)

Une ligne par membre, une colonne par couche ; mettre la part (en %) de chaque membre dans chaque couche, chaque
colonne totalisant 100 %.

| Membre | Données / terrain | App mobile (Salubri Go) | API | Optimisation | Simulation | Web (Map, Sim) | Infrastructure | Rapport / vidéo |
|---|---|---|---|---|---|---|---|---|
| [Nom 1] | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % |
| [Nom 2] | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % |
| [Nom 3] | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % |
| [Nom 4] | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % | [ ] % |

Outils d'aide au développement utilisés : [à compléter par l'équipe].

## 2. Briques réutilisées hors code (partie manuelle)

| Brique | Licence | Couche | Usage |
|---|---|---|---|
| OpenStreetMap (routes, eau, centres de santé) | ODbL 1.0 | données | réseau routier, zones d'exclusion |
| Google Open Buildings v3 | CC BY 4.0 / ODbL | données | bâtiments → îlots → demande |
| OSRM (profils sec / pluie) | BSD-2-Clause | optimisation | matrice de distances routières |
| PostGIS | GPL-2.0 | API | géométries, distances |
| YuNet 2023mar (OpenCV Zoo) | MIT | app mobile, API | détection des visages |
| YOLOv9-t plaques (open-image-models) | MIT | app mobile, API | détection des plaques |
| WIDER Face (validation), plaques Roboflow | recherche / CC BY 4.0 | validation | jeu de contrôle du masquage (non redistribué) |
| Polices Inter | OFL-1.1 | web, app mobile | typographie |

Détail des licences et attributions : `docs/LICENCES_TIERCES.md`.

## 3. Bibliothèques et images (généré par `scripts/matrice_contribution.py`)

<!-- debut-genere -->
| Brique | Version | Licence | Couche | Source de l'information |
|---|---|---|---|---|
| fastapi | 0.163.1 | MIT | API | pyproject.toml |
| uvicorn | 0.54.0 | BSD-3-Clause | API | pyproject.toml |
| pydantic | 2.14.3 | MIT | API | pyproject.toml |
| pydantic-settings | 2.16.3 | MIT | API | pyproject.toml |
| sqlalchemy | 2.1.8 | MIT | API | pyproject.toml |
| geoalchemy2 | 0.21.0 | MIT | API | pyproject.toml |
| alembic | 1.20.1 | MIT | API | pyproject.toml |
| psycopg | 3.3.9 | LGPL-3.0-only | API | pyproject.toml |
| ortools | 9.15.6755 | Apache Software License | optimisation | pyproject.toml |
| numpy | 2.5.5 | BSD-3-Clause (et licences des composants) | simulation, optimisation | pyproject.toml |
| scikit-learn | 1.9.1 | BSD-3-Clause | optimisation | pyproject.toml |
| shapely | 2.2.0 | BSD-3-Clause | données | pyproject.toml |
| pyproj | 3.8.0 | MIT | données | pyproject.toml |
| pillow | 13.0.0 | MIT-CMU | API (validation) | pyproject.toml |
| imagehash | 4.3.2 | 2-clause BSD License | API (validation) | pyproject.toml |
| httpx | 0.28.1 | BSD License | API | pyproject.toml |
| sse-starlette | 3.7.0 | BSD-3-Clause | API | pyproject.toml |
| osmium | 4.3.2 | BSD License | données | pyproject.toml |
| python-multipart | 0.0.34 | Apache-2.0 | API | pyproject.toml |
| pyyaml | 6.0.3 | MIT License | API | pyproject.toml |
| argon2-cffi | 25.1.0 | MIT | API | pyproject.toml |
| onnxruntime | 1.32.0 | MIT License | API (masquage) | pyproject.toml |
| @fontsource/inter | 5.3.0 | OFL-1.1 | app mobile | pnpm-lock.yaml |
| exifr | 7.1.3 | MIT | app mobile | pnpm-lock.yaml |
| lucide-react | 0.460.0 | ISC | app mobile | pnpm-lock.yaml |
| onnxruntime-web | 1.31.1 | MIT | app mobile (masquage) | pnpm-lock.yaml |
| react | 18.3.1 | MIT | app mobile | pnpm-lock.yaml |
| react-dom | 18.3.1 | MIT | app mobile | pnpm-lock.yaml |
| @fontsource/inter | 5.3.0 | OFL-1.1 | web | pnpm-lock.yaml |
| lucide-react | 0.460.0 | ISC | web | pnpm-lock.yaml |
| maplibre-gl | 6.18.0 | BSD-3-Clause | web | pnpm-lock.yaml |
| react | 18.3.1 | MIT | web | pnpm-lock.yaml |
| react-dom | 18.3.1 | MIT | web | pnpm-lock.yaml |
| react-router-dom | 7.18.5 | MIT | web | pnpm-lock.yaml |
| ghcr.io/project-osrm/osrm-backend:v5.27.1 | image | BSD-2-Clause | infrastructure | Dockerfile / docker-compose.yml |
| nginx:1.27-alpine | image | BSD-2-Clause | infrastructure | Dockerfile / docker-compose.yml |
| node:22-alpine | image | MIT | infrastructure | Dockerfile / docker-compose.yml |
| postgis/postgis:16-3.4 | image | GPL-2.0 (PostGIS), PostgreSQL License | infrastructure | Dockerfile / docker-compose.yml |
| python:3.12-slim | image | PSF-2.0 | infrastructure | Dockerfile / docker-compose.yml |
<!-- fin-genere -->

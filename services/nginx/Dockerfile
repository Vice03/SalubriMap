# SPDX-License-Identifier: AGPL-3.0-or-later
# Image « web » autonome : construit Salubri Map/Sim (apps/web) et Salubri Go (apps/go), puis les sert avec nginx.
# Contexte de build = racine du dépôt (voir docker-compose.yml). Aucun Node/pnpm requis sur la machine hôte.
FROM node:22-alpine AS build
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate
WORKDIR /src
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/
COPY apps/go/package.json apps/go/
RUN pnpm install --frozen-lockfile
COPY apps/web apps/web
COPY apps/go apps/go
RUN pnpm --filter web build && pnpm --filter go build

FROM nginx:1.27-alpine
COPY services/nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY services/nginx/placeholder/ /srv/placeholder/
COPY --from=build /src/apps/web/dist /srv/web
COPY --from=build /src/apps/go/dist /srv/go

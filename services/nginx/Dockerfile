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
# Certificat auto-signé pour l'accès HTTPS depuis un téléphone sur le réseau local (démo uniquement)
RUN apk add --no-cache openssl && mkdir -p /etc/nginx/salubri \
 && openssl req -x509 -nodes -newkey rsa:2048 -days 825 -subj "/CN=salubri.local" \
      -addext "subjectAltName=DNS:localhost,DNS:salubri.local,IP:127.0.0.1" \
      -keyout /etc/nginx/salubri/key.pem -out /etc/nginx/salubri/cert.pem \
 && apk del openssl
COPY services/nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY services/nginx/locations.conf /etc/nginx/salubri/locations.conf
COPY services/nginx/api_proxy.conf /etc/nginx/salubri/api_proxy.conf
COPY services/nginx/security_headers.conf /etc/nginx/salubri/security_headers.conf
COPY services/nginx/placeholder/ /srv/placeholder/
COPY --from=build /src/apps/web/dist /srv/web
COPY --from=build /src/apps/go/dist /srv/go

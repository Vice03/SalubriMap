# SPDX-License-Identifier: AGPL-3.0-or-later
FROM ghcr.io/project-osrm/osrm-backend:v5.27.1
COPY entrypoint.sh /entrypoint.sh
COPY profiles/ /profiles/
RUN chmod +x /entrypoint.sh
EXPOSE 5000
ENTRYPOINT ["/entrypoint.sh"]

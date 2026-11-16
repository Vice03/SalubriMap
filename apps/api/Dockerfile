# SPDX-License-Identifier: AGPL-3.0-or-later
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# libexpat1: needed by the osmium wheel (OSM extract loader); absent from python:slim
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.5.11
WORKDIR /app/apps/api
COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml && uv pip install --system pytest ruff
COPY . .
RUN uv pip install --system --no-deps -e .
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=12s --retries=12 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=10).status == 200 else 1)"
CMD ["uvicorn", "salubri_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

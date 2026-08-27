# Frontend image — Cloud Masking SPA (Milestone 17).
# Replaces the Milestone-2 placeholder. Multi-stage: Node build (Vite) -> static nginx serve with an
# /api reverse proxy that mirrors the Vite dev-proxy rewrite (ADR-0014 / ADR-0017).
#
# Build context is the repository root (see docker/docker-compose.yml `context: ..`).

# --- Stage 1: build the static bundle ----------------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /app

# Install from the committed lockfile first, as its own layer, so source edits do not re-install.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

# The SPA's API base URL is baked at build time; "/api" keeps it same-origin so nginx (prod) and the
# Vite dev server both serve the identical contract. Overridable, never a secret.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# `npm run build` = tsc --noEmit && vite build -> the image fails on any type error.
RUN npm run build

# --- Stage 2: serve static files + proxy /api --------------------------------------------------
FROM nginx:1.27-alpine AS serve

LABEL org.opencontainers.image.title="cloud-masking-frontend" \
      org.opencontainers.image.description="Cloud Masking React/TS SPA served by nginx with an /api reverse proxy." \
      org.opencontainers.image.licenses="TBD"

# Where the /api proxy points. Substituted into the template at container start by the nginx
# entrypoint; the filter keeps envsubst away from nginx's own $variables.
ENV BACKEND_HOST=backend \
    BACKEND_PORT=8000 \
    NGINX_ENVSUBST_FILTER=^BACKEND_

# Rendered to /etc/nginx/conf.d/default.conf at startup (overwriting the base image's default).
COPY docker/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# busybox wget (bundled in nginx:alpine) against nginx's own /healthz — no curl/apt needed.
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=5s \
    CMD wget -q --spider http://127.0.0.1/healthz || exit 1

# nginx:alpine's default entrypoint renders the templates, then runs nginx in the foreground.

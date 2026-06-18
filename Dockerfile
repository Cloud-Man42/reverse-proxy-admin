# syntax=docker/dockerfile:1

FROM node:20-bookworm-slim AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ubuntu:24.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ROOT=/app \
    FRONTEND_DIST=/app/frontend/dist \
    USE_SUDO=false \
    NGINX_RELOAD_MODE=signal \
    HOST=127.0.0.1 \
    PORT=8080

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        nginx \
        certbot \
        python3-certbot-nginx \
        python3-venv \
        python3-pip \
        apache2-utils \
        openssl \
        supervisor \
        curl \
        cron \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python3 -m venv /app/backend/.venv \
    && /app/backend/.venv/bin/pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY --from=frontend-build /build/dist /app/frontend/dist
COPY deploy/nginx/proxy-debug-log.conf /etc/nginx/conf.d/proxy-debug-log.conf
COPY deploy/docker/nginx.conf /etc/nginx/nginx.conf
COPY deploy/docker/admin-ui.conf /app/deploy/docker/admin-ui.conf
COPY deploy/docker/certbot-renew.cron /etc/cron.d/certbot-renew
COPY deploy/docker/supervisord.conf /etc/supervisor/conf.d/reverse-proxy-admin.conf
COPY deploy/docker/entrypoint.sh /entrypoint.sh

RUN sed -i 's/\r$//' /entrypoint.sh \
    && chmod +x /entrypoint.sh \
    && chmod 644 /etc/cron.d/certbot-renew \
    && mkdir -p /var/lib/reverse-proxy-admin/backups \
        /var/lib/reverse-proxy-admin/certbot/work \
        /var/lib/reverse-proxy-admin/certbot/logs \
        /etc/nginx/.htpasswd \
        /etc/letsencrypt/live \
        /var/log/nginx

EXPOSE 80 443 8443

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/api/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]

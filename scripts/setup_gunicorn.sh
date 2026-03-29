#!/usr/bin/env bash
# Configures the gunicorn systemd service and the nginx reverse proxy.
# Must be run as root: sudo bash scripts/setup_gunicorn.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_USER="appuser"
VENV_DIR="$APP_DIR/.venv"
ENV_FILE="$APP_DIR/.env"
GUNICORN_SERVICE="gunicorn"
GUNICORN_SOCKET="/run/gunicorn/gunicorn.sock"
NGINX_SITE="investment_club"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root. Try: sudo bash scripts/setup_gunicorn.sh"
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    error "${ENV_FILE} not found. Have you run setup_python.sh first?"
    exit 1
fi

if [[ ! -f "$VENV_DIR/bin/gunicorn" ]]; then
    error "Gunicorn not found at ${VENV_DIR}/bin/gunicorn. Have you run setup_python.sh first?"
    exit 1
fi

info "App directory: $APP_DIR"

# ---------------------------------------------------------------------------
# 1. Gunicorn systemd service
# ---------------------------------------------------------------------------
info "Writing gunicorn systemd service…"
GUNICORN_SERVICE_FILE="/etc/systemd/system/${GUNICORN_SERVICE}.service"

cat > "$GUNICORN_SERVICE_FILE" <<EOF
[Unit]
Description=Gunicorn daemon for investment_club
After=network.target postgresql.service
Requires=postgresql.service

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/gunicorn investment_club.wsgi:application \\
    --bind unix:${GUNICORN_SOCKET} \\
    --workers 3 \\
    --timeout 120 \\
    --access-logfile /var/log/gunicorn/access.log \\
    --error-logfile /var/log/gunicorn/error.log
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# ---------------------------------------------------------------------------
# 2. Log directory and Unix socket setup
# ---------------------------------------------------------------------------
info "Creating log and socket directories…"
mkdir -p /var/log/gunicorn
chown "$APP_USER:$APP_USER" /var/log/gunicorn

mkdir -p /run/gunicorn
chown "$APP_USER:$APP_USER" /run/gunicorn

# Recreate /run/gunicorn on every boot (tmpfs is cleared at shutdown)
echo "d /run/gunicorn 0755 ${APP_USER} ${APP_USER} -" \
    > /etc/tmpfiles.d/gunicorn.conf

# Allow nginx (www-data) to access the socket
usermod -aG "$APP_USER" www-data

# ---------------------------------------------------------------------------
# 3. Enable and start gunicorn
# ---------------------------------------------------------------------------
systemctl daemon-reload
systemctl enable "$GUNICORN_SERVICE"
systemctl restart "$GUNICORN_SERVICE"
info "Gunicorn service enabled and started."

# ---------------------------------------------------------------------------
# 4. nginx reverse proxy config
# ---------------------------------------------------------------------------
info "Writing nginx site config…"
NGINX_AVAILABLE="/etc/nginx/sites-available/${NGINX_SITE}"
NGINX_ENABLED="/etc/nginx/sites-enabled/${NGINX_SITE}"

cat > "$NGINX_AVAILABLE" <<EOF
upstream gunicorn_upstream {
    server unix:${GUNICORN_SOCKET};
}

server {
    listen 80;
    server_name _;

    client_max_body_size 20M;

    location /static/ {
        alias ${APP_DIR}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://gunicorn_upstream;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf "$NGINX_AVAILABLE" "$NGINX_ENABLED"

info "Testing nginx configuration…"
nginx -t

systemctl enable nginx
systemctl reload nginx
info "nginx configured and reloaded."

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
info "============================================================"
info " All services are running!"
info "============================================================"
info "  App directory  : ${APP_DIR}"
info "  Env file       : ${ENV_FILE}"
info "  Gunicorn       : systemctl status ${GUNICORN_SERVICE}"
info "  nginx          : systemctl status nginx"
info "  PostgreSQL     : systemctl status postgresql"
info ""
warn " Remember to:"
warn "  1. Edit ${ENV_FILE} with your real SECRET_KEY and DJANGO_ALLOWED_HOSTS."
warn "  2. Restart gunicorn after any .env changes:"
warn "     sudo systemctl restart ${GUNICORN_SERVICE}"
echo ""

#!/usr/bin/env bash
# Provisions a fresh Ubuntu 24 LTS VM for the investment_club Django project.
# Must be run as root: sudo bash setup.sh

set -euo pipefail

# ---------------------------------------------------------------------------
# Config — edit these if you want different defaults before running
# ---------------------------------------------------------------------------
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_USER="appuser"
VENV_DIR="$APP_DIR/.venv"
read -rp "PostgreSQL database name [investment_db]: " DB_NAME
DB_NAME="${DB_NAME:-investment_db}"

read -rp "PostgreSQL user [investment_user]: " DB_USER
DB_USER="${DB_USER:-investment_user}"

while true; do
    read -rsp "PostgreSQL password: " DB_PASS
    echo
    read -rsp "Confirm PostgreSQL password: " DB_PASS_CONFIRM
    echo
    if [[ "$DB_PASS" == "$DB_PASS_CONFIRM" ]]; then
        break
    fi
    error "Passwords do not match. Please try again."
done
PYTHON="python3.13"
GUNICORN_SERVICE="gunicorn"
GUNICORN_SOCKET="/run/gunicorn/gunicorn.sock"
NGINX_SITE="investment_club"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ---------------------------------------------------------------------------
# 0. Sanity checks
# ---------------------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root. Try: sudo bash setup.sh"
    exit 1
fi

if ! grep -qi "ubuntu" /etc/os-release; then
    warn "This script targets Ubuntu 24 LTS. Proceeding anyway…"
fi

info "App directory: $APP_DIR"

# ---------------------------------------------------------------------------
# 1. System update & APT repos
# ---------------------------------------------------------------------------
info "Updating package lists…"
apt-get update -y
apt-get upgrade -y

info "Installing prerequisites…"
apt-get install -y --no-install-recommends \
    software-properties-common \
    curl \
    gnupg \
    ca-certificates \
    lsb-release \
    apt-transport-https

# Python 3.13 via deadsnakes PPA (Ubuntu 24 ships 3.12)
info "Adding deadsnakes PPA for Python 3.13…"
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update -y
apt-get install -y --no-install-recommends \
    python3.13 \
    python3.13-venv \
    python3.13-dev \
    python3-pip

# PostgreSQL 17 via the official PostgreSQL apt repo
info "Adding official PostgreSQL 17 apt repository…"
PG_KEYRING="/usr/share/keyrings/pgdg.gpg"
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    | gpg --dearmor -o "$PG_KEYRING"
echo "deb [signed-by=${PG_KEYRING}] https://apt.postgresql.org/pub/repos/apt \
$(lsb_release -cs)-pgdg main" \
    > /etc/apt/sources.list.d/pgdg.list
apt-get update -y
apt-get install -y postgresql-17

# nginx & build deps for psycopg2
info "Installing nginx and build dependencies…"
apt-get install -y --no-install-recommends \
    nginx \
    libpq-dev \
    gcc

# ---------------------------------------------------------------------------
# 2. App user & virtualenv
# ---------------------------------------------------------------------------
info "Creating system user '$APP_USER'…"
if ! id "$APP_USER" &>/dev/null; then
    adduser --system --no-create-home --group "$APP_USER"
fi

info "Creating Python virtual environment at $VENV_DIR…"
"$PYTHON" -m venv "$VENV_DIR"

info "Installing Python requirements…"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install --no-cache-dir -r "$APP_DIR/requirements.txt"

info "Setting ownership of $APP_DIR to $APP_USER…"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# ---------------------------------------------------------------------------
# 3. Generate .env file (skipped if one already exists)
# ---------------------------------------------------------------------------
ENV_FILE="$APP_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
    warn ".env already exists — skipping generation. Review it before proceeding."
else
    info "Generating $ENV_FILE with placeholder values…"
    SECRET_KEY="$(python3 -c "import secrets, string; \
        chars=string.ascii_letters+string.digits+'!@#\$%^&*(-_=+)'; \
        print(''.join(secrets.choice(chars) for _ in range(50)))")"

    cat > "$ENV_FILE" <<EOF
SECRET_KEY=${SECRET_KEY}
DEBUG=False
DJANGO_ALLOWED_HOSTS="localhost 127.0.0.1"
POSTGRES_DB_NAME=${DB_NAME}
POSTGRES_DB_USER=${DB_USER}
POSTGRES_DB_PASSWORD=${DB_PASS}
POSTGRES_DB_HOST=localhost
POSTGRES_DB_PORT=5432
EOF
    chown "$APP_USER:$APP_USER" "$ENV_FILE"
    chmod 640 "$ENV_FILE"
    warn "Review and update $ENV_FILE (especially SECRET_KEY and DJANGO_ALLOWED_HOSTS) before going live."
fi

# ---------------------------------------------------------------------------
# 4. PostgreSQL setup
# ---------------------------------------------------------------------------
info "Starting PostgreSQL…"
systemctl enable postgresql
systemctl start postgresql

info "Creating PostgreSQL role '$DB_USER' and database '$DB_NAME'…"
# Run idempotently — ignore errors if role/db already exist
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}';" \
    | grep -q 1 || \
    sudo -u postgres psql -c "CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}';" \
    | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

# ---------------------------------------------------------------------------
# 5. Django migrate & collectstatic
# ---------------------------------------------------------------------------
info "Running Django migrations and collectstatic…"
cd "$APP_DIR"
sudo -u "$APP_USER" \
    env "$(grep -v '^#' "$ENV_FILE" | xargs)" \
    "$VENV_DIR/bin/python" manage.py migrate --noinput

sudo -u "$APP_USER" \
    env "$(grep -v '^#' "$ENV_FILE" | xargs)" \
    "$VENV_DIR/bin/python" manage.py collectstatic --noinput

# ---------------------------------------------------------------------------
# 6. Gunicorn systemd service
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

mkdir -p /var/log/gunicorn
chown "$APP_USER:$APP_USER" /var/log/gunicorn

# Create the runtime directory for the Unix socket and ensure nginx can access it
mkdir -p /run/gunicorn
chown "$APP_USER:$APP_USER" /run/gunicorn

# Persist the runtime directory across reboots via tmpfiles.d
echo "d /run/gunicorn 0755 ${APP_USER} ${APP_USER} -" \
    > /etc/tmpfiles.d/gunicorn.conf

# Allow nginx (www-data) to reach the socket
usermod -aG "$APP_USER" www-data

systemctl daemon-reload
systemctl enable "$GUNICORN_SERVICE"
systemctl restart "$GUNICORN_SERVICE"
info "Gunicorn service enabled and started."

# ---------------------------------------------------------------------------
# 7. nginx reverse proxy config
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

# Remove default site and enable ours
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
info " Setup complete!"
info "============================================================"
info " App directory  : $APP_DIR"
info " Virtual env    : $VENV_DIR"
info " Env file       : $ENV_FILE"
info " Gunicorn       : systemctl status ${GUNICORN_SERVICE}"
info " nginx          : systemctl status nginx"
info " PostgreSQL     : systemctl status postgresql"
info ""
warn " Remember to:"
warn "  1. Edit $ENV_FILE with your real SECRET_KEY and ALLOWED_HOSTS."
warn "  2. Restart gunicorn after any .env changes:"
warn "     sudo systemctl restart ${GUNICORN_SERVICE}"
echo ""

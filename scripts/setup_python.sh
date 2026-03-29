#!/usr/bin/env bash
# Installs Python 3.13, nginx, creates the app virtualenv, installs Python
# requirements, generates the .env file, and runs Django migrations.
# Must be run as root: sudo bash scripts/setup_python.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_USER="appuser"
VENV_DIR="$APP_DIR/.venv"
PYTHON="python3.13"
CREDS_FILE="/root/.investment_club_db"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ---------------------------------------------------------------------------
# Sanity check
# ---------------------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root. Try: sudo bash scripts/setup_python.sh"
    exit 1
fi

info "App directory: $APP_DIR"

# ---------------------------------------------------------------------------
# 1. Load or prompt for database credentials (written by setup_db.sh)
# ---------------------------------------------------------------------------
if [[ -f "$CREDS_FILE" ]]; then
    info "Loading database credentials from ${CREDS_FILE}…"
    # shellcheck source=/dev/null
    source "$CREDS_FILE"
else
    warn "${CREDS_FILE} not found. Have you run setup_db.sh first?"
    read -rp "PostgreSQL database name [investment_db]: " DB_NAME
    DB_NAME="${DB_NAME:-investment_db}"
    read -rp "PostgreSQL user [investment_user]: " DB_USER
    DB_USER="${DB_USER:-investment_user}"
    read -rsp "PostgreSQL password: " DB_PASS
    echo
fi

# ---------------------------------------------------------------------------
# 2. Python 3.13 via deadsnakes PPA
# ---------------------------------------------------------------------------
info "Updating package lists…"
apt-get update -y

info "Adding deadsnakes PPA for Python 3.13…"
apt-get install -y --no-install-recommends software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update -y

info "Installing Python 3.13…"
apt-get install -y --no-install-recommends \
    python3.13 \
    python3.13-venv \
    python3.13-dev \
    python3-pip

# ---------------------------------------------------------------------------
# 3. nginx and psycopg2 build dependencies
# ---------------------------------------------------------------------------
info "Installing nginx and build dependencies…"
apt-get install -y --no-install-recommends \
    nginx \
    libpq-dev \
    gcc

# ---------------------------------------------------------------------------
# 4. App user
# ---------------------------------------------------------------------------
info "Creating system user '${APP_USER}'…"
if ! id "$APP_USER" &>/dev/null; then
    adduser --system --no-create-home --group "$APP_USER"
fi

# ---------------------------------------------------------------------------
# 5. Virtualenv and Python requirements
# ---------------------------------------------------------------------------
info "Creating virtual environment at ${VENV_DIR}…"
"$PYTHON" -m venv "$VENV_DIR"

info "Installing Python requirements…"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install --no-cache-dir -r "$APP_DIR/requirements.txt"

# ---------------------------------------------------------------------------
# 6. Generate .env file
# ---------------------------------------------------------------------------
ENV_FILE="$APP_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
    warn ".env already exists — skipping generation. Review it before proceeding."
else
    info "Generating ${ENV_FILE}…"
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
    chmod 640 "$ENV_FILE"
    warn "Review ${ENV_FILE} (especially SECRET_KEY and DJANGO_ALLOWED_HOSTS) before going live."
fi

# ---------------------------------------------------------------------------
# 7. Set ownership and run Django setup
# ---------------------------------------------------------------------------
info "Setting ownership of ${APP_DIR} to ${APP_USER}…"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

info "Running Django migrations…"
cd "$APP_DIR"
sudo -u "$APP_USER" \
    env "$(grep -v '^#' "$ENV_FILE" | xargs)" \
    "$VENV_DIR/bin/python" manage.py migrate --noinput

info "Collecting static files…"
sudo -u "$APP_USER" \
    env "$(grep -v '^#' "$ENV_FILE" | xargs)" \
    "$VENV_DIR/bin/python" manage.py collectstatic --noinput

# ---------------------------------------------------------------------------
# 8. Clean up the credentials file
# ---------------------------------------------------------------------------
if [[ -f "$CREDS_FILE" ]]; then
    rm -f "$CREDS_FILE"
    info "Removed ${CREDS_FILE}."
fi

echo ""
info "Python environment setup complete."
info "  Virtual env : ${VENV_DIR}"
info "  Env file    : ${ENV_FILE}"
info "  Next step   : sudo bash scripts/setup_gunicorn.sh"
echo ""

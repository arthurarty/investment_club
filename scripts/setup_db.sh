#!/usr/bin/env bash
# Installs PostgreSQL 17 and creates the application database and role.
# Must be run as root: sudo bash scripts/setup_db.sh

set -euo pipefail

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
    error "This script must be run as root. Try: sudo bash scripts/setup_db.sh"
    exit 1
fi

# ---------------------------------------------------------------------------
# Prompt for database credentials
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# 1. Base prerequisites
# ---------------------------------------------------------------------------
info "Updating package lists…"
apt-get update -y

info "Installing prerequisites…"
apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    ca-certificates \
    lsb-release \
    apt-transport-https

# ---------------------------------------------------------------------------
# 2. PostgreSQL 17
# ---------------------------------------------------------------------------
info "Adding official PostgreSQL 17 apt repository…"
PG_KEYRING="/usr/share/keyrings/pgdg.gpg"
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    | gpg --dearmor -o "$PG_KEYRING"
echo "deb [signed-by=${PG_KEYRING}] https://apt.postgresql.org/pub/repos/apt \
$(lsb_release -cs)-pgdg main" \
    > /etc/apt/sources.list.d/pgdg.list

apt-get update -y
apt-get install -y postgresql-17

# ---------------------------------------------------------------------------
# 3. Start PostgreSQL and create role + database
# ---------------------------------------------------------------------------
info "Starting PostgreSQL…"
systemctl enable postgresql
systemctl start postgresql

info "Creating PostgreSQL role '${DB_USER}' and database '${DB_NAME}'…"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}';" \
    | grep -q 1 || \
    sudo -u postgres psql -c "CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}';" \
    | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

# ---------------------------------------------------------------------------
# 4. Save credentials for the next script to consume
# ---------------------------------------------------------------------------
CREDS_FILE="/root/.investment_club_db"
cat > "$CREDS_FILE" <<EOF
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASS=${DB_PASS}
EOF
chmod 600 "$CREDS_FILE"
info "Credentials saved to ${CREDS_FILE} (root-only, deleted by setup_python.sh)."

echo ""
info "Database setup complete."
info "  PostgreSQL : systemctl status postgresql"
info "  Next step  : sudo bash scripts/setup_python.sh"
echo ""

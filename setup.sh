#!/usr/bin/env bash
# Orchestrator — runs all three setup scripts in sequence.
# Use this only if your VM has sufficient RAM to handle everything at once.
# Otherwise run each script individually and reboot between steps:
#
#   sudo bash scripts/setup_db.sh
#   sudo bash scripts/setup_python.sh
#   sudo bash scripts/setup_gunicorn.sh

set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/scripts" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root. Try: sudo bash setup.sh"
    exit 1
fi

info "==> Step 1/3: Database"
bash "$SCRIPTS_DIR/setup_db.sh"

info "==> Step 2/3: Python environment"
bash "$SCRIPTS_DIR/setup_python.sh"

info "==> Step 3/3: Gunicorn & nginx"
bash "$SCRIPTS_DIR/setup_gunicorn.sh"

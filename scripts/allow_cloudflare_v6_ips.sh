#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IP_FILE="$SCRIPT_DIR/cloud_flare_v6_ips.txt"

if [[ ! -f "$IP_FILE" ]]; then
  echo "Error: $IP_FILE not found." >&2
  exit 1
fi

if [[ $EUID -ne 0 ]]; then
  echo "Error: this script must be run as root (use sudo)." >&2
  exit 1
fi

echo "Allowing Cloudflare IPv6 ranges via ip6tables..."

while IFS= read -r ip || [[ -n "$ip" ]]; do
  # Skip blank lines and comments
  [[ -z "$ip" || "$ip" == \#* ]] && continue

  echo "  Allowing $ip"
  ip6tables -I INPUT -p tcp -m multiport --dports http,https -s "$ip" -j ACCEPT
done < "$IP_FILE"

echo "Done. Current INPUT chain (IPv6):"
ip6tables -L INPUT -n -v --line-numbers

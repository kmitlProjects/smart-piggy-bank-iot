#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./tools/sync_up.sh <host> <password>
# Example:
#   ./tools/sync_up.sh 10.163.23.245 neae4850

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <host> <password>"
  exit 1
fi

HOST="$1"
PASS="$2"
PY="python"
CLI="tools/webrepl_cli.py"

upload_with_retry() {
  local src="$1"
  local dst="$2"
  local attempts=0
  local max_attempts=3

  while true; do
    attempts=$((attempts + 1))
    if "$PY" "$CLI" -p "$PASS" "$src" "$dst"; then
      return 0
    fi

    if [[ $attempts -ge $max_attempts ]]; then
      echo "Upload failed after ${max_attempts} attempts: $src"
      return 1
    fi

    echo "Retry ${attempts}/${max_attempts} for $src ..."
    sleep 1
  done
}

if [[ ! -f "$CLI" ]]; then
  echo "Error: $CLI not found"
  exit 1
fi

if [[ ! -d "esp32" ]]; then
  echo "Error: esp32 directory not found"
  exit 1
fi

echo "Uploading esp32/*.py to $HOST ..."
for f in esp32/*.py; do
  [[ -f "$f" ]] || continue
  dst="${HOST}:/$(basename "$f")"
  echo "  $f -> $dst"
  upload_with_retry "$f" "$dst"
done

echo "Uploading esp32/lib/*.py to $HOST ..."
for f in esp32/lib/*.py; do
  [[ -f "$f" ]] || continue
  dst="${HOST}:/lib/$(basename "$f")"
  echo "  $f -> $dst"
  upload_with_retry "$f" "$dst"
done

echo "Done."

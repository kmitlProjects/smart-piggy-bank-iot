#!/usr/bin/env bash
set -euo pipefail


# Usage:
#   ./tools/sync_up.sh <host|auto> <password> [preferred_ip]
# Example:
#   ./tools/sync_up.sh 10.163.23.245 neae4850
#   ./tools/sync_up.sh auto neae4850
#   ./tools/sync_up.sh auto neae4850 10.164.223.24

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "Usage: $0 <host|auto> <password> [preferred_ip]"
  exit 1
fi

HOST="$1"
PASS="$2"
PREFERRED_IP=""
if [[ $# -eq 3 ]]; then
  PREFERRED_IP="$3"
fi
PY="python3"
CLI="tools/webrepl_cli.py"
FINDER="tools/find_webrepl_host.py"
CACHE_FILE="tools/.webrepl_last_host"
MDNS_HOSTNAME="esp32.local"
FIND_TIMEOUT="0.5"

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

if [[ ! -f "$FINDER" ]]; then
  echo "Error: $FINDER not found"
  exit 1
fi

if [[ ! -d "esp32" ]]; then
  echo "Error: esp32 directory not found"
  exit 1
fi

if [[ "$HOST" == "auto" ]]; then
  LOCAL_IP="$($PY "$FINDER" --local-ip 2>/dev/null || true)"
  if [[ -n "$LOCAL_IP" ]]; then
    LOCAL_SUBNET="${LOCAL_IP%.*}.0/24"
    echo "Local Wi-Fi IP: $LOCAL_IP"
    echo "Scanning subnet: $LOCAL_SUBNET (port 8266)"
  else
    echo "Scanning local subnet (port 8266)"
  fi

  echo "Discovering WebREPL host on local network ..."
  PREFERRED_IP=""
  CACHE_IP=""
  if [[ -f "$CACHE_FILE" ]]; then
    CACHE_IP="$(tr -d '[:space:]' < "$CACHE_FILE")"
    if [[ -n "$CACHE_IP" ]]; then
      echo "Last successful host: $CACHE_IP"
    fi
  fi

  FIND_ARGS=(--first --print-network --timeout "$FIND_TIMEOUT" --hostname "$MDNS_HOSTNAME" --cache-file "$CACHE_FILE")
  if [[ -n "$PREFERRED_IP" ]]; then
    FIND_ARGS+=(--prefer-ip "$PREFERRED_IP")
  fi
  if [[ -n "$CACHE_IP" ]]; then
    FIND_ARGS+=(--prefer-ip "$CACHE_IP")
  fi

  if ! HOST="$($PY "$FINDER" "${FIND_ARGS[@]}")"; then
    echo "Error: could not auto-discover WebREPL host (port 8266)."
    echo "Tip: ensure ESP32 is connected to the same Wi-Fi and WebREPL is enabled."
    exit 1
  fi
  echo "Auto-discovered host: $HOST"
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

printf '%s\n' "$HOST" > "$CACHE_FILE"
echo "Saved last successful host to $CACHE_FILE"

echo "Done."

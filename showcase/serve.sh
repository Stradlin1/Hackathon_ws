#!/usr/bin/env bash
# Serve the static showcase. No build step, no network.
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8600}"
BIND="${BIND:-127.0.0.1}"
echo "showcase  ->  http://${BIND}:${PORT}/"
echo "app demo  ->  http://127.0.0.1:8501/ (start ./run.sh first)"
exec python3 -m http.server "$PORT" --bind "$BIND"

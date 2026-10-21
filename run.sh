#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
if command -v streamlit >/dev/null 2>&1; then
  exec streamlit run app.py "$@"
fi
exec python -m streamlit run app.py "$@"

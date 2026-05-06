#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
API_DIR="${ROOT_DIR}/apps/api"
WEB_DIR="${ROOT_DIR}/apps/web"

ensure_api_venv() {
  if [ ! -x "${API_DIR}/.venv/bin/python" ]; then
    python3 -m venv "${API_DIR}/.venv"
  fi
  "${API_DIR}/.venv/bin/python" -m pip install --upgrade pip
  "${API_DIR}/.venv/bin/python" -m pip install -e "${API_DIR}[dev]"
}

ensure_web_deps() {
  cd "${WEB_DIR}"
  if [ -f package-lock.json ]; then
    npm ci
  else
    npm install
  fi
}

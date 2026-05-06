#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

ensure_api_venv

if [ ! -f "${API_DIR}/.env" ]; then
  cp "${API_DIR}/.env.example" "${API_DIR}/.env"
fi

cd "${API_DIR}"
exec .venv/bin/uvicorn app.main:app --reload

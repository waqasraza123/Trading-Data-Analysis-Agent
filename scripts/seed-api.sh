#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

ensure_api_venv

cd "${API_DIR}"
exec .venv/bin/python -m app.cli seed

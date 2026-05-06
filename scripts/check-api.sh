#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

ensure_api_venv

cd "${API_DIR}"
.venv/bin/ruff check .
.venv/bin/mypy app
.venv/bin/pytest
.venv/bin/alembic heads
.venv/bin/alembic history

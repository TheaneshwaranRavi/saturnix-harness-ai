#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p data backups

export SATURNIX_ENABLE_MOCK_BRAINS="${SATURNIX_ENABLE_MOCK_BRAINS:-true}"
export SATURNIX_ENABLE_CHROMA="${SATURNIX_ENABLE_CHROMA:-false}"
export SATURNIX_DASHBOARD_AUTH_REQUIRED="${SATURNIX_DASHBOARD_AUTH_REQUIRED:-false}"
export SATURNIX_SQLITE_PATH="${SATURNIX_SQLITE_PATH:-./data/saturnix.sqlite3}"
export SATURNIX_CHROMA_PATH="${SATURNIX_CHROMA_PATH:-./data/chroma}"

HOST="${SATURNIX_API_HOST:-0.0.0.0}"
PORT="${SATURNIX_API_PORT:-8088}"

exec python3.11 -m uvicorn saturnix_harness.main:app \
  --reload \
  --host "$HOST" \
  --port "$PORT"

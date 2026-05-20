#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/frontend"

export NEXT_PUBLIC_SATURNIX_API_BASE="${NEXT_PUBLIC_SATURNIX_API_BASE:-http://localhost:8088}"
export NEXT_TELEMETRY_DISABLED="${NEXT_TELEMETRY_DISABLED:-1}"

if [ ! -d node_modules ]; then
  npm install
fi

exec npm run dev

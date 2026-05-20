#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PIDS=()

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}

trap cleanup EXIT INT TERM

scripts/run_backend.sh &
PIDS+=("$!")

scripts/run_frontend.sh &
PIDS+=("$!")

cat <<'EOF'
SATURNIX-HARNESS Secure Dashboard MVP is starting.

Backend:   http://localhost:8088
API docs:  http://localhost:8088/docs
Frontend:  http://localhost:3000

Press Ctrl+C to stop both services.
EOF

wait

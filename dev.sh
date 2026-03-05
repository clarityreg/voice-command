#!/usr/bin/env bash
# Start Clarity backend + frontend for local development.
# Usage: ./dev.sh

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT/backend"
PIDS=()

cleanup() {
  echo ""
  echo "Shutting down..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null
  echo "Done."
}
trap cleanup EXIT INT TERM

# ── Backend (FastAPI on :8001) ──────────────────────────────────
echo "Starting backend..."
cd "$BACKEND_DIR"
DOTENV_CONFIG=1 dotenvx run -- uv run uvicorn clarity_backend.main:app --host 0.0.0.0 --port 8070 --reload &
PIDS+=($!)
cd "$ROOT"

# ── Frontend (Next.js dev server) ───────────────────────────────
echo "Starting frontend..."
bun run dev --port 3070 &
PIDS+=($!)

echo ""
echo "  Backend  → http://localhost:8070"
echo "  Frontend → http://localhost:3070"
echo ""
echo "Press Ctrl+C to stop both."

wait

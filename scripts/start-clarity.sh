#!/bin/bash
# Start Clarity Command Centre — backend + optional Claude Code channels
#
# Usage:
#   ./scripts/start-clarity.sh                  # Backend only
#   ./scripts/start-clarity.sh --with-channels  # Backend + Telegram + webhooks
#   ./scripts/start-clarity.sh --backend-only   # Just the FastAPI backend

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_PORT="${CLARITY_BACKEND_PORT:-8070}"

cleanup() {
  echo ""
  echo "[clarity] Shutting down..."
  kill $BACKEND_PID 2>/dev/null
  wait $BACKEND_PID 2>/dev/null
  echo "[clarity] Done."
}

trap cleanup EXIT INT TERM

# --- Start backend ---
echo "[clarity] Starting backend on :${BACKEND_PORT}..."
cd "$PROJECT_DIR/backend"
uv run uvicorn clarity_backend.main:app --port "$BACKEND_PORT" &
BACKEND_PID=$!

# Wait for backend to be ready
for i in $(seq 1 30); do
  if curl -sf "http://localhost:${BACKEND_PORT}/health" > /dev/null 2>&1; then
    echo "[clarity] Backend ready."
    break
  fi
  sleep 1
done

if ! curl -sf "http://localhost:${BACKEND_PORT}/health" > /dev/null 2>&1; then
  echo "[clarity] ERROR: Backend failed to start within 30s"
  exit 1
fi

# --- Handle flags ---
if [[ "$1" == "--backend-only" ]]; then
  echo "[clarity] Running backend only. Press Ctrl+C to stop."
  wait $BACKEND_PID
  exit 0
fi

if [[ "$1" == "--with-channels" ]]; then
  echo "[clarity] Starting Claude Code with channels..."
  cd "$PROJECT_DIR"

  CHANNEL_ARGS=""

  # Check for Telegram plugin
  if [[ -f ".claude/plugins/clarity-telegram/index.ts" ]]; then
    if [[ -n "$TELEGRAM_BOT_TOKEN" ]] || [[ -f ".claude/plugins/clarity-telegram/.env" ]]; then
      CHANNEL_ARGS="$CHANNEL_ARGS plugin:clarity-telegram"
      echo "[clarity] Telegram channel enabled."
    else
      echo "[clarity] Telegram: skipped (no TELEGRAM_BOT_TOKEN or .env file)"
    fi
  fi

  # Check for webhook plugin
  if [[ -f ".claude/plugins/clarity-webhooks/index.ts" ]]; then
    CHANNEL_ARGS="$CHANNEL_ARGS plugin:clarity-webhooks"
    echo "[clarity] Webhook receiver enabled."
  fi

  if [[ -n "$CHANNEL_ARGS" ]]; then
    exec claude --channels $CHANNEL_ARGS "${@:2}"
  else
    echo "[clarity] No channels configured. Running Claude Code without channels."
    exec claude "${@:2}"
  fi
else
  echo "[clarity] Backend running on http://localhost:${BACKEND_PORT}"
  echo "[clarity] Use --with-channels to start Claude Code with Telegram/webhook channels"
  echo "[clarity] Press Ctrl+C to stop."
  wait $BACKEND_PID
fi

#!/usr/bin/env bash
set -euo pipefail

# Starts the backend API and the indexing service concurrently.
# - API runs via uvicorn
# - Indexer runs as a background process (src.indexing)
# - Logs are written to ./logs
# - PID files are written to ./run

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT"

mkdir -p "$ROOT/logs" "$ROOT/run"

API_LOG="$ROOT/logs/api.log"
INDEX_LOG="$ROOT/logs/indexer.log"
API_PID_FILE="$ROOT/run/api.pid"
INDEX_PID_FILE="$ROOT/run/indexer.pid"

echo "Starting Invoice Chatbot services (logs: $ROOT/logs)"

# Start API (uvicorn) in background
echo "Starting API (uvicorn)..."
uv run uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload >>"$API_LOG" 2>&1 &
API_PID=$!
echo $API_PID > "$API_PID_FILE"

# Start indexer in background (unbuffered python)
echo "Starting indexer (src.indexing)..."
PYTHONUNBUFFERED=1 uv run python -m src.indexing >>"$INDEX_LOG" 2>&1 &
INDEX_PID=$!
echo $INDEX_PID > "$INDEX_PID_FILE"

echo "API PID: $API_PID (log: $API_LOG)"
echo "Indexer PID: $INDEX_PID (log: $INDEX_LOG)"
echo "Use 'make stop' to stop both services."

cleanup() {
    echo "Shutting down services..."
    if [ -f "$API_PID_FILE" ]; then
        kill "$(cat $API_PID_FILE)" 2>/dev/null || true
        rm -f "$API_PID_FILE"
    fi
    if [ -f "$INDEX_PID_FILE" ]; then
        kill "$(cat $INDEX_PID_FILE)" 2>/dev/null || true
        rm -f "$INDEX_PID_FILE"
    fi
}

trap cleanup EXIT INT TERM

# Wait for API process to exit; keep indexer running until API stops or script is terminated
wait $API_PID || true

echo "API exited; stopping indexer..."
cleanup

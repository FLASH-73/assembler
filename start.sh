#!/usr/bin/env bash
# Start the Nextis Assembler — backend (FastAPI) + frontend (Next.js)
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python}"

echo "=== Killing stale processes ==="
lsof -ti :8000 | xargs kill 2>/dev/null && echo "  Killed backend (port 8000)" || true
lsof -ti :3000 | xargs kill 2>/dev/null && echo "  Killed frontend (port 3000)" || true
sleep 1

# Cleanup on Ctrl+C
cleanup() {
    echo ""
    echo "=== Shutting down ==="
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "Done."
}
trap cleanup INT TERM

echo "=== Starting backend (port 8000) ==="
cd "$DIR"
"$PYTHON" -m uvicorn nextis.api.app:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "=== Starting frontend (port 3000) ==="
cd "$DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "=== AURA is running ==="
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "  Press Ctrl+C to stop"
echo ""

wait

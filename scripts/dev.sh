#!/usr/bin/env bash
# Starts the backend (port 8010) and the frontend (port 5173); Ctrl+C stops both.
set -u
root="$(cd "$(dirname "$0")/.." && pwd)"
(cd "$root/backend" && python -X utf8 -m referee) &
backend=$!
(cd "$root/frontend" && npm run dev) &
frontend=$!
trap 'kill $backend $frontend 2>/dev/null' INT TERM EXIT
echo "Backend: http://localhost:8010/docs   Frontend: http://localhost:5173"
wait

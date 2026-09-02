#!/usr/bin/env bash
# Start Enarratio: analysis API on :8000, reading interface on :5173.
# Everything runs locally; nothing about a pasted passage leaves this machine.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "No .venv found. Creating one (Python 3.12 -- the NLP stack has no 3.14 wheels)…"
  uv venv --python 3.12 .venv
  uv pip install --python .venv/bin/python -r server/requirements.txt
fi
[ -d web/node_modules ] || npm --prefix web install

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

PYTHONPATH=server .venv/bin/python -m uvicorn enarratio.app:app \
  --host 127.0.0.1 --port 8000 &
npm --prefix web run dev &

echo
echo "  Enarratio → http://localhost:5173"
echo "  API       → http://127.0.0.1:8000/api/health"
echo "  Ctrl-C to stop both."
wait

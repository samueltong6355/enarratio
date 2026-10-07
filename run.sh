#!/usr/bin/env bash
# One local server; ordinary startup never downloads dependencies or data.
set -euo pipefail
cd "$(dirname "$0")"

if [[ "${1:-}" == "--setup" ]]; then
  command -v uv >/dev/null || { echo "Install uv first: https://docs.astral.sh/uv/"; exit 1; }
  command -v npm >/dev/null || { echo "Install Node.js (including npm) first."; exit 1; }
  [[ -x .venv/bin/python ]] || uv venv --python 3.12 .venv
  uv pip install --python .venv/bin/python -r server/requirements.txt
  npm --prefix web ci
  npm --prefix web run build
  echo "Setup complete. Start with ./run.sh (works without internet)."
  exit 0
fi
[[ -x .venv/bin/python ]] || { echo "Missing Python environment. While online, run ./run.sh --setup once."; exit 1; }
export PYTHONPATH="$PWD/server${PYTHONPATH:+:$PYTHONPATH}"
exec .venv/bin/python scripts/launch.py "$@"

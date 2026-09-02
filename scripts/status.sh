#!/usr/bin/env bash
# Where things stand. Run this first in a new session.
cd "$(dirname "$0")/.."
bold() { printf "\033[1m%s\033[0m\n" "$1"; }

bold "== Enarratio status =="
echo "branch $(git rev-parse --abbrev-ref HEAD)  |  $(git rev-list --count HEAD) commits  |  $(git status --porcelain | wc -l | tr -d ' ') files dirty"
echo
bold "-- last 5 commits"
git log --oneline -5
echo
bold "-- tests"
if [ -x .venv/bin/python ]; then
  PYTHONPATH=server .venv/bin/python -m pytest server/tests -q 2>&1 | tail -3
else
  echo "  no .venv — run ./run.sh to create it"
fi
echo
bold "-- data files (gitignored, fetched at setup)"
for f in data/*.db data/*.parquet; do
  [ -e "$f" ] && printf "  %-34s %s\n" "$(basename "$f")" "$(du -h "$f" | cut -f1)"
done
[ -e data/morpheus-quantities.db ] || echo "  MISSING morpheus-quantities.db — scansion degrades to position-only"
echo
bold "-- servers"
curl -s -o /dev/null -w "  api  :8000  %{http_code}\n" --max-time 1 http://127.0.0.1:8000/api/health 2>/dev/null || echo "  api  :8000  down"
curl -s -o /dev/null -w "  web  :5173  %{http_code}\n" --max-time 1 http://localhost:5173/ 2>/dev/null || echo "  web  :5173  down"
echo
bold "-- AP Latin syllabus coverage"
if [ -f data/passages.db ]; then
  PYTHONPATH=server .venv/bin/python scripts/ap_coverage.py 2>/dev/null | tail -4 | sed 's/^/  /'
else
  echo "  passages.db not built — run scripts/build-data.sh"
fi
echo
bold "-- next actions (from docs/STATE.md)"
sed -n '/^## Next actions/,/^## /p' docs/STATE.md 2>/dev/null | grep -E '^[0-9]+\.' | head -6
echo
echo "Full detail: docs/STATE.md"

#!/usr/bin/env bash
# Build the local databases in data/ from openly-licensed sources.
#
# Nothing here is vendored into the repository: the sources are large and separately
# licensed (Perseus TEI markup is CC BY-SA 3.0; the underlying texts of Servius, Conington
# and Vergil are public domain). data/ is gitignored, so this script is how a fresh clone
# acquires them.
#
#   scripts/build-data.sh [path-to-perseus-opensource-dir]
#
# The Perseus "hopper" open-source dump is at
#   https://github.com/PerseusDL/hopper  (or the GreekRoman tarball from Perseus downloads)
# and the directory wanted is  Classics/Vergil/opensource/.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data

SRC="${1:-}"
if [ -z "$SRC" ]; then
  for guess in \
      "$HOME/hopper/Classics/Vergil/opensource" \
      "/private/tmp/claude-501/-Users-samueltong"/*/*/scratchpad/hopper/Classics/Vergil/opensource; do
    [ -d "$guess" ] && SRC="$guess" && break
  done
fi
if [ -z "$SRC" ] || [ ! -d "$SRC" ]; then
  echo "Perseus source directory not found."
  echo "Pass it explicitly:  scripts/build-data.sh /path/to/Classics/Vergil/opensource"
  exit 1
fi
echo "Source: $SRC"

echo
echo "== commentary (Servius, Conington) =="
PYTHONPATH=server .venv/bin/python -m enarratio.commentary ingest "$SRC"

echo
echo "== passage index (Aeneid, Eclogues, Georgics) =="
PYTHONPATH=server .venv/bin/python -m enarratio.identify build "$SRC"

echo
if [ ! -f data/morpheus-quantities.db ]; then
  cat <<'MSG'
== vowel quantities: MISSING ==
  Scansion needs data/morpheus-quantities.db (Morpheus forms with marked quantities).
  Build it with Johan Winge's latin-macronizer (GPL-3.0):
      https://github.com/Alatius/latin-macronizer
  and copy its macrons.db to data/morpheus-quantities.db.
  Without it, scansion still works but relies on position and diphthongs alone.
MSG
else
  echo "== vowel quantities: present ($(du -h data/morpheus-quantities.db | cut -f1)) =="
fi

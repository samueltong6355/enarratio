#!/usr/bin/env bash
# Build the local databases in data/ from openly-licensed sources.
#
# Nothing here is vendored into the repository: the sources are large and separately
# licensed (Perseus TEI markup is CC BY-SA 3.0; the underlying texts of Servius, Conington
# and Vergil are public domain). data/ is gitignored, so this script is how a fresh clone
# acquires them.
#
#   scripts/build-data.sh /path/to/hopper/Classics [/path/to/lat_text_latin_library]
#
# The Perseus "hopper" open-source dump is at
#   https://github.com/PerseusDL/hopper  (or the GreekRoman tarball from Perseus downloads)
# and the directory wanted is  Classics/  (the whole tree, not one author).
set -euo pipefail
cd "$(dirname "$0")/.."

SRC="${1:-}"
if [ -z "$SRC" ] || [ ! -d "$SRC" ]; then
  echo "Perseus source directory not found."
  echo "Pass it explicitly:  scripts/build-data.sh /path/to/hopper/Classics"
  exit 1
fi
echo "Source: $SRC"

echo
echo "== commentary (Servius, Conington, Shorey, Merrill, Allen & Greenough) =="
PYTHONPATH=server .venv/bin/python -m enarratio.commentary ingest "$SRC"

echo
echo "== passage index (Vergil, Horace, Catullus, Ovid, Caesar) =="
PYTHONPATH=server .venv/bin/python -m enarratio.identify build "$SRC"

echo
echo "== The Latin Library (optional: breadth, no commentary) =="
LL="${2:-}"
if [ -n "$LL" ] && [ -d "$LL" ]; then
  PYTHONPATH=server .venv/bin/python -m enarratio.latinlibrary build "$LL" | tail -3
else
  echo "  not found. Clone https://github.com/cltk/lat_text_latin_library for wider"
  echo "  passage identification (Livy, Tacitus, Sallust, Juvenal, Lucretius, Seneca...)."
  echo "  It carries texts only -- no commentary."
fi

echo
QUANTITY_DB="${ENARRATIO_QUANTITY_DB:-${ENARRATIO_DATA_DIR:-data}/morpheus-quantities.db}"
if [ ! -f "$QUANTITY_DB" ]; then
  cat <<'MSG'
== vowel quantities: MISSING ==
  Scansion needs data/morpheus-quantities.db (Morpheus forms with marked quantities).
  Build it with Johan Winge's latin-macronizer (GPL-3.0):
      https://github.com/Alatius/latin-macronizer
  and copy its macrons.db to data/morpheus-quantities.db.
  Without it, scansion still works but relies on position and diphthongs alone.
MSG
else
  echo "== vowel quantities: present ($(du -h "$QUANTITY_DB" | cut -f1)) =="
fi

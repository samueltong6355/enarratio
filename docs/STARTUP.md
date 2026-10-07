# Starting Enarratio

## First installation (internet required)

Install uv and Node.js, then in the project folder:

```sh
./run.sh --setup
./run.sh
```

Setup installs Python 3.12, the Latin model and dictionaries, and the reader dependencies.
It builds the reader. It does **not** download optional research databases. Setup may take
several minutes and substantial disk space because the existing Latin model is large.

## Everyday use (internet not required)

```sh
./run.sh
```

Open **http://127.0.0.1:8000**. Keep the terminal running. The page reports model warm-up,
then enables analysis. Page and API share this address, so there is no cross-origin setup.
`--offline` explicitly selects the same default behavior: no automatic installations or
downloads. Source changes rebuild the reader locally when needed.

The local server is still necessary for **new analyses**. Disconnecting from the internet
does not stop it. Saved analyses are stored in this browser and can be reopened in an
already loaded page even if the server stops. There is no service worker: reopening the
site from scratch still requires the local server. Export JSON for a durable backup;
clearing browser data deletes saved readings. Storage is specific to browser and address
(a different port has separate saved readings). Export contains the entire pasted text.

## Troubleshooting

- **Failed to fetch / cannot connect:** use the address printed by `./run.sh`, not an old
  `localhost:5173` bookmark or a double-clicked HTML file. Keep the server terminal open.
- **Incomplete installation:** `./run.sh --setup` repairs an existing partial environment.
  It is the explicit online step. Ordinary startup does not attempt a download.
- **Port already in use:** an old server may still be running. Stop that terminal, or use
  `./run.sh --port 8001`, then open the newly printed address. The launcher never kills
  unrelated processes. A port conflict aborts rather than silently changing the port.
- **Model could not load:** the page and health endpoint remain reachable. Read the
  terminal error, repair with setup if appropriate, and restart. This is distinct from
  missing optional research data.
- **Long passages:** try a shorter excerpt. Requests have a two-minute client timeout;
  timing out does not cancel work already running on the server.
- **Installation check:** `./run.sh --check` checks dependencies, built assets and optional
  data without starting a server. The running app verifies actual model loading.

## Optional local research data

A fresh clone does not include the large, separately licensed databases. Missing files
are normal; morphology, syntax and literary-device heuristics continue working.

| File | Enables |
| --- | --- |
| `data/passages.db` | Known-passage recognition |
| `data/commentary.db` | Imported editorial notes for recognized passages |
| `data/morpheus-quantities.db` | Lexical vowel quantities for more reliable hexameter scans |

To reuse existing data without copying it, set `ENARRATIO_DATA_DIR` to its directory before
launching. `ENARRATIO_QUANTITY_DB` optionally overrides just the quantity file.

For already downloaded Perseus source XML:

```sh
scripts/build-data.sh /path/to/hopper/Classics
# Optional second argument adds Latin Library texts, not commentary:
scripts/build-data.sh /path/to/hopper/Classics /path/to/lat_text_latin_library
```

This explicitly rebuilds the local data; back up existing databases first. Source download
and licensing information is in [research/commentary-sources.md](research/commentary-sources.md).
The quantity database still needs to be built/copied separately as described by the script.
Restart after changing database files. Corrupt optional databases are reported without
discarding the core word analysis. No corpus is silently downloaded at startup.

## Developer mode and verification

```sh
PYTHONPATH=server .venv/bin/python -m uvicorn enarratio.app:app --host 127.0.0.1 --port 8000
npm --prefix web run dev
# In another terminal:
PYTHONPATH=server .venv/bin/python -m pytest server/tests -q
npm --prefix web run build
# With the application running (adjust port as needed):
node web/scripts/smoke.mjs http://127.0.0.1:8000
```

The development page is http://127.0.0.1:5173 and proxies `/api` to port 8000. It refuses
a busy port. `VITE_API` is an optional build-time override for custom installations;
normally leave it unset. `/api/health` reports `warming`, `ready` or `error`, and optional
data status. `/api/constructions` lists core, case-use and clause rules. New analyses
return 503 while warming or if model loading failed, with an actionable message.

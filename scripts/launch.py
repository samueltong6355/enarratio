"""Offline launcher. Installs nothing; owns exactly one local server process."""
import argparse
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check installation without starting")
    parser.add_argument("--offline", action="store_true", help="Explicit offline mode (also the default)")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    missing = [name for name in ("uvicorn", "fastapi", "spacy", "numpy", "lingua", "latincy_lexicon", "la_core_web_lg")
               if importlib.util.find_spec(name) is None]
    if missing:
        print("Incomplete installation: " + ", ".join(missing))
        print("While online, repair it with ./run.sh --setup. No downloads were attempted.")
        return 1
    built = ROOT / "web/dist/index.html"
    sources = [*ROOT.glob("web/src/**/*"), ROOT / "web/package-lock.json", ROOT / "web/vite.config.ts"]
    stale = not built.exists() or any(p.is_file() and p.stat().st_mtime > built.stat().st_mtime for p in sources)
    if stale:
        if args.check:
            print("Reader needs building: npm --prefix web run build (no internet needed after setup).")
            return 1
        try:
            subprocess.run(["npm", "--prefix", "web", "run", "build"], cwd=ROOT, check=True)
        except (OSError, subprocess.CalledProcessError):
            print("Could not build the reader. Run ./run.sh --setup while online to repair dependencies.")
            return 1
    from enarratio.storage import resource_status
    for name, status in resource_status().items():
        print(f"Optional {name}: {status['status']}")
    if args.check:
        print("Installation ready. Start with ./run.sh; no internet required.")
        return 0
    try:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", args.port))
    except OSError:
        print(f"Port {args.port} is already in use. Open the existing app, or use ./run.sh --port {args.port + 1}.")
        return 1
    print(f"Enarratio → http://127.0.0.1:{args.port}\nThe model warms up after the page opens. Ctrl-C stops the server.", flush=True)
    os.chdir(ROOT)
    os.execv(sys.executable, [sys.executable, "-m", "uvicorn", "enarratio.app:app", "--host", "127.0.0.1", "--port", str(args.port)])


if __name__ == "__main__":
    sys.exit(main())

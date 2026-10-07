"""Locations and read-only diagnostics for optional, separately licensed data."""
import os
from pathlib import Path
import sqlite3


def data_path(filename: str) -> Path:
    return (Path(os.environ.get("ENARRATIO_DATA_DIR", Path(__file__).resolve().parents[2] / "data")).expanduser() / filename).resolve()


def resource_status() -> dict:
    resources = {}
    for name, path, table in (
        ("passages", data_path("passages.db"), "work"),
        ("commentary", data_path("commentary.db"), "note"),
        ("quantities", Path(os.environ.get("ENARRATIO_QUANTITY_DB", data_path("morpheus-quantities.db"))).expanduser().resolve(), "morpheus"),
    ):
        status = "missing"
        if path.is_file():
            try:
                with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as conn:
                    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    status = "available" if table in tables else "incompatible"
            except (sqlite3.Error, ValueError):
                status = "unreadable"
        resources[name] = {"status": status}
    return resources

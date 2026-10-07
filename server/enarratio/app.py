"""HTTP API for Enarratio.

Deliberately small. All the intelligence lives in the pipeline; this layer exists so the
browser can reach it. It binds to localhost only -- the analysis runs on the reader's own
machine and nothing about a pasted passage leaves it.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from threading import Lock, Thread

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import __version__
from .constructions import CONSTRUCTION_INDEX
from .cases import CASE_USE_INDEX
from .clauses import CLAUSE_INDEX
from .pipeline import MODEL_NAME, analyse, load_nlp
from .storage import resource_status

_model = {"status": "warming", "message": "Loading the local Latin model. Please wait."}
_analysis_lock = Lock()


def _warm() -> None:
    try:
        with _analysis_lock:
            load_nlp()
        _model.update(status="ready", message="Local analysis ready; no internet required.")
    except Exception:
        logging.exception("Could not load the local Latin model")
        _model.update(status="error", message="The local model could not load. Run ./run.sh --setup while online, then restart. See the terminal for details.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _model.update(status="warming", message="Loading the local Latin model. Please wait.")
    Thread(target=_warm, daemon=True, name="latin-model").start()
    yield


app = FastAPI(title="Enarratio", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


@app.get("/api/health")
def health() -> dict:
    return {**_model, "version": __version__, "model": MODEL_NAME, "resources": resource_status()}


@app.get("/api/constructions")
def constructions() -> dict:
    """The catalogue of constructions the analyser can recognise."""
    return {
        "constructions": [
            {"key": k, "name": n, "grammarRef": r}
            for k, (n, r) in sorted((CONSTRUCTION_INDEX | CASE_USE_INDEX | CLAUSE_INDEX).items(), key=lambda kv: kv[1][0])
        ]
    }


@app.post("/api/analyse")
def analyse_text(req: AnalyseRequest) -> dict:
    if not req.text.strip():
        raise HTTPException(422, "Please enter a Latin passage.")
    if _model["status"] != "ready":
        raise HTTPException(503, _model["message"], headers={"Retry-After": "3"})
    # LatinCy and the cached SQLite quantity connection are shared between requests.
    with _analysis_lock:
        return analyse(req.text)


# A single origin works on any chosen port, with or without internet.
_dist = Path(__file__).resolve().parents[2] / "web" / "dist"
if (_dist / "index.html").is_file():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="reader")
else:
    @app.get("/")
    def missing_reader() -> dict:
        return {"message": "Build the reader with npm --prefix web run build, then restart using ./run.sh."}

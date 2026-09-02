"""HTTP API for Enarratio.

Deliberately small. All the intelligence lives in the pipeline; this layer exists so the
browser can reach it. It binds to localhost only -- the analysis runs on the reader's own
machine and nothing about a pasted passage leaves it.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import __version__
from .constructions import CONSTRUCTION_INDEX
from .pipeline import MODEL_NAME, analyse, load_nlp

app = FastAPI(title="Enarratio", version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


@app.on_event("startup")
def _warm() -> None:
    """Load the model at startup so the first analysis is not the slow one."""
    load_nlp()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "model": MODEL_NAME}


@app.get("/api/constructions")
def constructions() -> dict:
    """The catalogue of constructions the analyser can recognise."""
    return {
        "constructions": [
            {"key": k, "name": n, "grammarRef": r}
            for k, (n, r) in sorted(CONSTRUCTION_INDEX.items(), key=lambda kv: kv[1][0])
        ]
    }


@app.post("/api/analyse")
def analyse_text(req: AnalyseRequest) -> dict:
    return analyse(req.text)

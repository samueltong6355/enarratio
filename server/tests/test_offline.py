import sqlite3
from fastapi.testclient import TestClient
from enarratio import app as api
from enarratio.storage import data_path, resource_status


def test_missing_databases_do_not_create_files(tmp_path, monkeypatch):
    monkeypatch.setenv("ENARRATIO_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("ENARRATIO_QUANTITY_DB", raising=False)
    assert all(r["status"] == "missing" for r in resource_status().values())
    assert not list(tmp_path.iterdir())


def test_corrupt_and_incompatible_databases(tmp_path, monkeypatch):
    monkeypatch.setenv("ENARRATIO_DATA_DIR", str(tmp_path))
    (tmp_path / "passages.db").write_text("not a database")
    with sqlite3.connect(tmp_path / "commentary.db") as conn:
        conn.execute("CREATE TABLE unexpected (id INTEGER)")
    result = resource_status()
    assert result["passages"]["status"] == "unreadable"
    assert result["commentary"]["status"] == "incompatible"


def test_configured_paths(tmp_path, monkeypatch):
    from enarratio.identify import index_db
    from enarratio.commentary import commentary_db
    monkeypatch.setenv("ENARRATIO_DATA_DIR", str(tmp_path))
    assert index_db() == data_path("passages.db") == tmp_path / "passages.db"
    assert commentary_db() == tmp_path / "commentary.db"


def test_health_and_warming_response(monkeypatch):
    monkeypatch.setitem(api._model, "status", "warming")
    client = TestClient(api.app)
    assert client.get("/api/health").json()["status"] == "warming"
    response = client.post("/api/analyse", json={"text": "Arma virumque cano"})
    assert response.status_code == 503
    assert response.headers["retry-after"] == "3"


def test_request_validation_and_ready_route(monkeypatch):
    monkeypatch.setitem(api._model, "status", "ready")
    monkeypatch.setattr(api, "analyse", lambda text: {"text": text})
    client = TestClient(api.app)
    for text in ["", "   ", "x" * 20001]:
        assert client.post("/api/analyse", json={"text": text}).status_code == 422
    assert client.post("/api/analyse", json={"text": "Salve"}).json() == {"text": "Salve"}


def test_model_failure_is_explained(monkeypatch):
    def fail():
        raise OSError("model missing")
    monkeypatch.setattr(api, "load_nlp", fail)
    monkeypatch.setattr(api, "_model", {})
    api._warm()
    assert api.health()["status"] == "error"
    assert "--setup" in api.health()["message"]


def test_complete_construction_catalogue():
    keys = {c["key"] for c in api.constructions()["constructions"]}
    assert {"ablative_of_price", "dative_direction", "conditional_clause", "gerund_dative"} <= keys


def test_corrupt_enrichment_preserves_core(monkeypatch):
    from enarratio import pipeline
    def broken(*args):
        raise sqlite3.DatabaseError("bad data")
    monkeypatch.setattr(pipeline, "identify", broken)
    monkeypatch.setattr(pipeline, "_maybe_scan", broken)
    result = pipeline.analyse("Puella rosam amat.")
    assert result["tokens"] and result["gate"]["isLatin"]
    assert result["passage"] is None and result["scansion"] is None
    assert len(result["warnings"]) == 2

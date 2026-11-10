from fastapi.testclient import TestClient

from app.api.main import app
from app.core.config import get_settings


def client() -> TestClient:
    get_settings.cache_clear()
    return TestClient(app, raise_server_exceptions=False)


def test_healthz(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ML_CONSUMER_ENABLED", "false")
    with client() as c:
        assert c.get("/healthz").json() == {"status": "ok"}


def test_interactive_docs_are_not_exposed(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ML_CONSUMER_ENABLED", "false")
    with client() as c:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert c.get(path).status_code == 404


def test_readyz_reports_unavailable_without_leaking_connection_details(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ML_CONSUMER_ENABLED", "false")
    monkeypatch.setenv("ML_DATABASE_URL", "postgresql://secret-user:secret-pw@127.0.0.1:1/none")
    with client() as c:
        response = c.get("/readyz")
    assert response.status_code == 503
    assert "secret" not in response.text

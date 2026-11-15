import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.agent.api import AgentService
from app.agent.limits import DailyBudget, RunLimiter
from app.agent.llm import Turn
from app.api.main import app
from app.core.config import get_settings
from tests.agent_helpers import FixedTools, PlayedModel, call

SECRET = "test-secret-that-is-at-least-32-characters"
URL = "/api/v1/agent/runs"
QUESTION = {"question": "Is 0.06 fair for sertraline 50 mg?"}


def token(scope: str = "agent:run", secret: str = SECRET, **extra: object) -> str:
    claims = {"sub": "buyer-1", "scope": scope, "exp": int(time.time()) + 60, **extra}
    return jwt.encode(claims, secret, algorithm="HS256")


def auth(t: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {t or token()}"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ML_CONSUMER_ENABLED", "false")
    monkeypatch.setenv("DEV_JWT_SECRET", SECRET)
    monkeypatch.delenv("BENCHLINE_LLM_MODEL", raising=False)
    get_settings.cache_clear()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    get_settings.cache_clear()


def use(model: PlayedModel | None, per_hour: int = 20, budget: float = 1.0) -> None:
    app.state.agent = AgentService(model, FixedTools(), RunLimiter(per_hour), DailyBudget(budget))


def answering() -> PlayedModel:
    return PlayedModel(Turn("Checking.", [call("get_benchmark", drug="sertraline 50 mg")]), Turn("Fair."))


def parse(body: str) -> list[tuple[str, str]]:
    events = []
    for block in body.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if not line.startswith(":"))
        events.append((fields["event"], fields["data"]))
    return events


def test_streams_server_sent_events(client: TestClient) -> None:
    use(answering())
    response = client.post(URL, json=QUESTION, headers=auth())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache, no-transform"
    events = parse(response.text)
    assert [e for e, _ in events] == ["run", "thinking", "tool_call", "tool_result", "answer", "done"]
    assert response.text.startswith("id: 0\nevent: run\n")


@pytest.mark.parametrize(("headers", "status"), [
    ({}, 401),
    ({"Authorization": "Basic abc"}, 401),
    ({"Authorization": f"Bearer {token(secret='another-secret-that-is-32-characters-long')}"}, 401),
    ({"Authorization": f"Bearer {token(exp=int(time.time()) - 10)}"}, 401),
    ({"Authorization": f"Bearer {token(scope='prices:write insights:read')}"}, 403),
])
def test_refuses_without_a_valid_token_and_scope(client: TestClient, headers: dict[str, str], status: int) -> None:
    use(answering())
    response = client.post(URL, json=QUESTION, headers=headers)
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"


def test_question_is_validated(client: TestClient) -> None:
    use(answering())
    assert client.post(URL, json={"question": "hi"}, headers=auth()).status_code == 422
    assert client.post(URL, json={"question": "x" * 501}, headers=auth()).status_code == 422


def test_without_a_model_the_agent_says_it_is_not_set_up(client: TestClient) -> None:
    use(None)
    response = client.post(URL, json=QUESTION, headers=auth())
    assert response.status_code == 503
    assert response.json()["detail"] == "The assistant is not set up on this server."


def test_rate_limit_per_user(client: TestClient) -> None:
    use(PlayedModel(Turn("One."), Turn("Two.")), per_hour=1)
    assert client.post(URL, json=QUESTION, headers=auth()).status_code == 200
    second = client.post(URL, json=QUESTION, headers=auth())
    assert second.status_code == 429
    assert int(second.headers["retry-after"]) > 0


def test_daily_budget_stops_new_runs(client: TestClient) -> None:
    use(PlayedModel(Turn("Pricey.", [], cost_usd=0.5)), budget=0.5)
    assert client.post(URL, json=QUESTION, headers=auth()).status_code == 200
    blocked = client.post(URL, json=QUESTION, headers=auth())
    assert blocked.status_code == 503
    assert "budget" in blocked.json()["detail"]


def test_cors_allows_only_configured_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    preflight = {"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"}
    monkeypatch.setenv("ML_CONSUMER_ENABLED", "false")
    with TestClient(app) as c:
        response = c.options(URL, headers=preflight)
    assert "access-control-allow-origin" not in response.headers

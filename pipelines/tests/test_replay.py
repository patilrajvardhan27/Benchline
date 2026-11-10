import json
from pathlib import Path

import httpx
import pandas as pd
import pytest

from benchline_pipelines.gold.replay import BATCH_SIZE, replay, select_weeks
from benchline_pipelines.silver.build import build_silver

FIXTURE = Path(__file__).parent / "fixtures" / "nadac_sample.csv"


@pytest.fixture
def silver_file(tmp_path: Path) -> Path:
    build_silver([FIXTURE], tmp_path)
    return tmp_path / "nadac.parquet"


def _client(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler, headers={"Authorization": "Bearer t"})


def test_posts_weeks_in_date_order(silver_file: Path) -> None:
    seen: list[list[str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        rows = json.loads(request.content)["pricePoints"]
        seen.append(sorted({r["asOfDate"] for r in rows}))
        return httpx.Response(202, json={"accepted": len(rows), "duplicates": 0})

    result = replay(silver_file, "http://api", "t", client=_client(httpx.MockTransport(handler)))

    flat = [d for call in seen for d in call]
    assert flat == sorted(flat)
    assert all(len(call) == 1 for call in seen)  # one publication week per request
    assert result.weeks == len(seen)
    assert result.accepted == result.sent == 4


def test_payload_matches_the_api_contract(silver_file: Path) -> None:
    captured: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.extend(json.loads(request.content)["pricePoints"])
        return httpx.Response(202, json={"accepted": 1, "duplicates": 0})

    replay(silver_file, "http://api/", "t", client=_client(httpx.MockTransport(handler)))
    row = captured[0]
    assert set(row) == {
        "ndc11", "description", "otc", "source",
        "unitPrice", "pricingUnit", "effectiveDate", "asOfDate",
    }
    assert isinstance(row["unitPrice"], str)  # decimal string, never a float
    assert row["source"] == "NADAC"


def test_retries_transient_errors_then_succeeds(
    silver_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("benchline_pipelines.gold.replay.time.sleep", lambda _s: None)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        rows = json.loads(request.content)["pricePoints"]
        return httpx.Response(202, json={"accepted": len(rows), "duplicates": 0})

    result = replay(silver_file, "http://api", "t", client=_client(httpx.MockTransport(handler)))
    assert result.accepted == 4


def test_client_errors_are_not_retried_and_do_not_echo_the_body(silver_file: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"detail": "The request body failed validation"})

    with pytest.raises(RuntimeError, match="400") as exc:
        replay(silver_file, "http://api", "t", client=_client(httpx.MockTransport(handler)))
    assert "00000000001" not in str(exc.value)


def test_select_weeks_takes_the_latest_n() -> None:
    df = pd.DataFrame(
        {
            "ndc11": ["1", "1", "2", "3"],
            "effective_date": ["2026-10-01", "2026-10-22", "2026-10-29", "2026-10-29"],
            "as_of_date": ["2026-10-07", "2026-10-28", "2026-11-04", "2026-11-04"],
        }
    )
    window = select_weeks(df, 2, None)
    assert sorted(window["as_of_date"].unique()) == ["2026-10-27", "2026-10-28", "2026-11-04"]
    assert list(select_weeks(df, None, "2026-11-01")["as_of_date"].unique()) == [
        "2026-11-03",  # baseline for NDC 1, dated the day before the window
        "2026-11-04",
    ]


def test_truncated_run_starts_from_a_baseline() -> None:
    df = pd.DataFrame(
        {
            "ndc11": ["1", "1", "2", "1"],
            "effective_date": ["2026-01-01", "2026-02-01", "2026-01-01", "2026-03-01"],
            "as_of_date": ["2026-01-07", "2026-02-04", "2026-01-07", "2026-03-04"],
        }
    )
    picked = select_weeks(df, 1, None)

    baseline = picked[picked["as_of_date"] == "2026-03-03"]
    assert sorted(zip(baseline["ndc11"], baseline["effective_date"], strict=True)) == [
        ("1", "2026-02-01"),  # the rate in force before the window, not the older one
        ("2", "2026-01-01"),
    ]
    assert list(picked[picked["as_of_date"] == "2026-03-04"]["effective_date"]) == ["2026-03-01"]


def test_full_run_needs_no_baseline() -> None:
    df = pd.DataFrame({"ndc11": ["1", "1"], "as_of_date": ["2026-01-07", "2026-02-04"]})
    assert len(select_weeks(df, None, None)) == 2


def test_batch_size_matches_the_api_limit() -> None:
    assert BATCH_SIZE == 1000

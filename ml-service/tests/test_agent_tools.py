import json
import re
from typing import Any

import pytest

from app.agent.record import DEMO_DIR
from app.agent.results import word_pattern
from app.agent.tools import TOOL_SPECS, query_words, run_tool
from app.agent.tools_snapshot import SnapshotTools


@pytest.fixture(scope="module")
def tools() -> SnapshotTools:
    return SnapshotTools(DEMO_DIR)


def matches(query: str, name: str) -> bool:
    return all(re.search(word_pattern(w), name) for w in query_words(query))


def test_query_words_split_numbers_from_units() -> None:
    assert query_words("Sertraline 50mg tab") == ["SERTRALINE", "50", "MG", "TAB"]


def test_numbers_match_whole_and_words_match_a_prefix() -> None:
    assert matches("sertraline 50 tab", "SERTRALINE HCL 50 MG TABLET")
    assert not matches("sertraline 50", "SERTRALINE HCL 150 MG TABLET")
    assert not matches("tab", "ACETAB 5 MG")


def test_specs_are_plain_json_schema_without_titles() -> None:
    names = [s["function"]["name"] for s in TOOL_SPECS]
    assert names == ["get_benchmark", "list_anomalies", "find_equivalents"]
    assert "title" not in json.dumps(TOOL_SPECS)


def test_benchmark_from_the_snapshot(tools: SnapshotTools) -> None:
    result = tools.get_benchmark("sertraline 50 mg")
    assert result.ok and result.data["group"] == "SERTRALINE HCL 50 MG TABLET"
    prices: dict[str, Any] = result.data["unit_price_usd"]
    assert [float(prices[k]) for k in ("p10", "p25", "median", "p75", "p90")] == sorted(
        float(prices[k]) for k in ("p10", "p25", "median", "p75", "p90"))
    assert all(c.href.startswith("/items/ndc-") for c in result.citations)


def test_equivalents_are_cheapest_first(tools: SnapshotTools) -> None:
    result = tools.find_equivalents("omeprazole 20")
    prices = [float(p["latest_price"]) for p in result.data["products"]]
    assert prices == sorted(prices) and result.data["total_products"] >= len(prices)


def test_anomalies_filter_by_drug_and_limit(tools: SnapshotTools) -> None:
    result = tools.list_anomalies("metoprolol", 3)
    assert len(result.data["anomalies"]) == 3
    assert {a["group"] for a in result.data["anomalies"]} == {"METOPROLOL SUCC ER 25 MG TAB"}


def test_unknown_drug_is_a_normal_answer_not_an_error(tools: SnapshotTools) -> None:
    result = tools.get_benchmark("unobtainium 5 mg")
    assert result.ok and result.data == {"found": False}


def test_arguments_are_checked_before_any_lookup(tools: SnapshotTools) -> None:
    assert not run_tool(tools, "list_anomalies", '{"limit": 500}').ok
    assert not run_tool(tools, "get_benchmark", "not json").ok
    assert run_tool(tools, "list_anomalies", "{}").ok

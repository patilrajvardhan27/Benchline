"""The demo and the browser tests replay recorded streams. These fail if the server's output drifts from them."""

import asyncio
import json

import pytest

from app.agent.record import DEMO_DIR, RECORDINGS, header, record


@pytest.mark.parametrize("name", list(RECORDINGS))
def test_committed_recording_matches_what_the_server_sends_today(name: str) -> None:
    question, scripted = RECORDINGS[name]
    expected = header("scripted") + asyncio.run(record(question, scripted()))
    committed = (DEMO_DIR / "agent" / f"{name}.sse").read_text()
    assert committed == expected, "re-record with: uv run python -m app.agent.record"


def test_index_lists_every_recording() -> None:
    index = json.loads((DEMO_DIR / "agent" / "index.json").read_text())
    assert [(r["id"], r["question"]) for r in index] == [(k, q) for k, (q, _) in RECORDINGS.items()]


def test_every_recording_ends_with_done() -> None:
    for name in RECORDINGS:
        text = (DEMO_DIR / "agent" / f"{name}.sse").read_text()
        assert text.rstrip().split("\n\n")[-1].startswith(f"id: {text.count('event: ') - 1}\nevent: done")

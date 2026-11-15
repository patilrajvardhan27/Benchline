import datetime as dt
import hashlib
from collections.abc import Iterator
from pathlib import Path

import boto3
import httpx
import pytest
import respx
from moto import mock_aws

from benchline_pipelines.__main__ import main
from benchline_pipelines.bronze.fetch import fetch_nadac
from benchline_pipelines.bronze.store import BronzeStore, LocalStore, S3Store, open_store
from benchline_pipelines.sources import nadac

FIXTURE = Path(__file__).parent / "fixtures" / "nadac_sample.csv"
DOWNLOAD = "https://download.example/nadac_2026.csv"
TODAY = dt.date(2026, 11, 10)


@pytest.fixture
def s3(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key, value in {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test",
                       "AWS_DEFAULT_REGION": "us-east-1"}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    with mock_aws():
        yield


@pytest.fixture
def cms(monkeypatch: pytest.MonkeyPatch) -> Iterator[respx.MockRouter]:
    monkeypatch.setattr(nadac, "download_url", lambda client, year: DOWNLOAD)
    with respx.mock(assert_all_called=False) as router:
        router.get(DOWNLOAD).mock(return_value=httpx.Response(200, content=FIXTURE.read_bytes()))
        yield router


def test_fetch_puts_the_raw_file_in_the_bucket_unchanged(s3: None, cms: respx.MockRouter) -> None:
    keys = fetch_nadac([2026], S3Store("benchline-bronze"), today=TODAY)

    assert keys == ["nadac/2026-11-10/nadac_2026.csv"]
    obj = boto3.client("s3").get_object(Bucket="benchline-bronze", Key=keys[0])
    body = obj["Body"].read()
    assert body == FIXTURE.read_bytes()
    assert obj["Metadata"]["sha256"] == hashlib.sha256(body).hexdigest()
    assert obj["Metadata"]["source-url"] == DOWNLOAD


def test_fetch_skips_a_file_already_stored(s3: None, cms: respx.MockRouter) -> None:
    store = S3Store("benchline-bronze")
    fetch_nadac([2026], store, today=TODAY)
    fetch_nadac([2026], store, today=TODAY)
    assert cms.calls.call_count == 1


def test_failed_download_stores_nothing(s3: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nadac, "download_url", lambda client, year: DOWNLOAD)
    store = S3Store("benchline-bronze")
    with respx.mock() as router:
        router.get(DOWNLOAD).mock(return_value=httpx.Response(503))
        with pytest.raises(httpx.HTTPStatusError):
            fetch_nadac([2026], store, today=TODAY)
    assert store.runs() == []


@pytest.mark.parametrize("kind", ["local", "s3"])
def test_runs_and_files_work_the_same_for_both_stores(kind: str, tmp_path: Path, s3: None,
                                                      cms: respx.MockRouter) -> None:
    store: BronzeStore = LocalStore(tmp_path / "bronze") if kind == "local" else S3Store("benchline-bronze")
    fetch_nadac([2026], store, today=TODAY)
    fetch_nadac([2026], store, today=dt.date(2026, 11, 17))

    assert store.runs() == ["2026-11-10", "2026-11-17"]
    files = store.files("2026-11-17", tmp_path / "cache")
    assert [f.name for f in files] == ["nadac_2026.csv"]
    assert files[0].read_bytes() == FIXTURE.read_bytes()


def test_open_store_picks_by_scheme(tmp_path: Path, s3: None) -> None:
    assert isinstance(open_store("s3://benchline-bronze"), S3Store)
    assert isinstance(open_store(tmp_path), LocalStore)


def test_fetch_then_silver_from_the_bucket(tmp_path: Path, s3: None, cms: respx.MockRouter,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BENCHLINE_BRONZE_URI", "s3://benchline-bronze")
    main(["--data-dir", str(tmp_path), "fetch", "--years", "2026"])
    main(["--data-dir", str(tmp_path), "silver"])

    assert (tmp_path / "silver" / "nadac.parquet").exists()
    assert not (tmp_path / "bronze").exists()  # the raw file went to the bucket, not to disk

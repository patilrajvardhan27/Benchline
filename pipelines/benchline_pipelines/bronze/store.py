"""Where bronze files live: a local folder, or a bucket behind the S3 API (MinIO locally, S3 in the cloud).

Keys look like nadac/<download date>/nadac_<year>.csv in both, so a run moves between them unchanged.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import boto3
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

PREFIX = "nadac"


class BronzeStore(Protocol):
    def has(self, key: str) -> bool: ...
    def put(self, key: str, source: Path, metadata: dict[str, str]) -> None: ...
    def runs(self) -> list[str]: ...
    def files(self, run: str, cache: Path) -> list[Path]: ...


class LocalStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def has(self, key: str) -> bool:
        return (self.root / key).exists()

    def put(self, key: str, source: Path, metadata: dict[str, str]) -> None:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, target)

    def runs(self) -> list[str]:
        return sorted(p.name for p in (self.root / PREFIX).glob("*") if p.is_dir())

    def files(self, run: str, cache: Path) -> list[Path]:
        return sorted((self.root / PREFIX / run).glob("nadac_*.csv"))


class S3Store:
    """Endpoint and credentials come from the standard AWS variables (AWS_ENDPOINT_URL for MinIO)."""

    def __init__(self, bucket: str, client: S3Client | None = None) -> None:
        self.bucket = bucket
        self.client: S3Client = client or boto3.client("s3")
        self._bucket_checked = False

    def has(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NoSuchBucket"):
                return False
            raise
        return True

    def put(self, key: str, source: Path, metadata: dict[str, str]) -> None:
        self._ensure_bucket()
        self.client.upload_file(str(source), self.bucket, key,
                                ExtraArgs={"Metadata": metadata, "ContentType": "text/csv"})
        source.unlink()

    def runs(self) -> list[str]:
        pages = self.client.get_paginator("list_objects_v2").paginate(
            Bucket=self.bucket, Prefix=f"{PREFIX}/", Delimiter="/")
        try:
            return sorted(p["Prefix"].split("/")[1] for page in pages for p in page.get("CommonPrefixes", []))
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchBucket":
                return []  # nothing fetched yet
            raise

    def files(self, run: str, cache: Path) -> list[Path]:
        """Downloads the run into cache once; silver reads local files."""
        local: list[Path] = []
        pages = self.client.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=f"{PREFIX}/{run}/")
        for obj in (o for page in pages for o in page.get("Contents", [])):
            name = obj["Key"].rsplit("/", 1)[-1]
            if not (name.startswith("nadac_") and name.endswith(".csv")):
                continue
            target = cache / run / name
            if not target.exists() or target.stat().st_size != obj["Size"]:
                target.parent.mkdir(parents=True, exist_ok=True)
                self.client.download_file(self.bucket, obj["Key"], str(target))
            local.append(target)
        return sorted(local)

    def _ensure_bucket(self) -> None:
        if self._bucket_checked:
            return
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)
        self._bucket_checked = True


def open_store(location: str | Path) -> BronzeStore:
    """s3://bucket for object storage, anything else is a folder."""
    text = str(location)
    if text.startswith("s3://"):
        return S3Store(text.removeprefix("s3://").strip("/"))
    return LocalStore(Path(text))


def default_location(data_dir: Path) -> str:
    return os.environ.get("BENCHLINE_BRONZE_URI") or str(data_dir / "bronze")

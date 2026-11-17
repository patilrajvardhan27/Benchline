"""Where the CMS NADAC files live and how their columns map to ours."""

from __future__ import annotations

import httpx

# Dataset ids on data.medicaid.gov, one per calendar year.
# https://data.medicaid.gov/dataset/fbb83258-11c7-47f5-8b18-5f8e79f7e704 is 2026.
DATASET_IDS: dict[int, str] = {
    2013: "1fe73992-cbfd-5109-97bc-dee8b33fdcff",
    2014: "ba0c3734-8012-549a-8f50-2ff389d0e0ef",
    2015: "4d7af295-2132-55a8-b40c-d6630061f3e8",
    2016: "7656fc17-f1b4-566b-9a2d-c4a4f2ac7ae1",
    2017: "1c5d0fc9-693a-534a-8240-4627d9362b0d",
    2018: "8de1b213-73c5-552b-b84e-ac795f34d056",
    2019: "76a1984a-6d69-5e4d-86c8-65eb31f0506d",
    2020: "c933dc16-7de9-52b6-8971-4b75992673e0",
    2021: "d5eaf378-dcef-5779-83de-acdd8347d68e",
    2022: "dfa2ab14-06c2-457a-9e36-5cb6d80f8d93",
    2023: "4a00010a-132b-4e4d-a611-543c9521280f",
    2024: "99315a95-37ac-4eee-946a-3c523b4c481e",
    2025: "f38d0706-1239-442c-a3cc-40ef1b686ac0",
    2026: "fbb83258-11c7-47f5-8b18-5f8e79f7e704",
}

METASTORE = "https://data.medicaid.gov/api/1/metastore/schemas/dataset/items/{id}?show-reference-ids"

# CSV header (lowercased, underscores) to the column names used from silver on.
COLUMN_MAP: dict[str, str] = {
    "ndc_description": "description",
    "ndc": "ndc",
    "nadac_per_unit": "unit_price",
    "effective_date": "effective_date",
    "pricing_unit": "pricing_unit",
    "otc": "otc",
    "as_of_date": "as_of_date",
}


def download_url(client: httpx.Client, year: int) -> str:
    """The download link changes every publication, so ask the metastore for it."""
    try:
        dataset_id = DATASET_IDS[year]
    except KeyError as exc:
        known = ", ".join(str(y) for y in sorted(DATASET_IDS))
        raise ValueError(f"No NADAC dataset registered for {year}. Known years: {known}") from exc
    response = client.get(METASTORE.format(id=dataset_id), timeout=30)
    response.raise_for_status()
    distributions = response.json().get("distribution", [])
    for dist in distributions:
        url = dist.get("data", {}).get("downloadURL")
        if url:
            return str(url)
    raise RuntimeError(f"Dataset {dataset_id} has no downloadable distribution")

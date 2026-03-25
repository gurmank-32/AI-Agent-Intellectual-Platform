from __future__ import annotations

import csv
import hashlib
import sys
from datetime import date
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.client import get_db


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


STATE_NAME_TO_CODE: dict[str, str] = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}

CITY_TO_STATE_CODE: dict[str, str] = {
    "Los Angeles": "CA",
    "San Francisco": "CA",
    "San Diego": "CA",
    "New York City": "NY",
    "Dallas": "TX",
    "Houston": "TX",
    "Austin": "TX",
    "San Antonio": "TX",
    "Fort Worth": "TX",
}


def _get_federal_jurisdiction_id() -> int:
    db = get_db()
    res = (
        db.table("jurisdictions")
        .select("id")
        .eq("type", "federal")
        .eq("name", "Federal Government")
        .limit(1)
        .execute()
    )
    if not res.data:
        raise RuntimeError(
            "Federal jurisdiction row is missing. Run scripts/seed_jurisdictions.py first."
        )
    return int(res.data[0]["id"])


def _get_state_jurisdiction_id(state_code: str) -> int:
    db = get_db()
    res = (
        db.table("jurisdictions")
        .select("id")
        .eq("type", "state")
        .eq("state_code", state_code)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise RuntimeError(
            f"Unknown state_code '{state_code}'. Run scripts/seed_jurisdictions.py first."
        )
    return int(res.data[0]["id"])


def _resolve_jurisdiction_id(category: str, city_name: str) -> int:
    kind = (category or "").strip().lower()
    label = (city_name or "").strip()

    if kind == "federal":
        return _get_federal_jurisdiction_id()

    if kind == "state":
        # Expect "California-Statewide" style. Some rows may omit the dash.
        state_part = label.split("-", 1)[0].strip()
        state_part = state_part.replace("NewYork", "New York")
        state_code = STATE_NAME_TO_CODE.get(state_part)
        if not state_code:
            raise RuntimeError(f"Cannot map state name '{state_part}' to a state code.")
        return _get_state_jurisdiction_id(state_code)

    if kind == "city":
        # Prefer an actual city jurisdiction if present; otherwise fall back to state.
        db = get_db()
        city_res = (
            db.table("jurisdictions")
            .select("id")
            .eq("type", "city")
            .eq("name", label)
            .limit(1)
            .execute()
        )
        if city_res.data:
            return int(city_res.data[0]["id"])

        state_code = CITY_TO_STATE_CODE.get(label)
        if not state_code:
            raise RuntimeError(
                f"City '{label}' not found in jurisdictions and no fallback mapping exists."
            )
        return _get_state_jurisdiction_id(state_code)

    raise RuntimeError(f"Unknown category '{category}'. Expected Federal/State/City.")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "data" / "seeds" / "sources.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing seed file: {csv_path}")

    db = get_db()

    loaded = 0
    skipped = 0

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = (row.get("hyperlink") or "").strip()
            if not url:
                continue

            category = (row.get("category") or "").strip()
            city_name = (row.get("city_name") or "").strip()
            law_name = (row.get("law_name") or "").strip()
            # Keep non-empty seed text so vector search has at least some content.
            content = f"{law_name} {url}".strip()
            content_hash = _sha256(content or url)

            # Idempotency: skip if there is already an `is_current` row with the same content_hash.
            existing_current_res = (
                db.table("regulations")
                .select("id,content_hash,version")
                .eq("url", url)
                .eq("is_current", True)
                .limit(1)
                .execute()
            )
            existing_current = (
                existing_current_res.data[0] if existing_current_res.data else None
            )
            if existing_current:
                existing_hash = str(existing_current.get("content_hash") or "")
                if existing_hash == content_hash:
                    skipped += 1
                    continue

            jurisdiction_id = _resolve_jurisdiction_id(category=category, city_name=city_name)

            payload: dict[str, Any] = {
                "jurisdiction_id": jurisdiction_id,
                "domain": "housing",
                "category": category or "General",
                "source_name": law_name or "Unknown",
                "url": url,
                "content": content,
                "content_hash": content_hash,
                "version": 1,
                "is_current": True,
                "effective_date": None,
            }

            if existing_current:
                payload["version"] = int(existing_current.get("version") or 1) + 1
                db.table("regulations").update({"is_current": False}).eq(
                    "id", int(existing_current["id"])
                ).execute()

            db.table("regulations").insert([payload]).execute()
            loaded += 1

    print(f"Loaded {loaded} regulations, skipped {skipped} duplicates")


if __name__ == "__main__":
    main()


from __future__ import annotations

import csv
import hashlib
import io
import logging
import re
from pathlib import Path
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

from core.rag.vector_store import RegulationVectorStore
from db.client import get_db
from db.models import Regulation

logger = logging.getLogger(__name__)

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


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _get_state_id_by_code(db: Any, state_code: str) -> int:
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
            f"State with state_code='{state_code}' not found. Run scripts/seed_jurisdictions.py first."
        )
    return int(res.data[0]["id"])


def _get_federal_id(db: Any) -> int:
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
            "Federal jurisdiction row missing. Run scripts/seed_jurisdictions.py first."
        )
    return int(res.data[0]["id"])


def _resolve_jurisdiction_id(db: Any, category: str, city_name: str) -> int:
    kind = (category or "").strip().lower()
    label = (city_name or "").strip()

    if kind == "federal":
        return _get_federal_id(db)

    if kind == "state":
        state_part = label.split("-", 1)[0].strip()
        state_part = state_part.replace("NewYork", "New York")
        state_code = STATE_NAME_TO_CODE.get(state_part)
        if not state_code:
            raise RuntimeError(f"Cannot map state name '{state_part}' to a state code.")
        return _get_state_id_by_code(db, state_code)

    if kind == "city":
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
        return _get_state_id_by_code(db, state_code)

    raise RuntimeError(f"Unknown category '{category}'. Expected Federal/State/City.")


# ---------------------------------------------------------------------------
# CSV loader (used by settings page "Load regulations from CSV")
# ---------------------------------------------------------------------------


def load_regulations_from_csv(csv_path: Path) -> dict[str, Any]:
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

            category = (row.get("category") or "").strip()
            city_name = (row.get("city_name") or "").strip()
            law_name = (row.get("law_name") or "").strip()

            jurisdiction_id = _resolve_jurisdiction_id(db, category, city_name)

            content = f"{law_name} {url}".strip()
            content_hash = _sha256(content or url)

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
                existing_hash = str(existing_current.get("content_hash") or "")
                if existing_hash == content_hash:
                    skipped += 1
                    continue

                db.table("regulations").update({"is_current": False}).eq(
                    "id", int(existing_current["id"])
                ).execute()
                payload["version"] = int(existing_current.get("version") or 1) + 1

            db.table("regulations").insert([payload]).execute()
            loaded += 1

    return {"loaded": loaded, "skipped": skipped}


# ---------------------------------------------------------------------------
# Vector-index helpers (used by settings page)
# ---------------------------------------------------------------------------


def get_unindexed_regulations() -> list[dict[str, Any]]:
    db = get_db()

    embeddings = db.table("regulation_embeddings").select("regulation_id").execute()
    embedded_ids = {int(row["regulation_id"]) for row in (embeddings.data or [])}

    regs_res = (
        db.table("regulations")
        .select("id,content,source_name,url,domain,category,jurisdiction_id")
        .eq("is_current", True)
        .execute()
    )
    docs: list[dict[str, Any]] = []
    for row in regs_res.data or []:
        rid = int(row["id"])
        if rid in embedded_ids:
            continue
        docs.append(
            {
                "text": row.get("content") or "",
                "regulation_id": rid,
                "metadata": {
                    "source_name": row.get("source_name"),
                    "url": row.get("url"),
                    "domain": row.get("domain"),
                    "category": row.get("category"),
                    "jurisdiction_id": row.get("jurisdiction_id"),
                },
            }
        )
    return docs


def initialize_vector_index() -> dict[str, Any]:
    docs = get_unindexed_regulations()
    store = RegulationVectorStore()
    if docs:
        store.add_documents(docs)
    return {"indexed_docs": len(docs)}


def get_indexing_status() -> list[dict[str, Any]]:
    db = get_db()
    states_res = (
        db.table("jurisdictions")
        .select("id,name")
        .eq("type", "state")
        .order("name")
        .execute()
    )
    state_rows = states_res.data or []

    regs_res = (
        db.table("regulations")
        .select("id,jurisdiction_id")
        .eq("is_current", True)
        .execute()
    )
    regs = regs_res.data or []
    regs_by_state: dict[int, list[int]] = {}
    for r in regs:
        jid = int(r["jurisdiction_id"])
        regs_by_state.setdefault(jid, []).append(int(r["id"]))

    embeddings_res = (
        db.table("regulation_embeddings").select("regulation_id").execute()
    )
    indexed_ids = {int(r["regulation_id"]) for r in (embeddings_res.data or [])}

    status: list[dict[str, Any]] = []
    for row in state_rows:
        state_id = int(row["id"])
        regulation_ids = regs_by_state.get(state_id, [])
        reg_count = len(regulation_ids)
        indexed_count = sum(1 for rid in regulation_ids if rid in indexed_ids)
        status.append(
            {
                "jurisdiction": row.get("name"),
                "jurisdiction_id": state_id,
                "regulation_count": reg_count,
                "indexed_count": indexed_count,
                "last_indexed_date": None,
            }
        )
    return status


def is_supabase_connected() -> bool:
    try:
        db = get_db()
        db.table("jurisdictions").select("id").limit(1).execute()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# RegulationScraper — web scraping + DB upsert + vector indexing
# ---------------------------------------------------------------------------


class RegulationScraper:
    def scrape_source(
        self,
        url: str,
        source_name: str,
        jurisdiction_id: int,
        domain: str,
        category: str,
    ) -> Regulation | None:
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code >= 400:
                logger.warning("HTTP %s for %s — skipping", resp.status_code, url)
                return None
        except Exception as exc:
            logger.warning("Unreachable URL %s: %s", url, exc)
            return None

        content_type = (resp.headers.get("content-type") or "").lower()
        is_pdf = url.lower().endswith(".pdf") or "application/pdf" in content_type

        if is_pdf:
            try:
                reader = PdfReader(io.BytesIO(resp.content))
                pages = [(page.extract_text() or "").strip() for page in reader.pages]
                text = "\n".join(p for p in pages if p)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed PDF extraction for %s: %s", url, exc)
                return None
        else:
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)

        text = re.sub(r"\n{3,}", "\n\n", (text or "")).strip()
        if len(text) < 120:
            logger.warning("Low-content page for %s (len=%s) — skipping", url, len(text))
            return None

        content_hash = _sha256(text)

        return Regulation(
            jurisdiction_id=int(jurisdiction_id),
            domain=domain or "housing",
            category=category or "General",
            source_name=source_name or "Unknown",
            url=url,
            content=text,
            content_hash=content_hash,
            version=1,
            is_current=True,
        )

    def scrape_all_sources(self) -> list[Regulation]:
        db = get_db()
        regs_res = (
            db.table("regulations")
            .select("url,source_name,jurisdiction_id,domain,category")
            .eq("is_current", True)
            .execute()
        )
        rows = regs_res.data or []
        results: list[Regulation] = []

        for row in rows:
            url = str(row.get("url") or "").strip()
            if not url:
                continue
            reg = self.scrape_source(
                url=url,
                source_name=str(row.get("source_name") or ""),
                jurisdiction_id=int(row.get("jurisdiction_id") or 0),
                domain=str(row.get("domain") or "housing"),
                category=str(row.get("category") or "General"),
            )
            if reg is not None:
                results.append(reg)

        return results

    def scrape_and_index(
        self, jurisdiction_id: int | None = None
    ) -> dict[str, Any]:
        db = get_db()

        query = (
            db.table("regulations")
            .select("id,url,source_name,jurisdiction_id,domain,category,content_hash,version")
            .eq("is_current", True)
        )
        if jurisdiction_id is not None:
            query = query.eq("jurisdiction_id", int(jurisdiction_id))

        regs_res = query.execute()
        rows = regs_res.data or []

        scraped = 0
        indexed = 0
        errors: list[str] = []
        new_docs: list[dict[str, Any]] = []

        for row in rows:
            url = str(row.get("url") or "").strip()
            if not url:
                continue

            reg = self.scrape_source(
                url=url,
                source_name=str(row.get("source_name") or ""),
                jurisdiction_id=int(row.get("jurisdiction_id") or 0),
                domain=str(row.get("domain") or "housing"),
                category=str(row.get("category") or "General"),
            )
            if reg is None:
                errors.append(f"Failed to scrape {url}")
                continue

            scraped += 1

            old_hash = str(row.get("content_hash") or "")
            if reg.content_hash == old_hash:
                continue

            old_id = int(row["id"])
            old_version = int(row.get("version") or 1)

            db.table("regulations").update({"is_current": False}).eq(
                "id", old_id
            ).execute()

            new_payload: dict[str, Any] = {
                "jurisdiction_id": reg.jurisdiction_id,
                "domain": reg.domain,
                "category": reg.category,
                "source_name": reg.source_name,
                "url": reg.url,
                "content": reg.content,
                "content_hash": reg.content_hash,
                "version": old_version + 1,
                "is_current": True,
                "effective_date": None,
            }
            ins = db.table("regulations").insert([new_payload]).execute()
            new_id: int | None = None
            if ins.data and ins.data[0].get("id") is not None:
                new_id = int(ins.data[0]["id"])
            else:
                lookup = (
                    db.table("regulations")
                    .select("id")
                    .eq("url", reg.url)
                    .eq("content_hash", reg.content_hash)
                    .eq("is_current", True)
                    .limit(1)
                    .execute()
                )
                if lookup.data:
                    new_id = int(lookup.data[0]["id"])

            if new_id is not None:
                new_docs.append(
                    {
                        "text": reg.content,
                        "regulation_id": new_id,
                        "metadata": {
                            "source_name": reg.source_name,
                            "url": reg.url,
                            "domain": reg.domain,
                            "category": reg.category,
                            "jurisdiction_id": reg.jurisdiction_id,
                        },
                    }
                )

        if new_docs:
            store = RegulationVectorStore()
            store.add_documents(new_docs)
            indexed = len(new_docs)

        return {"scraped": scraped, "indexed": indexed, "errors": errors}


# ---------------------------------------------------------------------------
# Backward-compatible ScraperService used by pages/5_settings.py
# ---------------------------------------------------------------------------


class ScraperService:
    def __init__(self) -> None:
        self._regulation_scraper = RegulationScraper()

    def load_regulations_from_csv(self, csv_path: Path) -> dict[str, Any]:
        return load_regulations_from_csv(csv_path)

    def initialize_vector_index(self) -> dict[str, Any]:
        return initialize_vector_index()

    def get_indexing_status(self) -> list[dict[str, Any]]:
        return get_indexing_status()

    def run_manual_scraper(self) -> dict[str, Any]:
        return self._regulation_scraper.scrape_and_index()

    def scrape_and_index(self, jurisdiction_id: int | None = None) -> dict[str, Any]:
        """Run scraping for all active sources (or a filtered jurisdiction) and index results."""
        return self._regulation_scraper.scrape_and_index(jurisdiction_id=jurisdiction_id)


scraper = ScraperService()
regulation_scraper = RegulationScraper()

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Callable, Optional

import requests
from pydantic import BaseModel

from config import settings
from core.llm.client import llm
from core.llm.prompts import UPDATE_SUMMARY_PROMPT
from db.client import get_db


class UpdateResult(BaseModel):
    source_name: str
    url: str
    category: str
    affected_jurisdiction_ids: list[int]
    update_summary: str
    detected_at: datetime


class UpdateChecker:
    def __init__(
        self,
        *,
        requests_get: Callable[..., Any] = requests.get,
        db_getter: Callable[[], Any] = get_db,
        llm_client: Any = llm,
        sha256_fn: Callable[[str], str] = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest(),
    ) -> None:
        self._requests_get = requests_get
        self._db_getter = db_getter
        self._llm = llm_client
        self._sha256_fn = sha256_fn

    def _jurisdiction_chain_ids(self, db: Any, start_id: int) -> list[int]:
        chain: list[int] = []
        current: Optional[int] = int(start_id)
        while current is not None:
            res = (
                db.table("jurisdictions")
                .select("id,parent_id")
                .eq("id", int(current))
                .limit(1)
                .execute()
            )
            if not res.data:
                break
            row = res.data[0]
            chain.append(int(row["id"]))
            parent_id = row.get("parent_id")
            current = int(parent_id) if parent_id is not None else None
        return chain

    def _fetch_url_content(self, url: str) -> Optional[str]:
        try:
            resp = self._requests_get(url, timeout=30)
            if resp.status_code >= 400:
                return None
            # Store as-is (HTML/text) so downstream clause/embedding can still work.
            return resp.text or ""
        except Exception:
            return None

    def _generate_update_summary(self, old_content: str, new_content: str) -> str:
        if not self._llm.is_ai_available():
            return "The regulation content changed. Please review the source link for the full details."

        user = f"Old content:\n{old_content}\n\nNew content:\n{new_content}"
        try:
            return self._llm.ask(system=UPDATE_SUMMARY_PROMPT, user=user, max_tokens=700)
        except Exception:
            return "The regulation content changed. Please review the source link for the full details."

    def _insert_regulation_version(
        self, *, db: Any, payload: dict[str, Any]
    ) -> int:
        ins = db.table("regulations").insert([payload]).execute()
        if ins.data and ins.data[0].get("id") is not None:
            return int(ins.data[0]["id"])

        # Fallback lookup: identify the inserted row by unique combo of url+hash+version.
        res = (
            db.table("regulations")
            .select("id")
            .eq("url", payload["url"])
            .eq("content_hash", payload["content_hash"])
            .eq("version", int(payload["version"]))
            .eq("is_current", True)
            .limit(1)
            .execute()
        )
        if not res.data:
            raise RuntimeError("Failed to resolve inserted regulation id.")
        return int(res.data[0]["id"])

    def check_single(self, regulation_id: int) -> UpdateResult | None:
        db = self._db_getter()

        reg_res = (
            db.table("regulations")
            .select(
                "id,jurisdiction_id,domain,category,source_name,url,content,content_hash,version,is_current"
            )
            .eq("id", int(regulation_id))
            .eq("is_current", True)
            .limit(1)
            .execute()
        )

        if not reg_res.data:
            return None

        reg = reg_res.data[0]
        url = str(reg.get("url") or "")
        if not url:
            return None

        new_content = self._fetch_url_content(url)
        if new_content is None:
            return None

        new_hash = self._sha256_fn(new_content)
        old_hash = str(reg.get("content_hash") or "")
        if new_hash == old_hash:
            return None

        detected_at = datetime.utcnow()
        affected_ids = self._jurisdiction_chain_ids(
            db, int(reg.get("jurisdiction_id") or 0)
        )

        old_content = str(reg.get("content") or "")
        update_summary = self._generate_update_summary(
            old_content=old_content, new_content=new_content
        )

        # Versioning flow
        db.table("regulations").update({"is_current": False}).eq(
            "id", int(regulation_id)
        ).execute()

        new_version = int(reg.get("version") or 1) + 1
        payload: dict[str, Any] = {
            "jurisdiction_id": int(reg["jurisdiction_id"]),
            "domain": reg.get("domain") or "housing",
            "category": reg.get("category") or "",
            "source_name": reg.get("source_name") or "Unknown",
            "url": url,
            "content": new_content,
            "content_hash": new_hash,
            "version": new_version,
            "is_current": True,
            "effective_date": reg.get("effective_date"),
        }
        new_regulation_id = self._insert_regulation_version(db=db, payload=payload)

        db.table("regulation_updates").insert(
            [
                {
                    "regulation_id": new_regulation_id,
                    "update_summary": update_summary,
                    "affected_jurisdictions": affected_ids,
                    "detected_at": detected_at,
                }
            ]
        ).execute()

        return UpdateResult(
            source_name=str(reg.get("source_name") or payload["source_name"]),
            url=url,
            category=str(reg.get("category") or payload["category"]),
            affected_jurisdiction_ids=affected_ids,
            update_summary=update_summary,
            detected_at=detected_at,
        )

    def check_for_updates(self) -> list[UpdateResult]:
        db = self._db_getter()

        regs_res = (
            db.table("regulations")
            .select(
                "id,jurisdiction_id,domain,category,source_name,url,content,content_hash,version,is_current"
            )
            .eq("is_current", True)
            .execute()
        )

        regs = regs_res.data or []
        out: list[UpdateResult] = []
        for row in regs:
            try:
                result = self.check_single(int(row["id"]))
                if result is not None:
                    out.append(result)
            except Exception:
                # Continue checking other regulations.
                continue

        return out


update_checker = UpdateChecker()


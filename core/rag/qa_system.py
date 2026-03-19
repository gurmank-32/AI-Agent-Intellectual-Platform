from __future__ import annotations

import re
from typing import Any

from core.llm.client import llm
from core.llm.prompts import QA_SYSTEM_PROMPT
from core.rag.utils import deduplicate_sources
from core.rag.vector_store import RegulationVectorStore

_MAX_CONTEXT_RESULTS = 5
_MAX_HISTORY_ITEMS = 6

_CONTEXT_LEAK_RE = re.compile(r"^From\s+.*\(.*\).*$", re.MULTILINE)
_NOTE_SUFFIX_RE = re.compile(r"\[Note:.*$", re.DOTALL)


def _build_context(results: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for r in results[:_MAX_CONTEXT_RESULTS]:
        meta = r.get("metadata") or {}
        header = meta.get("source_name") or meta.get("url") or "Source"
        blocks.append(f"[{header}]\n{r['document']}")
    return "\n---\n".join(blocks)


def _build_history(chat_history: list[dict[str, Any]]) -> str:
    recent = chat_history[-_MAX_HISTORY_ITEMS:]
    lines: list[str] = []
    for msg in recent:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _clean_answer(text: str) -> str:
    cleaned = _CONTEXT_LEAK_RE.sub("", text)
    cleaned = _NOTE_SUFFIX_RE.sub("", cleaned)
    return cleaned.strip()


def _extract_sources(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw: list[dict[str, Any]] = []
    for r in results[:_MAX_CONTEXT_RESULTS]:
        meta = r.get("metadata") or {}
        raw.append(
            {
                "source": meta.get("source_name", ""),
                "url": meta.get("url", ""),
                "category": meta.get("category", ""),
                "domain": meta.get("domain", ""),
            }
        )
    return deduplicate_sources(raw)


class QASystem:
    def __init__(self) -> None:
        self._store = RegulationVectorStore()

    def answer_question(
        self,
        question: str,
        chat_history: list[dict[str, Any]],
        jurisdiction_id: int | None = None,
    ) -> dict[str, Any]:
        # In `rule_based` mode we should still return a helpful message even if
        # vector search is unavailable (e.g., missing/invalid Supabase config).
        search_results: list[Any] = []
        try:
            search_results = self._store.search(
                query=question,
                n_results=_MAX_CONTEXT_RESULTS,
                jurisdiction_id=jurisdiction_id,
            )
        except Exception:
            if llm.is_ai_available():
                raise

        result_dicts: list[dict[str, Any]] = [
            {"document": r.document, "metadata": r.metadata, "score": r.score}
            for r in search_results
        ]
        sources = _extract_sources(result_dicts)

        if not llm.is_ai_available():
            return {
                "answer": (
                    "AI-powered answers are currently unavailable because no LLM API key "
                    "is configured. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY in your "
                    "environment to enable AI responses.\n\n"
                    "In the meantime, here are the most relevant regulation sources I found."
                ),
                "sources": sources,
            }

        context = _build_context(result_dicts)
        history = _build_history(chat_history)

        user_message = (
            f"Regulation context:\n{context}\n\n"
            f"Conversation history:\n{history}\n\n"
            f"Question: {question}"
        )

        raw_answer = llm.ask(system=QA_SYSTEM_PROMPT, user=user_message)
        answer = _clean_answer(raw_answer)

        return {"answer": answer, "sources": sources}


qa = QASystem()

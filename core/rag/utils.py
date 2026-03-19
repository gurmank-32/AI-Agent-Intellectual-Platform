from __future__ import annotations

from typing import Any


def deduplicate_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_urls: set[str] = set()
    seen_sources: set[str] = set()
    out: list[dict[str, Any]] = []

    for item in sources:
        url = item.get("url")
        if isinstance(url, str) and url.strip():
            key = url.strip()
            if key in seen_urls:
                continue
            seen_urls.add(key)
            out.append(item)
            continue

        src = item.get("source")
        if isinstance(src, str) and src.strip():
            key = src.strip()
            if key in seen_sources:
                continue
            seen_sources.add(key)
            out.append(item)
            continue

        # If neither url nor source is present, keep it (can't dedup reliably).
        out.append(item)

    return out


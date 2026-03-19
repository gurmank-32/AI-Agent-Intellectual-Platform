from __future__ import annotations

from core.rag.utils import deduplicate_sources


def test_deduplicate_sources() -> None:
    sources = [
        {"url": "https://example.com/a", "source": "Source A"},
        {"url": "https://example.com/b", "source": "Source B"},
        {"url": "https://example.com/a", "source": "Source A duplicate"},
        {"url": "https://example.com/c", "source": "Source C"},
        {"url": "https://example.com/b", "source": "Source B again"},
    ]
    result = deduplicate_sources(sources)
    assert len(result) == 3
    urls = [r["url"] for r in result]
    assert urls == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
    ]
    assert result[0]["source"] == "Source A"


def test_deduplicate_by_source_name() -> None:
    sources = [
        {"source": "HUD Guidance"},
        {"source": "Texas Property Code"},
        {"source": "HUD Guidance"},
        {"source": "Fair Housing Act"},
        {"source": "Texas Property Code"},
    ]
    result = deduplicate_sources(sources)
    assert len(result) == 3
    names = [r["source"] for r in result]
    assert names == ["HUD Guidance", "Texas Property Code", "Fair Housing Act"]

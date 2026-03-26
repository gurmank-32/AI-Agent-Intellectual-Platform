from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

import config
from core.regulations.scraper import is_supabase_connected
from core.regulations.scraper import scraper
from core.ui import apply_ui


def show_page() -> None:
    apply_ui()
    st.title("Settings", anchor=False)

    csv_path = Path(__file__).resolve().parents[1] / "data" / "seeds" / "sources.csv"

    st.subheader("Data", anchor=False)
    if st.button("Load regulations from CSV"):
        try:
            result = scraper.load_regulations_from_csv(csv_path=csv_path)
            st.success(
                f"Loaded {result.get('loaded', 0)} regulations, skipped {result.get('skipped', 0)} duplicates."
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to load regulations: {exc}")

    st.subheader("Vector Index", anchor=False)
    if st.button("Initialize vector index"):
        try:
            result = scraper.initialize_vector_index()
            st.success(
                f"Vector index initialized for {result.get('indexed_docs', 0)} unindexed regulations (doc count)."
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to initialize vector index: {exc}")

    st.subheader("Indexing status", anchor=False)
    try:
        status_rows = scraper.get_indexing_status()
        if status_rows:
            st.dataframe(
                status_rows,
                use_container_width=True,
            )
        else:
            st.info("No indexing status available yet.")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load indexing status: {exc}")

    st.divider()
    st.subheader("API status", anchor=False)

    supabase_ok = is_supabase_connected()
    c1, c2, c3 = st.columns(3)
    c1.metric("Anthropic", "set" if config.settings.has_anthropic_key else "not set")
    c2.metric("OpenAI", "set" if config.settings.has_openai_key else "not set")
    c3.metric("Supabase", "connected" if supabase_ok else "not connected")

    st.divider()
    st.subheader("Scraper", anchor=False)
    if st.button("Manual scraper trigger"):
        try:
            res = scraper.run_manual_scraper()
            st.success(f"Scraper trigger result: {res.get('status')}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Manual scraper trigger failed: {exc}")


show_page()


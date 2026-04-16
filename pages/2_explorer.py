from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import streamlit as st

from core.regulations import explorer
from ui_theme import apply_theme, cross_page_link, log_activity, metric_card, page_hero, section_heading, skeleton_card


_CST = timezone(timedelta(hours=-6))


def _format_sync_time(raw: Any) -> str:
    """Return a human-readable date + time in CST, e.g. 'Apr 10, 2025 · 2:32 PM CST'."""
    if not raw:
        return "N/A"
    try:
        dt = datetime.fromisoformat(str(raw)).astimezone(_CST)
        return dt.strftime("%b %d, %Y · %I:%M %p") + " CST"
    except (ValueError, TypeError):
        return str(raw)


def show_page() -> None:
    apply_theme()
    page_hero("🔍", "Regulation Explorer", "Search and browse indexed housing regulations across all covered jurisdictions.", "blue")

    metrics = explorer.get_explorer_metrics()
    total_regs = metrics["total_regulations"]
    total_states = metrics["total_states_covered"]
    last_updated = _format_sync_time(metrics["last_updated"])

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(metric_card("Indexed Regulations", f"{total_regs:,}", "📑"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("Jurisdictions", str(total_states), "📍"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("Most Recent Sync", last_updated, "🕐"), unsafe_allow_html=True)

    st.markdown('<div style="height:1.5rem;"></div>', unsafe_allow_html=True)

    section_heading("Search Regulations")

    popular_searches = ["rent control", "eviction notice", "fair housing", "security deposit", "lease termination"]
    chip_cols = st.columns(len(popular_searches))
    chip_clicked: Optional[str] = None
    for i, term in enumerate(popular_searches):
        with chip_cols[i]:
            if st.button(term, key=f"chip_{term}", use_container_width=True):
                chip_clicked = term

    default_query = chip_clicked or ""
    query = st.text_input(
        "Search regulations",
        value=default_query,
        placeholder="Search by regulation title, legal code, or keyword...",
        label_visibility="collapsed",
    )

    col_cat, col_state, col_btn = st.columns([2, 2, 1])

    categories = explorer.get_distinct_categories()
    with col_cat:
        selected_category = st.selectbox(
            "Category",
            options=["All Categories"] + categories,
            index=0,
        )
    category_value: Optional[str] = (
        None if selected_category == "All Categories" else selected_category
    )

    state_options = explorer.get_state_jurisdiction_options()
    state_names = ["All States"] + [s["name"] for s in state_options]
    with col_state:
        selected_state_name = st.selectbox(
            "State",
            options=state_names,
            index=0,
        )
    selected_state_id: Optional[int] = None
    if selected_state_name != "All States":
        for s in state_options:
            if s["name"] == selected_state_name:
                selected_state_id = int(s["id"])
                break

    with col_btn:
        st.markdown('<div style="height:1.6rem;"></div>', unsafe_allow_html=True)
        search_clicked = st.button("Search", type="primary", use_container_width=True)

    should_search = (search_clicked or chip_clicked) and query.strip()
    if should_search:
        results_placeholder = st.empty()
        results_placeholder.markdown(skeleton_card(3), unsafe_allow_html=True)

        results = explorer.search_regulations(
            query=query.strip(),
            jurisdiction_id=selected_state_id,
            category=category_value,
            n_results=5,
        )
        results_placeholder.empty()
        log_activity("Searched regulations", query.strip()[:60])

        st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)
        section_heading("Search Results")

        if not results:
            st.info("No matching regulations found. Try different keywords or broaden your filters.")
            return

        df = explorer.to_results_dataframe(results)
        st.dataframe(df, use_container_width=True, hide_index=True)
        cross_page_link("💬", "Ask the Compliance Agent about these regulations →", "pages/1_agent.py")


show_page()

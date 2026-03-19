from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from core.regulations.explorer import get_state_jurisdiction_options
from core.regulations.update_checker import update_checker
from db.client import get_db


def show_page() -> None:
    st.title("Update Log")

    state_options = get_state_jurisdiction_options()
    state_names = ["(All states)"] + [s["name"] for s in state_options]
    state_default_index = 0

    selected_state_name = st.selectbox(
        "Filter by state", options=state_names, index=state_default_index
    )
    selected_state_id: Optional[int] = None
    if selected_state_name != "(All states)":
        for s in state_options:
            if s["name"] == selected_state_name:
                selected_state_id = int(s["id"])
                break

    if st.button("Check for updates now"):
        updates = update_checker.check_for_updates()
        st.session_state["latest_updates"] = updates
        st.rerun()

    count = st.slider("How many updates to show?", min_value=1, max_value=50, value=10)

    updates: list[Any] = st.session_state.get("latest_updates") or []
    if not updates:
        st.info("No updates found.")
        return

    filtered = []
    for u in updates:
        affected = getattr(u, "affected_jurisdiction_ids", []) or []
        if selected_state_id is None or int(selected_state_id) in [int(x) for x in affected]:
            filtered.append(u)

    # Sort by most recent first, then deduplicate by source+url.
    filtered.sort(key=lambda x: getattr(x, "detected_at"), reverse=True)

    deduped: list[Any] = []
    seen: set[str] = set()
    for u in filtered:
        key = f"{getattr(u, 'source_name', '')}|{getattr(u, 'url', '')}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(u)

    deduped = deduped[:count]

    # Map affected jurisdiction IDs to names for display.
    all_affected_ids: set[int] = set()
    for u in deduped:
        for jid in getattr(u, "affected_jurisdiction_ids", []) or []:
            all_affected_ids.add(int(jid))

    jid_to_name: dict[int, str] = {}
    if all_affected_ids:
        db = get_db()
        juris_res = (
            db.table("jurisdictions")
            .select("id,name")
            .in_("id", list(all_affected_ids))
            .execute()
        )
        for row in juris_res.data or []:
            jid_to_name[int(row["id"])] = str(row.get("name") or row["id"])

    st.subheader("Latest regulation updates")
    for u in deduped:
        category = str(getattr(u, "category", "") or "")
        url = str(getattr(u, "url", "") or "")
        update_summary = str(getattr(u, "update_summary", "") or "")
        affected_ids = getattr(u, "affected_jurisdiction_ids", []) or []
        affected_names = [jid_to_name.get(int(jid), str(jid)) for jid in affected_ids]

        with st.expander(f"{category} — {url}", expanded=False):
            st.write(f"Category: {category}")
            st.write(f"URL: {url}")
            st.write(f"Affected jurisdictions: {', '.join(affected_names) or '(none)'}")
            st.write(f"Detected: {getattr(u, 'detected_at', '')}")
            st.write("Update summary:")
            st.write(update_summary)


show_page()


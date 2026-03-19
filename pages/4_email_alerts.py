from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from core.regulations.explorer import get_state_jurisdiction_options
from core.notifications.email_alerts import email_alerts


def show_page() -> None:
    st.title("Email Alerts")

    state_options = get_state_jurisdiction_options()
    state_names = [s["name"] for s in state_options]
    state_ids = [int(s["id"]) for s in state_options]

    col_sub, col_unsub = st.columns(2)

    with col_sub:
        st.subheader("Subscribe")
        sub_email = st.text_input("Email")
        sub_state_name = st.selectbox(
            "State", options=state_names if state_names else ["(No states)"], index=0
        )
        sub_state_id: Optional[int] = None
        if sub_state_name != "(No states)":
            sub_state_id = next(
                int(s["id"]) for s in state_options if str(s["name"]) == sub_state_name
            )

        if st.button("Subscribe"):
            if not sub_email.strip():
                st.error("Please enter an email.")
            elif sub_state_id is None:
                st.error("Please select a state.")
            else:
                email_alerts.subscribe(email=sub_email.strip(), jurisdiction_id=sub_state_id)
                st.success("Subscription saved (welcome email sent if SMTP is configured).")

    with col_unsub:
        st.subheader("Unsubscribe")
        unsub_email = st.text_input("Email", key="unsub_email")
        unsub_state_name = st.selectbox(
            "State",
            options=state_names if state_names else ["(No states)"],
            index=0,
            key="unsub_state",
        )
        unsub_state_id: Optional[int] = None
        if unsub_state_name != "(No states)":
            unsub_state_id = next(
                int(s["id"]) for s in state_options if str(s["name"]) == unsub_state_name
            )

        if st.button("Unsubscribe"):
            if not unsub_email.strip():
                st.error("Please enter an email.")
            elif unsub_state_id is None:
                st.error("Please select a state.")
            else:
                email_alerts.unsubscribe(
                    email=unsub_email.strip(), jurisdiction_id=unsub_state_id
                )
                st.success("You have been unsubscribed.")

    st.divider()
    st.subheader("View subscriptions")
    view_email = st.text_input("Enter email to view active subscriptions", key="view_email")
    if st.button("Load subscriptions", key="load_subs"):
        if not view_email.strip():
            st.error("Please enter an email.")
        else:
            subs = email_alerts.get_active_subscriptions(email=view_email.strip())
            if not subs:
                st.info("No active subscriptions found for this email.")
            else:
                for s in subs:
                    st.write(f"- {s['jurisdiction_name']}")

    st.divider()
    st.subheader("Daily digest emails")
    st.write(
        "Subscribers receive a daily digest of newly detected regulation updates for their selected jurisdictions. "
        "If immediate alerts are enabled for a category update, those may be sent sooner."
    )


show_page()


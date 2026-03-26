import streamlit as st

import config
from core.ui import apply_ui


def main() -> None:
    st.set_page_config(page_title="Compliance Agent", page_icon="⚖️", layout="wide")
    apply_ui()

    with st.sidebar:
        st.title("Compliance Agent", anchor=False)
        st.caption(config.LEGAL_DISCLAIMER)

    st.title("Compliance Agent", anchor=False)
    st.write("Use the pages in the left sidebar to get started.")


if __name__ == "__main__":
    main()

import streamlit as st

import config


def main() -> None:
    st.set_page_config(page_title="Compliance Agent", page_icon="⚖️", layout="wide")

    with st.sidebar:
        st.title("Compliance Agent")
        st.caption(config.LEGAL_DISCLAIMER)

    st.title("Compliance Agent")
    st.write("Use the pages in the left sidebar to get started.")


if __name__ == "__main__":
    main()

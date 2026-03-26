from __future__ import annotations

import streamlit as st


UI_CSS = """
<style>
/* Base app look */
.stApp {
  background-color: #f8f9fa !important;
}
[data-testid="stAppViewContainer"], [data-testid="stHeader"] {
  background-color: #f8f9fa !important;
}
[data-testid="stSidebar"] {
  background-color: #f1f5f9 !important;
}
.block-container {
  padding-top: 1.25rem;
  padding-bottom: 1.75rem;
}
h1, h2, h3, p, label, span, .stMarkdown {
  color: #1e293b !important;
}

/* Hide auto-generated heading anchors / link icons */
[data-testid="stHeadingWithAnchor"],
[data-testid="StyledLinkIconContainer"] {
  display: none !important;
}
.stApp h1 a[href^="#"],
.stApp h2 a[href^="#"],
.stApp h3 a[href^="#"],
.stApp h4 a[href^="#"],
.stApp h5 a[href^="#"],
.stApp h6 a[href^="#"],
.stApp h1 > div > a,
.stApp h2 > div > a,
.stApp h3 > div > a,
.stApp h4 > div > a,
.stApp h5 > div > a,
.stApp h6 > div > a {
  display: none !important;
}

/* Card-like containers */
[data-testid="stVerticalBlockBorderWrapper"],
div.stVerticalBlockBorderWrapper {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 12px !important;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
}

/* Inactive clickable state */
.stButton > button[data-testid="baseButton-secondary"],
[data-testid="stFormSubmitButton"] button[data-testid="baseButton-secondary"],
[data-testid="stDownloadButton"] button[data-testid="baseButton-secondary"],
[data-testid="stPopover"] > button {
  background-color: #E8EAF0 !important;
  color: #333333 !important;
  border: 1px solid #D0D3DC !important;
  box-shadow: 0 2px 5px rgba(0,0,0,0.10) !important;
  border-radius: 8px !important;
  transition: all 0.2s ease !important;
}

/* Inactive hover */
.stButton > button[data-testid="baseButton-secondary"]:hover:not(:disabled),
[data-testid="stFormSubmitButton"] button[data-testid="baseButton-secondary"]:hover:not(:disabled),
[data-testid="stDownloadButton"] button[data-testid="baseButton-secondary"]:hover:not(:disabled),
[data-testid="stPopover"] > button:hover:not(:disabled):not([aria-expanded="true"]) {
  background-color: #D8DCE8 !important;
  box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
  transform: translateY(-1px) !important;
  cursor: pointer !important;
}

/* Active / selected state */
.stButton > button[data-testid="baseButton-primary"],
[data-testid="stFormSubmitButton"] button[data-testid="baseButton-primary"],
[data-testid="stDownloadButton"] button[data-testid="baseButton-primary"],
[data-testid="stPopover"] > button[aria-expanded="true"] {
  background-color: #2563EB !important;
  color: white !important;
  border: none !important;
  box-shadow: 0 2px 5px rgba(0,0,0,0.15) !important;
  border-radius: 8px !important;
  transition: all 0.2s ease !important;
}

.stButton > button[data-testid="baseButton-primary"]:hover:not(:disabled),
[data-testid="stFormSubmitButton"] button[data-testid="baseButton-primary"]:hover:not(:disabled),
[data-testid="stDownloadButton"] button[data-testid="baseButton-primary"]:hover:not(:disabled),
[data-testid="stPopover"] > button[aria-expanded="true"]:hover:not(:disabled) {
  background-color: #2563EB !important;
  color: white !important;
  box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
  transform: translateY(-1px) !important;
  cursor: pointer !important;
}

/* Selects and dropdown triggers */
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div,
[data-testid="stDateInput"] [data-baseweb="select"] > div {
  background-color: #E8EAF0 !important;
  color: #333333 !important;
  border: 1px solid #D0D3DC !important;
  box-shadow: 0 2px 5px rgba(0,0,0,0.10) !important;
  border-radius: 8px !important;
  transition: all 0.2s ease !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"]:hover > div,
[data-testid="stMultiSelect"] [data-baseweb="select"]:hover > div,
[data-testid="stDateInput"] [data-baseweb="select"]:hover > div {
  background-color: #D8DCE8 !important;
  box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
}

/* Dropdown menu options */
[data-baseweb="menu"] li:not([aria-disabled="true"]):hover,
[data-baseweb="popover"] ul[role="listbox"] li:hover,
[data-baseweb="popover"] [role="option"]:hover {
  background-color: #D8DCE8 !important;
  cursor: pointer !important;
}

/* Expander headers */
[data-testid="stExpander"] details > summary {
  background-color: #E8EAF0 !important;
  color: #333333 !important;
  border: 1px solid #D0D3DC !important;
  box-shadow: 0 2px 5px rgba(0,0,0,0.10) !important;
  border-radius: 8px !important;
  transition: all 0.2s ease !important;
}
[data-testid="stExpander"] details > summary:hover {
  background-color: #D8DCE8 !important;
  box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
  transform: translateY(-1px);
  cursor: pointer !important;
}
[data-testid="stExpander"] details[open] > summary {
  background-color: #2563EB !important;
  color: white !important;
  border: none !important;
  box-shadow: 0 2px 5px rgba(0,0,0,0.15) !important;
  border-radius: 8px !important;
}

/* File upload zone */
[data-testid="stFileUploaderDropzone"], [data-testid="stFileUploader"] > section {
  background-color: #E8EAF0 !important;
  border: 1px solid #D0D3DC !important;
  box-shadow: 0 2px 5px rgba(0,0,0,0.10) !important;
  border-radius: 8px !important;
  transition: all 0.2s ease !important;
}
[data-testid="stFileUploaderDropzone"]:hover, [data-testid="stFileUploader"] > section:hover {
  background-color: #D8DCE8 !important;
  box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
  transform: translateY(-1px);
  cursor: pointer !important;
}
</style>
"""


def apply_ui() -> None:
    st.markdown(UI_CSS, unsafe_allow_html=True)

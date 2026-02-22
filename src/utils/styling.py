import streamlit as st

SIDEBAR_CUSTOM_CSS = """
<style>
/* Sidebar background and padding */
section[data-testid="stSidebar"] {
    min-width: 240px;
    width: fit-content;
}


/* Sidebar radio label */
section[data-testid="stSidebar"] .stRadio > div[role='radiogroup'] > label[data-baseweb="radio"] {
    color: #fff !important;
    font-size: 16px;
    font-weight: 500;
    padding: 12px 8px;
    border-radius: 8px;
    margin-bottom: 4px;
    transition: background 0.2s;
    width: 100%;
    display: block;
    box-sizing: border-box;
    min-width: 0;
    background: transparent;
}

section[data-testid="stSidebar"] .stRadio > div[role='radiogroup'] label[data-baseweb="radio"] > div:first-child {
    display: none;
}

section[data-testid="stSidebar"] .stElementContainer {
    width: 100%;
}

section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] {
    display: none;
}

section[data-testid="stSidebar"] div.stHeading {
    padding-left: 16px;
}

section[data-testid="stSidebar"] .stRadio > div[role='radiogroup'] label[data-baseweb="radio"] div[data-testid="stMarkdownContainer"] span[role="img"] {
    padding-right: 6px;
}
</style>
"""

SIDEBAR_HIGHLIGHT_CUSTOM_CSS_DARK_MODE = """
<style>
section[data-testid="stSidebar"] .stRadio > div[role='radiogroup'] > label[data-baseweb="radio"]:has(input:checked) {
    background: #0e1117;
    color: #fff !important;
    width: 100%;
    display: block;
}
</style>
"""

SIDEBAR_HIGHLIGHT_CUSTOM_CSS_LIGHT_MODE = """
<style>
section[data-testid="stSidebar"] .stRadio > div[role='radiogroup'] > label[data-baseweb="radio"]:has(input:checked) {
    background: #d0d0d0;
    color: #222 !important;
    width: 100%;
    display: block;
}
</style>
"""


def load_custom_css():
    st.markdown(SIDEBAR_CUSTOM_CSS, unsafe_allow_html=True)
    if st.context.theme.type == "dark":
        st.markdown(SIDEBAR_HIGHLIGHT_CUSTOM_CSS_DARK_MODE, unsafe_allow_html=True)
    else:
        st.markdown(SIDEBAR_HIGHLIGHT_CUSTOM_CSS_LIGHT_MODE, unsafe_allow_html=True)

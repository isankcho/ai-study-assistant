import os
import streamlit as st


def load_env_vars():
    for k, v in st.secrets.items():
        os.environ.setdefault(k, v)

import streamlit as st
from contextlib import contextmanager


@contextmanager
def net_action(text: str):
    with st.spinner(text, show_time=True):
        yield

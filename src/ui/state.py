import streamlit as st
from langchain_core.messages import AIMessage
from utils.constants import STATE_KEYS


@st.cache_data(ttl=3600)
def _fetch_state_data():
    """Fetch current session state for persistence."""
    return {k: st.session_state[k] for k in STATE_KEYS}


def load_state_from_cache():
    """Restore state values from cache into session state."""
    saved_state = _fetch_state_data()
    for k in STATE_KEYS:
        st.session_state[k] = saved_state[k]


def save_state_to_cache():
    """Save current session state into cache."""
    _fetch_state_data.clear()
    _fetch_state_data()


def clear_state_from_cache():
    """Clear cached session state."""
    _fetch_state_data.clear()


def ensure_state():
    """Ensure default state values exist, then load cached state."""
    defaults = {
        "due_notes": [],
        "notes_md": "",
        "messages": [],
        "questions": [],
        "current_question_idx": 0,
        "qna": [],
        "selected_notion_page": None,
        "quiz_generated": False,
        "quiz_evaluated": False,
        "evaluation_output": "",
        "ingestion_in_progress": False,
        "revision_in_progress": False,
        "revision_logged": False,
        "chatbot_messages": [AIMessage(content="Hello! How can I assist you today?")],
        "chatbot_turn": "human",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    load_state_from_cache()

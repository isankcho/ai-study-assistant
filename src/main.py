import streamlit as st
from ui.state import ensure_state
from node_setup import ensure_node_modules
from utils.constants import Pages
from utils.logging import setup_logging
from utils.styling import load_custom_css
from di.container import Container


def main():
    setup_logging()
    ensure_state()
    load_custom_css()
    container = Container()

    st.sidebar.title("Navigation")
    selection = st.sidebar.radio(
        "Navigation",
        (
            Pages.CHATBOT.value["key"],
            Pages.UPLOAD_NOTES.value["key"],
            Pages.REVISION.value["key"],
        ),
        format_func=lambda x: {
            Pages.REVISION.value["key"]: Pages.REVISION.value["title"],
            Pages.UPLOAD_NOTES.value["key"]: Pages.UPLOAD_NOTES.value["title"],
            Pages.CHATBOT.value["key"]: Pages.CHATBOT.value["title"],
        }[x],
        label_visibility="hidden",
    )

    if selection == Pages.REVISION.value["key"]:
        container.revision_page().render()
    elif selection == Pages.UPLOAD_NOTES.value["key"]:
        container.upload_notes_page().render()
    elif selection == Pages.CHATBOT.value["key"]:
        container.chatbot_page().render()


if __name__ == "__main__":
    ensure_node_modules()
    main()

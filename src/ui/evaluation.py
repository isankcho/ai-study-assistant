from clients.notion_client import NotionClient
import streamlit as st
from datetime import datetime
from ui.state import clear_state_from_cache


def _log_revision():
    """Log a revision in Notion, then clear state cache."""
    notion_client = NotionClient()
    notion_client.log_revision(st.session_state.selected_notion_page[1])
    st.session_state.revision_logged = True
    clear_state_from_cache()
    st.cache_data.clear()


def render_evaluation():
    """Render evaluation results after quiz completion."""
    if not st.session_state.evaluation_output:
        return

    output = st.session_state.evaluation_output
    try:
        with st.container(border=True):
            st.subheader("Evaluation")
            st.caption(datetime.now().strftime("%Y-%m-%d %H:%M"))
            tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Notes", "Q&A", "Raw"])

            with tab1:
                st.json(output) if isinstance(output, dict) else st.markdown(output)

            with tab2:
                st.markdown(st.session_state.notes_md)

            with tab3:
                rows = [
                    {
                        "Question": x.get("question", ""),
                        "Your Answer": x.get("answer", ""),
                    }
                    for x in st.session_state.qna
                ]
                st.dataframe(rows, width="stretch")

            with tab4:
                (
                    st.json(output)
                    if isinstance(output, dict)
                    else st.code(output, language="markdown")
                )

            st.button(
                "Log revision",
                type="primary",
                disabled=not st.session_state.selected_notion_page
                or st.session_state.revision_logged,
                on_click=_log_revision,
            )
    except Exception as e:
        st.error(str(e))

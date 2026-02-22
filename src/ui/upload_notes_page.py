import streamlit as st
from utils.constants import Label, Keys
from ui.net_action import net_action
from ui.state import save_state_to_cache
from ui.Page import Page
from workflows.ingestion_workflow import IngestionWorkflow


class UploadNotesPage(Page):
    """UI for uploading and ingesting notes."""

    def __init__(self, ingestion_workflow: IngestionWorkflow):
        self.ingestion_workflow = ingestion_workflow

    def _set_ingestion_in_progress_true(self):
        st.session_state.ingestion_in_progress = True
        save_state_to_cache()

    def render(self):
        st.title("Upload Notes!")
        with st.form("notes_form", clear_on_submit=True):
            chapter_name = st.text_input(
                Label.CHAPTER_NAME.value + Label.MANDATORY_FIELD_MARKER.value,
                key=Keys.CHAPTER_NAME.value,
            )
            resource_tag = st.text_input(
                Label.RESOURCE_TAG.value + Label.MANDATORY_FIELD_MARKER.value,
                key=Keys.RESOURCE_TAG.value,
            )
            context = st.text_area(Label.CONTEXT.value, key=Keys.CONTEXT.value)
            files = st.file_uploader(
                Label.FILE_UPLOAD.value + Label.MANDATORY_FIELD_MARKER.value,
                type=["jpg", "jpeg"],
                accept_multiple_files=True,
                key=Keys.FILE_UPLOAD.value,
            )
            submitted = st.form_submit_button(
                Label.SUBMIT_BUTTON.value,
                disabled=st.session_state.ingestion_in_progress,
                on_click=self._set_ingestion_in_progress_true,
            )

        if not submitted:
            return

        if not chapter_name or not resource_tag or not files:
            st.error("Chapter, Resource Tag and at least one file are required.")
            return

        try:
            tracker = st.progress(0)
            with net_action("Ingesting notes..."):
                self.ingestion_workflow.run(
                    {
                        "chapter_name": chapter_name,
                        "resource_tag": resource_tag,
                        "files": files,
                        "additional_context": context,
                        "progress_tracker": tracker,
                    },
                )
            tracker.progress(1.0, "completed")
            st.success("Notes ingested.")
            save_state_to_cache()
        except Exception as e:
            st.error(str(e))

from clients.notion_client import NotionClient
from config.config import SETTINGS
import streamlit as st
from utils.constants import Label
from ui.net_action import net_action
from ui.state import save_state_to_cache
from ui.evaluation import render_evaluation
from ui.Page import Page
from workflows.llm_quiz_evaluation_workflow import LLMQuizEvaluationWorkflow
from workflows.quiz_generation_workflow import QuizGenerationWorkflow


class RevisionPage(Page):
    """UI for revision and quiz flow."""

    def __init__(
        self,
        notion_client: NotionClient,
        quiz_generation_workflow: QuizGenerationWorkflow,
        llm_quiz_evaluation_workflow: LLMQuizEvaluationWorkflow,
    ):
        self.notion_client = notion_client
        self.quiz_generation_workflow = quiz_generation_workflow
        self.llm_quiz_evaluation_workflow = llm_quiz_evaluation_workflow

    def _list_due_notes(self):
        """Return a list of (name, id, url) tuples for due notes."""
        if not st.session_state["due_notes"]:
            with net_action("Fetching due notes..."):
                res = self.notion_client.fetch_due_notes(
                    SETTINGS.notion_knowledge_db_id
                )
                st.session_state["due_notes"] = res.get("results", [])

        options = []
        for note in st.session_state["due_notes"]:
            props = note.get("properties", {})
            name = (
                props.get("Name", {})
                .get("title", [{}])[0]
                .get("text", {})
                .get("content", "")
            )
            nid, url = note.get("id"), note.get("url")
            if name and nid and url:
                options.append((name, nid, url))
        return options

    def _set_revision_in_progress_true(self):
        st.session_state.revision_in_progress = True
        save_state_to_cache()

    def _trigger_quiz_generation(self, selected):
        """Generate quiz questions from a selected Notion page."""
        if st.session_state.quiz_generated:
            return

        st.session_state.update(
            {
                "selected_notion_page": selected,
                "notes_md": "",
                "questions": [],
                "current_question_idx": -1,
                "qna": [],
                "quiz_evaluated": False,
            }
        )

        with net_action("Generating quiz..."):
            output = self.quiz_generation_workflow.run(
                {"notion_page_id": selected[1], "notion_url": selected[2]}
            )
            st.session_state.notes_md = output["notes_md"]
            st.session_state.questions = output["questions"]
            st.session_state.quiz_generated = True
            save_state_to_cache()

    def _advance_chat_flow(self):
        """Manage chat-driven quiz flow and evaluation."""
        questions = st.session_state.questions
        if not questions:
            return

        # Start quiz
        if st.session_state.current_question_idx == -1:
            cur = questions[0]
            st.session_state.messages.append({"role": "assistant", "content": cur})
            st.session_state.current_question_idx = 0
            save_state_to_cache()
            st.rerun()
            return

        # Handle responses
        if st.session_state.current_question_idx < len(questions):
            response = st.chat_input("Please write your answer here...")
            if response:
                answer = {"text": response}
                st.session_state.messages.append({"role": "user", "content": answer})
                st.session_state.qna.append(
                    {
                        "question": questions[st.session_state.current_question_idx][
                            "text"
                        ],
                        "answer": answer["text"],
                    }
                )
                st.session_state.current_question_idx += 1
                if st.session_state.current_question_idx < len(questions):
                    cur = questions[st.session_state.current_question_idx]
                    st.session_state.messages.append(
                        {"role": "assistant", "content": cur}
                    )
                save_state_to_cache()
                st.rerun()
            return

        # Evaluate
        if not st.session_state.quiz_evaluated:
            with net_action("Evaluating your answers..."):
                output = self.llm_quiz_evaluation_workflow.run(
                    {
                        "notes_md": st.session_state.notes_md,
                        "qna": st.session_state.qna,
                        "notion_url": (
                            st.session_state.selected_notion_page[2]
                            if st.session_state.selected_notion_page
                            else ""
                        ),
                    }
                )
                st.session_state.evaluation_output = output
                st.session_state.quiz_evaluated = True
                save_state_to_cache()
        render_evaluation()

    def render(self):
        st.title("Let's Revise!")
        try:
            with st.form("revision_form", clear_on_submit=True):
                options = self._list_due_notes()
                selected = st.selectbox(
                    "Which notes would you like to revise?",
                    options,
                    format_func=lambda x: x[0],
                    index=None,
                    placeholder="Select notes to revise...",
                )
                submitted = st.form_submit_button(
                    Label.SUBMIT_BUTTON.value,
                    disabled=st.session_state.revision_in_progress or not options,
                    on_click=self._set_revision_in_progress_true,
                )

            if submitted and selected:
                self._trigger_quiz_generation(selected)
                st.rerun()

            # Render chat messages
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"]["text"])

            self._advance_chat_flow()
        except Exception as e:
            st.error(str(e))

from typing import Any, Dict
from langgraph.graph import StateGraph, START, END
from models.models import QuizState
from workflows.workflow import Workflow
from clients.notion_client import NotionClient
from workflows.llm_quiz_generation_workflow import LLMQuizGenerationWorkflow


class QuizGenerationWorkflow(Workflow):

    def __init__(
        self,
        notion_client: NotionClient,
        llm_quiz_generation_workflow: LLMQuizGenerationWorkflow,
    ) -> None:
        self.notion_client = notion_client
        self.llm_quiz_generation_workflow = llm_quiz_generation_workflow
        self.n_questions = 10
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(QuizState)
        graph.add_node("fetch_notes", self._fetch_notes_from_notion)
        graph.add_node("generate_quiz", self._generate_quiz_from_notes)
        graph.add_edge(START, "fetch_notes")
        graph.add_edge("fetch_notes", "generate_quiz")
        graph.add_edge("generate_quiz", END)
        return graph.compile()

    def _coerce_state(self, payload: Dict[str, Any]) -> QuizState:
        if not isinstance(payload, dict):
            raise ValueError("Input must be a dict")
        page_id = payload.get("notion_page_id")
        url = payload.get("notion_url")
        if not page_id:
            raise ValueError("notion_page_id is required")
        if not url:
            raise ValueError("notion_url is required")
        n_q = payload.get("n_questions", self.n_questions)
        return QuizState(notion_page_id=page_id, notion_url=url, n_questions=n_q)

    def _fetch_notes_from_notion(self, state: QuizState) -> Dict[str, Any]:
        notes_md = self.notion_client.fetch_page_markdown(state.notion_page_id)
        return {"notes_md": notes_md}

    def _generate_quiz_from_notes(self, state: QuizState) -> Dict[str, Any]:
        llm_out = self.llm_quiz_generation_workflow.run(
            {"notes_md": state.notes_md, "n_questions": state.n_questions}
        )
        return {"questions": llm_out["questions"]}

    def run(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self.graph.invoke(input=self._coerce_state(input))

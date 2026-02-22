import logging
from clients.notion_client import NotionClient
from langchain_core.tools import StructuredTool
from typing import List, Dict, Any

from workflows.llm_quiz_evaluation_workflow import LLMQuizEvaluationWorkflow
from workflows.llm_quiz_generation_workflow import LLMQuizGenerationWorkflow

logger = logging.getLogger(__name__)


class QuizToolset:
    """Collection of tools that use LLM for various tasks."""

    def __init__(
        self,
        notion_client: NotionClient,
        llm_quiz_generation_workflow: LLMQuizGenerationWorkflow,
        llm_quiz_evaluation_workflow: LLMQuizEvaluationWorkflow,
    ):
        self.notion_client = notion_client
        self.llm_quiz_generation_workflow = llm_quiz_generation_workflow
        self.llm_quiz_evaluation_workflow = llm_quiz_evaluation_workflow

    def generate_quiz_from_notes(
        self, page_id: str, n_questions: int = 10
    ) -> Dict[str, Any]:
        """
        Generate a quiz based on the content of a specific Notion page.

        This method leverages a language model to create a quiz from the notes
        available in the specified Notion page. The quiz consists of a set of
        questions derived from the content, along with references to the sections
        of the notes where the questions were sourced.

        Args:
            page_id (str): The unique identifier of the Notion page containing the notes.
            n_questions (int, optional): The number of quiz questions to generate. Defaults to 10.

        Returns:
            Dict[str, Any]: A dictionary containing the generated quiz questions in the following format:
            {
                "questions": [
                    {
                        "id": "q001",           # Unique zero-padded question ID (e.g., "q001").
                        "text": "Question text", # The question prompt derived from the notes.
                        "refs": [               # List of strings representing the full header path for the question's source.
                            "H1: Header Level 1",
                            "H2: Header Level 2",
                            ...
                        ]
                    },
                    ...
                ]
            }
        """
        logger.info("TOOL_USAGE: Generating quiz from notes")
        notes_md = self.notion_client.fetch_page_markdown(page_id)
        quiz = self.llm_quiz_generation_workflow.run(
            {"notes_md": notes_md, "n_questions": n_questions}
        )
        return quiz

    def evaluate_quiz(
        self,
        page_id: str,
        questions: list[str],
        answers: list[str],
        notion_url: str = "",
    ) -> str:
        """
        Evaluate the answers to a quiz based on the content of a specific Notion page.

        This method uses a language model to assess the correctness of the provided answers
        to the quiz questions. It compares the answers against the content of the specified
        Notion page and provides feedback, including corrections where applicable.

        Args:
            page_id (str): The unique identifier of the Notion page containing the notes.
            questions (list[str]): A list of quiz questions to be evaluated.
            answers (list[str]): A list of answers corresponding to the quiz questions.
            notion_url (str, optional): The URL of the Notion page associated with the notes. This is used for reference in the evaluation report. Defaults to an empty string.

        Returns:
            str: A markdown-formatted string containing the evaluation results. The evaluation includes details on the correctness of each answer and suggested corrections or improvements where necessary.
        """
        logger.info("TOOL_USAGE: Evaluating quiz answers")
        notes_md = self.notion_client.fetch_page_markdown(page_id)
        qna = [{"question": q, "answer": a} for q, a in zip(questions, answers)]
        evaluation = self.llm_quiz_evaluation_workflow.run(
            {"notes_md": notes_md, "qna": qna, "notion_url": notion_url}
        )
        return evaluation

    def as_tools(self) -> List[StructuredTool]:
        return [
            StructuredTool.from_function(
                name="generate_quiz_from_notes",
                func=self.generate_quiz_from_notes,
            ),
            StructuredTool.from_function(
                name="evaluate_quiz",
                func=self.evaluate_quiz,
            ),
        ]

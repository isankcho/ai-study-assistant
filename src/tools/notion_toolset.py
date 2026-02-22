import logging
from clients.notion_client import NotionClient
from config.config import SETTINGS
from langchain_core.tools import StructuredTool
from typing import Any, List, Dict, Literal

from utils.notion_utils import select_dsa_problem

logger = logging.getLogger(__name__)


class NotionToolset:
    """Collection of tools to interact with Notion."""

    def __init__(self, notion_client: NotionClient):
        self.notion_client = notion_client

    def fetch_due_notes(self) -> List[Dict[str, Any]]:
        """
        Retrieve notes that are due for revision from the Notion database.

        This method interacts with the Notion client to fetch all notes that are marked as due for revision.
        It processes the raw data returned by the Notion API and formats it into a list of dictionaries,
        where each dictionary contains the note's ID, title, properties, and URL.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing a due note with its details,
            including the note's ID, title, properties, and URL.
        """
        logger.info("TOOL_USAGE: Fetching due notes from Notion")
        due_notes = self.notion_client.fetch_due_notes(SETTINGS.notion_knowledge_db_id)
        due_notes_formatted = [
            {
                "page_id": note["id"],
                "title": note["properties"]["Name"]["title"][0]["text"]["content"],
                "properties": note["properties"],
                "url": note["url"],
            }
            for note in due_notes["results"]
        ]
        return due_notes_formatted

    def fetch_page_content(self, page_id: str) -> str:
        """
        Retrieve the content of a Notion page in markdown format.

        This method interacts with the Notion client to fetch and return the content of a specific Notion page
        identified by its unique page ID. The content is returned as a markdown-formatted string, which can be
        used for further processing or display.

        Args:
            page_id (str): The unique identifier of the Notion page to retrieve.

        Returns:
            str: A markdown-formatted string containing the content of the specified Notion page.
        """
        logger.info(f"TOOL_USAGE: Fetching content for page ID: {page_id}")
        markdown_content = self.notion_client.fetch_page_markdown(page_id)
        return markdown_content

    def fetch_dsa_problem(self) -> Dict[str, Any] | None:
        """
        Retrieve a DSA problem that is due for revision from the Notion database.

        This method interacts with the Notion client to fetch a DSA problem that is marked as due for revision.
        It processes the raw data returned by the Notion API and formats it into a dictionary,
        where the dictionary contains the problem's ID, title, properties, and URL.

        Returns:
            Dict[str, Any] | None: A dictionary representing a due DSA problem with its details, or None if not found.
        """
        logger.info("TOOL_USAGE: Fetching due DSA problem from Notion")
        response = self.notion_client.fetch_due_notes(SETTINGS.notion_dsa_db_id)
        selected_problem = select_dsa_problem(response.get("results", []))
        if not selected_problem:
            return None
        problem_formatted = {
            "page_id": selected_problem["id"],
            "title": selected_problem["properties"]["Problem"]["title"][0]["text"][
                "content"
            ],
            "properties": selected_problem["properties"],
            "url": selected_problem["url"],
        }
        return problem_formatted

    def log_revision(
        self, page_id: str, effort: Literal["Low", "Medium", "High", None] = None
    ) -> bool:
        """
        Logs a revision entry for a specified Notion page.

        This method records a revision for the Notion page identified by the provided page_id.
        It utilizes the Notion client to perform the logging operation and returns a boolean
        indicating the success of the action.

        Args:
            page_id (str): The unique identifier of the Notion page for which the revision is to be logged.
            effort (Literal["Low", "Medium", "High", None]): The effort level of the revision. Defaults to None.

        Returns:
            bool: True if the revision was successfully logged in Notion, False otherwise.
        """
        logger.info(f"TOOL_USAGE: Logging revision for page ID: {page_id}")
        updated_page = self.notion_client.log_revision(page_id, effort)
        if updated_page:
            return True
        return False

    def as_tools(self) -> List[StructuredTool]:
        return [
            StructuredTool.from_function(
                name="fetch_due_notes",
                func=self.fetch_due_notes,
            ),
            StructuredTool.from_function(
                name="fetch_dsa_problem",
                func=self.fetch_dsa_problem,
            ),
            StructuredTool.from_function(
                name="fetch_page_content",
                func=self.fetch_page_content,
            ),
            StructuredTool.from_function(
                name="log_revision",
                func=self.log_revision,
            ),
        ]

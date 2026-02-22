import time
from datetime import date
from typing import Dict, Any, Literal
from config.config import SETTINGS
from utils.notion_utils import (
    create_due_today_filters,
    create_page_properties,
    flatten_nested_lists,
)
from utils.martian import MartianRunner
from notion2md.exporter.block import StringExporter
from notion_client import client


class NotionClient:
    def __init__(self):
        self.martian = MartianRunner()
        self.client = client.Client(auth=SETTINGS.notion_token)

    def fetch_page_markdown(self, page_id: str):
        return StringExporter(block_id=page_id, token=SETTINGS.notion_token).export()

    def create_notion_page(self, title: str, markdown: str, resource_tag: str) -> Dict:
        updated_md = flatten_nested_lists(markdown)
        blocks = self.martian.run(updated_md)
        properties = create_page_properties(title=title, resource_tag=resource_tag)

        # Notion API allows max 100 blocks per request
        initial_blocks = blocks[:100]
        remaining_blocks = blocks[100:]

        # Create the page with initial blocks
        response: Any = self.client.pages.create(
            parent={"database_id": SETTINGS.notion_knowledge_db_id},
            properties=properties,
            children=initial_blocks,
        )
        if not response:
            raise Exception("Failed to create Notion page")

        page_id = response["id"]

        # Append remaining blocks in batches of 100
        for i in range(0, len(remaining_blocks), 100):
            batch = remaining_blocks[i : i + 100]
            self.client.blocks.children.append(block_id=page_id, children=batch)
            if i + 100 < len(remaining_blocks):
                time.sleep(1)  # Avoid rate limits

        return response

    def fetch_due_notes(self, database_id: str) -> Dict[str, Any]:
        response: Any = self.client.databases.query(
            database_id=database_id,
            filter=create_due_today_filters(),
        )
        return response

    def _fetch_page_properties(self, page_id: str) -> Dict[str, Any]:
        page_object: Any = self.client.pages.retrieve(page_id=page_id)
        return page_object.get("properties", {})

    def _update_page_properties(
        self, page_id: str, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        updated_page: Any = self.client.pages.update(
            page_id=page_id, properties=properties
        )
        return updated_page

    def log_revision(
        self, page_id: str, effort: Literal["Low", "Medium", "High", None] = None
    ) -> bool:
        props = self._fetch_page_properties(page_id)
        last_review_data = props.get("Last Review", {}).get("date", {}).get("start", "")
        current_date = date.today().strftime("%Y-%m-%d")
        if last_review_data == current_date:
            return True
        current_revision_count = int(props.get("Revisions", {}).get("number", 0) or 0)
        updated_props = {
            "Revisions": {"number": min(current_revision_count + 1, 5)},
            "Last Review": {"date": {"start": current_date}},
        }
        if props.get("Effort") and effort:
            updated_props["Effort"] = {"select": {"name": f"{effort}"}}
        self._update_page_properties(page_id, properties=updated_props)
        return True

from ast import List
from typing import Dict, Any, List
from clients import init_notion_client
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("DemoServer", stateless_http=True)


@mcp.tool()
def fetch_due_notes() -> List[Dict[str, Any]]:
    """Fetch notes due for revision from Notion database."""
    print("Fetching due notes from Notion...")
    notion_client = init_notion_client()
    due_notes = notion_client.fetch_due_notes()
    due_notes_formatted = [
        {
            "id": note["id"],
            "title": note["properties"]["Name"]["title"][0]["text"]["content"],
            "properties": note["properties"],
            "url": note["url"],
        }
        for note in due_notes["results"]
    ]
    return due_notes_formatted


if __name__ == "__main__":
    # Run Streamable HTTP transport (recommended over SSE for production)
    # This starts an ASGI app at /mcp (default path) on http://127.0.0.1:8000
    mcp.run(transport="streamable-http")

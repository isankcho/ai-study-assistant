import re, random
from datetime import datetime, date
from typing import Dict


def create_page_properties(
    title: str,
    resource_tag: str,
    revisions: int = 0,
) -> Dict:
    created_str = datetime.now().strftime("%Y-%m-%d")
    props: Dict = {
        "Name": {"title": [{"text": {"content": title[:200]}}]},
        "Created Date": {"date": {"start": created_str}},
        "Last Review": {"date": {"start": created_str}},
        "Revisions": {"number": revisions},
    }
    if resource_tag:
        props["Resource Tag"] = {"select": {"name": resource_tag}}
    return props


def create_due_today_filters() -> Dict:
    today = date.today()
    formatted_date = today.strftime("%Y-%m-%d")
    return {
        "property": "Next Review",
        "formula": {"date": {"on_or_before": formatted_date}},
    }


def flatten_nested_lists(markdown: str, indent_size: int = 2) -> str:
    processed_lines = []
    lines = markdown.split("\n")
    max_level = 2

    # Regex to capture indentation, bullet (*, -, +), and content of a list item.
    list_item_pattern = re.compile(r"^(\s*)([*\-+])\s+(.*)$")

    for line in lines:
        match = list_item_pattern.match(line)

        if match:
            indentation_str, bullet, content = match.groups()
            nesting_level = len(indentation_str) // indent_size

            # Apply arrow notation for indent level 3 (nesting_level 2) and deeper.
            if nesting_level > max_level:
                arrow_prefix = "-" * (nesting_level - 1) + "> "
                new_content = f"{arrow_prefix}{content}"
                new_indentation = " " * (max_level * indent_size)
                new_line = f"{new_indentation}{bullet} {new_content}"
                processed_lines.append(new_line)
            else:
                processed_lines.append(line)
        else:
            processed_lines.append(line)

    return "\n".join(processed_lines)


def select_dsa_problem(problems):
    if not problems:
        return None

    effort_weights = {"Hard": 3, "Medium": 2}
    weights = [
        effort_weights.get(
            (problem.get("properties", {}).get("Effort", {}).get("select") or {}).get(
                "name", ""
            ),
            1,
        )
        for problem in problems
    ]
    return random.choices(problems, weights=weights, k=1)[0]

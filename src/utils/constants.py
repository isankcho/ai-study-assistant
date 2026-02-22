from enum import Enum

INGESTION_WORKFLOW_STEP_COUNT = 7
STATE_KEYS = [
    "due_notes",
    "notes_md",
    "messages",
    "questions",
    "current_question_idx",
    "qna",
    "selected_notion_page",
    "quiz_generated",
    "quiz_evaluated",
    "evaluation_output",
    "ingestion_in_progress",
    "revision_in_progress",
    "revision_logged",
    "chatbot_messages",
    "chatbot_turn",
]


class Label(Enum):
    CHAPTER_NAME = "Chapter Name"
    RESOURCE_TAG = "Resource Tag"
    CONTEXT = "Additional Context (optional)"
    FILE_UPLOAD = "Upload notes images"
    SUBMIT_BUTTON = "Submit"
    MANDATORY_FIELD_MARKER = "*"


class Keys(Enum):
    CHAPTER_NAME = "chapter_name"
    RESOURCE_TAG = "resource_tag"
    CONTEXT = "additional_context"
    FILE_UPLOAD = "files"


class EnvConstants(Enum):
    S3_BUCKET_NAME = "S3_BUCKET_NAME"


class ChunkConstants(Enum):
    SIZE_LIMIT_TOKENS = 1200
    CHUNK_SIZE_TOKENS = 900
    CHUNK_OVERLAP_TOKENS = 120
    HEADERS_TO_SPLIT_ON = [
        ("##", "Summary"),
        ("##", "Cues & Key Terms"),
        ("##", "Notes"),
    ]
    SEPARATORS = [
        "\n## ",
        "\n### ",
        "\n#### ",
        "\n\n",
        ". ",
        " ",
        "",
    ]


class Pages(Enum):
    CHATBOT = {
        "key": "chat",
        "title": ":material/smart_toy: Chatbot",
    }
    UPLOAD_NOTES = {
        "key": "capture",
        "title": ":material/sticky_note: Note Capture",
    }
    REVISION = {
        "key": "revision",
        "title": ":material/replay: Revision Mode",
    }

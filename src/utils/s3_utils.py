import re
import hashlib, mimetypes
from pathlib import Path
from streamlit.runtime.uploaded_file_manager import UploadedFile
from slugify import slugify


def _canonical_chapter(name: str) -> str:
    if not name:
        return "chapter-unknown"

    match = re.search(r"\d+", name)
    if match:
        num = int(match.group())
        return f"chapter-{num:02d}"
    else:
        slug = slugify(name)
        return f"chapter-{slug}" if slug else "chapter-unknown"


def make_s3_prefix(resource_tag: str, chapter_name: str) -> str:
    tag = slugify(resource_tag)
    chapter = _canonical_chapter(chapter_name)
    if not tag:
        raise ValueError("Resource tag cannot be empty after sanitization.")
    return f"active/{tag}/{chapter}/"


def _hash_bytes(b: bytes, n: int = 16) -> str:
    return hashlib.sha256(b).hexdigest()[:n]


def safe_filename(file: UploadedFile) -> str:
    p = Path(file.name)
    stem = slugify(p.stem) or "file"
    file.seek(0)
    data = file.getvalue()
    sig = _hash_bytes(data)
    ext = (p.suffix or "").lower()
    return f"{stem}-{sig}{ext}"


def detect_content_type(
    filename: str, fallback: str = "application/octet-stream"
) -> str:
    ctype, _ = mimetypes.guess_type(filename)
    return ctype or fallback

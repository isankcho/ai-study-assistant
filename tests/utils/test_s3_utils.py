import pytest
from unittest.mock import MagicMock

from utils.s3_utils import (
    slugify,
    _canonical_chapter,
    make_s3_prefix,
    _hash_bytes,
    safe_filename,
    detect_content_type,
)


def test_slugify_basic():
    assert slugify("Hello World!") == "hello-world"
    assert slugify("C++ & Python@2024") == "c-python-2024"
    assert slugify("") == ""
    assert slugify("!!!") == ""
    assert slugify("Café") == "cafe"
    assert slugify("  Hello  ") == "hello"


def test_canonical_chapter_with_number():
    assert _canonical_chapter("Chapter 5: Foo") == "chapter-05"
    assert _canonical_chapter("ch2") == "chapter-02"


def test_canonical_chapter_without_number():
    assert _canonical_chapter("Introduction") == "chapter-introduction"
    assert _canonical_chapter("") == "chapter-unknown"
    assert _canonical_chapter("!!!") == "chapter-unknown"


def test_make_s3_prefix_normal():
    prefix = make_s3_prefix("My Book", "Chapter 3: Bar")
    assert prefix == "active/my-book/chapter-03/"


def test_make_s3_prefix_empty_tag():
    with pytest.raises(ValueError):
        make_s3_prefix("!!!", "Chapter 1")


def test_hash_bytes_length():
    b = b"hello world"
    h = _hash_bytes(b, n=8)
    assert isinstance(h, str)
    assert len(h) == 8
    # Check deterministic
    assert h == _hash_bytes(b, n=8)


def test_safe_filename_basic():
    # Mock UploadedFile
    mock_file = MagicMock()
    mock_file.name = "My File.pdf"
    mock_file.getvalue.return_value = b"filecontent"
    # .seek is called but does nothing
    mock_file.seek.return_value = None
    result = safe_filename(mock_file)
    assert result.startswith("my-file-")
    assert result.endswith(".pdf")
    assert len(result.split("-")[-1].split(".")[0]) == 16  # hash length


def test_detect_content_type_known():
    assert detect_content_type("foo.pdf") == "application/pdf"
    assert detect_content_type("foo.txt") == "text/plain"


def test_detect_content_type_unknown():
    assert detect_content_type("foo.unknown", fallback="foo/bar") == "foo/bar"
    assert detect_content_type("foo", fallback="baz/qux") == "baz/qux"

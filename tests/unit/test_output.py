"""Unit tests for the shared output helpers (used by both CLI and API)."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.output import derive_filename, final_answer_text, write_markdown


def test_final_answer_prefers_last_writer_message():
    messages = [
        HumanMessage(content="q", name="User"),
        AIMessage(content="research", name="ScienceResearcher"),
        AIMessage(content="the answer", name="Writer"),
        AIMessage(content="more research", name="ScienceResearcher"),  # after Writer
    ]
    assert final_answer_text(messages) == "the answer"


def test_final_answer_falls_back_to_last_and_empty():
    assert final_answer_text([AIMessage(content="tail", name="X")]) == "tail"
    assert final_answer_text([]) == ""


def test_write_markdown_uses_basename_into_output_dir(tmp_path):
    # Any leading directories are stripped; the file lands in output_dir.
    target = write_markdown("body", "/somewhere/else/report", str(tmp_path))
    assert target == str(tmp_path / "report.md")
    assert (tmp_path / "report.md").read_text(encoding="utf-8") == "body\n"
    assert not (tmp_path / "somewhere").exists()


def test_write_markdown_rejects_empty_basename(tmp_path):
    with pytest.raises(ValueError, match="no filename"):
        write_markdown("body", "foo/", str(tmp_path))


def test_derive_filename_slugifies_prompt():
    assert derive_filename("What are the latest BYD models?") == "what-are-the-latest-byd-models"
    assert derive_filename("  Hello,   World!  ") == "hello-world"


def test_derive_filename_falls_back_when_empty():
    assert derive_filename("!!!") == "answer"
    assert derive_filename("") == "answer"


def test_derive_filename_caps_length():
    assert len(derive_filename("word " * 100)) <= 60

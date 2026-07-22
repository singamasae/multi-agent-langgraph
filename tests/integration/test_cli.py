"""Integration tests for the CLI entry point (no real model/network)."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import ValidationError

from app.interfaces.cli import _final_answer_text, main


def test_final_answer_prefers_last_writer_message():
    messages = [
        HumanMessage(content="q", name="User"),
        AIMessage(content="research", name="ScienceResearcher"),
        AIMessage(content="the answer", name="Writer"),
        AIMessage(content="more research", name="ScienceResearcher"),  # routed after Writer
    ]
    # Must return the Writer's answer, not the trailing Researcher message.
    assert _final_answer_text(messages) == "the answer"


def test_final_answer_empty_when_writer_text_is_blank():
    messages = [AIMessage(content=[{"type": "reasoning", "reasoning": "…"}], name="Writer")]
    assert _final_answer_text(messages) == ""


def test_cli_prints_writer_answer_and_exits_zero(mocker, capsys, monkeypatch, fake_deps):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    from app.config import Settings

    mocker.patch(
        "app.interfaces.cli._load_settings", return_value=Settings(_env_file=None)
    )
    mocker.patch(
        "app.interfaces.cli.build_dependencies",
        return_value=fake_deps(writer_content="ANSWER-XYZ"),
    )

    exit_code = main(["What is new in small language models?"])

    assert exit_code == 0
    assert "ANSWER-XYZ" in capsys.readouterr().out


def test_cli_writes_final_answer_to_markdown_file(
    mocker, capsys, monkeypatch, tmp_path, fake_deps
):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    from app.config import Settings

    mocker.patch(
        "app.interfaces.cli._load_settings", return_value=Settings(_env_file=None)
    )
    mocker.patch(
        "app.interfaces.cli.build_dependencies",
        return_value=fake_deps(writer_content="# Report\n\nFindings body."),
    )
    out_file = tmp_path / "result.md"

    exit_code = main(["research prompt", "--output", str(out_file)])

    assert exit_code == 0
    assert out_file.read_text(encoding="utf-8") == "# Report\n\nFindings body.\n"
    # A confirmation (with the path) is printed; the answer body is not dumped to stdout.
    stdout = capsys.readouterr().out
    assert str(out_file) in stdout
    assert "Findings body." not in stdout


def test_cli_handles_list_content_from_the_model(
    mocker, monkeypatch, tmp_path, fake_deps
):
    # Real Gemini responses may arrive as a list of content blocks rather than a
    # plain string; the CLI must normalise that before writing the file.
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    from app.config import Settings

    mocker.patch(
        "app.interfaces.cli._load_settings", return_value=Settings(_env_file=None)
    )
    mocker.patch(
        "app.interfaces.cli.build_dependencies",
        return_value=fake_deps(
            writer_content=[
                {"type": "text", "text": "# Title"},
                {"type": "text", "text": "\n\nBody"},
            ]
        ),
    )
    out_file = tmp_path / "result.md"

    exit_code = main(["prompt", "-o", str(out_file)])

    assert exit_code == 0
    assert out_file.read_text(encoding="utf-8") == "# Title\n\nBody\n"


def test_cli_warns_and_writes_nothing_on_empty_answer(
    mocker, capsys, monkeypatch, tmp_path, fake_deps
):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    from app.config import Settings

    mocker.patch(
        "app.interfaces.cli._load_settings", return_value=Settings(_env_file=None)
    )
    mocker.patch(
        "app.interfaces.cli.build_dependencies",
        return_value=fake_deps(writer_content=""),  # model produced no text
    )
    out_file = tmp_path / "result.md"

    exit_code = main(["prompt", "-o", str(out_file)])

    assert exit_code == 1
    assert not out_file.exists()  # no empty file left behind
    assert "empty answer" in capsys.readouterr().err


def test_cli_appends_md_extension_when_missing(
    mocker, monkeypatch, tmp_path, fake_deps
):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    from app.config import Settings

    mocker.patch(
        "app.interfaces.cli._load_settings", return_value=Settings(_env_file=None)
    )
    mocker.patch(
        "app.interfaces.cli.build_dependencies",
        return_value=fake_deps(writer_content="body"),
    )

    main(["prompt", "-o", str(tmp_path / "report")])

    assert (tmp_path / "report.md").exists()


def test_cli_fails_fast_on_config_error(mocker, capsys, monkeypatch):
    # Produce a real ValidationError by constructing Settings with no key.
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    from app.config import Settings

    try:
        Settings(_env_file=None)
        pytest.fail("expected Settings to raise without an API key")
    except ValidationError as exc:
        config_error = exc

    mocker.patch("app.interfaces.cli._load_settings", side_effect=config_error)

    exit_code = main(["any prompt"])

    assert exit_code == 1
    assert "Configuration error" in capsys.readouterr().err

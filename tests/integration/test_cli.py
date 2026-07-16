"""Integration tests for the CLI entry point (no real model/network)."""

import pytest
from pydantic import ValidationError

from app.interfaces.cli import main


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

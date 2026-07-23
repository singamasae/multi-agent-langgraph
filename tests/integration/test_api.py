"""Integration tests for the LangServe API (graph backed by fakes)."""

from fastapi.testclient import TestClient

from app.interfaces.api import create_app


def _client(mocker, monkeypatch, fake_deps, writer_content="API-ANSWER", settings=None):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    from app.config import Settings

    mocker.patch(
        "app.interfaces.api.build_dependencies",
        return_value=fake_deps(writer_content=writer_content),
    )
    app = create_app(settings or Settings(_env_file=None))
    return TestClient(app)


def test_root_redirects_to_docs(mocker, monkeypatch, fake_deps):
    client = _client(mocker, monkeypatch, fake_deps)
    response = client.get("/")
    assert response.status_code == 200  # TestClient follows the redirect to /docs


def test_invoke_returns_writer_answer(mocker, monkeypatch, fake_deps):
    client = _client(mocker, monkeypatch, fake_deps, writer_content="API-ANSWER-123")

    response = client.post(
        "/research/invoke",
        json={
            "input": {
                "messages": [{"type": "human", "content": "hello"}],
                "next": "",
            }
        },
    )

    assert response.status_code == 200
    assert "API-ANSWER-123" in response.text


def test_ui_page_is_served(mocker, monkeypatch, fake_deps):
    client = _client(mocker, monkeypatch, fake_deps)
    response = client.get("/ui")

    assert response.status_code == 200
    # The demo drives the built-in stream endpoint and shows the three states.
    assert "/research/stream" in response.text
    assert "started" in response.text and "working" in response.text


def test_stream_emits_sse_started_working_finished_signal(
    mocker, monkeypatch, fake_deps
):
    # The front-end maps SSE event names to status: data -> working, end ->
    # finished. Proving both reach the client proves the status signal works.
    client = _client(mocker, monkeypatch, fake_deps, writer_content="STREAMED")

    with client.stream(
        "POST",
        "/research/stream",
        json={"input": {"messages": [{"type": "human", "content": "hi"}], "next": ""}},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert "event: data" in body
    assert "event: end" in body


def test_run_streams_per_agent_status_and_writes_file(
    mocker, monkeypatch, tmp_path, fake_deps
):
    from app.config import Settings

    client = _client(
        mocker,
        monkeypatch,
        fake_deps,
        writer_content="# Report\n\nAll done.",
        settings=Settings(_env_file=None, output_dir=str(tmp_path)),
    )

    with client.stream(
        "POST", "/run", json={"prompt": "Latest BYD models"}
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    # Per-agent status detail reaches the client (default route hits Science).
    assert '"phase": "researching"' in body
    assert '"agent": "ScienceResearcher"' in body
    assert '"phase": "writing"' in body
    assert "event: result" in body
    assert "event: end" in body

    # The answer was persisted into OUTPUT_DIR under a slug of the prompt.
    saved = tmp_path / "latest-byd-models.md"
    assert saved.read_text(encoding="utf-8") == "# Report\n\nAll done.\n"


def test_run_empty_answer_errors_without_writing(
    mocker, monkeypatch, tmp_path, fake_deps
):
    from app.config import Settings

    client = _client(
        mocker,
        monkeypatch,
        fake_deps,
        writer_content="",  # model produced no text
        settings=Settings(_env_file=None, output_dir=str(tmp_path)),
    )

    with client.stream("POST", "/run", json={"prompt": "anything"}) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert "event: error" in body
    assert "empty answer" in body
    assert list(tmp_path.iterdir()) == []  # nothing written


def test_cors_headers_present_only_when_configured(mocker, monkeypatch, fake_deps):
    from app.config import Settings

    origin = "http://localhost:3000"

    # Configured: the allowed origin is echoed back.
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    with_cors = _client(
        mocker,
        monkeypatch,
        fake_deps,
        settings=Settings(_env_file=None, cors_allow_origins=origin),
    )
    resp = with_cors.get("/", headers={"Origin": origin})
    assert resp.headers.get("access-control-allow-origin") == origin

    # Default (empty): no CORS middleware, so no such header.
    without_cors = _client(mocker, monkeypatch, fake_deps)
    resp = without_cors.get("/", headers={"Origin": origin})
    assert "access-control-allow-origin" not in resp.headers

"""Integration tests for the LangServe API (graph backed by fakes)."""

from fastapi.testclient import TestClient

from app.interfaces.api import create_app


def _client(mocker, monkeypatch, fake_deps, writer_content="API-ANSWER"):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    from app.config import Settings

    mocker.patch(
        "app.interfaces.api.build_dependencies",
        return_value=fake_deps(writer_content=writer_content),
    )
    app = create_app(Settings(_env_file=None))
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

# Testing

The suite is **fully offline** — it requires no `GOOGLE_API_KEY` and makes no network calls. This is a deliberate design property, enabled by dependency injection.

## Running

```bash
pip install -r requirements.txt -r requirements-dev.txt

pytest -q                                        # full suite (30 tests)
pytest tests/unit/test_supervisor.py -q          # one file
pytest tests/unit/test_config.py::test_missing_api_key_fails_fast   # one test

ruff check src tests main.py serve.py            # lint
mypy src/app                                     # type-check
```

`pytest.ini` sets `pythonpath = src` so `import app` works without installing the package, and filters third-party deprecation warnings (langchain-community, starlette testclient, langserve) so our own code stays warning-clean.

## Strategy: mock at the injection boundary

The two external boundaries — the **Gemini LLM** and **DuckDuckGo search** — are the only things faked, and they are substituted via `GraphDependencies`, not by patching deep internals or the network layer.

Test doubles live in `tests/fakes.py`:

| Fake | Stands in for | Behaviour |
|------|---------------|-----------|
| `ScriptedSupervisor` | the supervisor runnable | Returns a preset sequence of routing decisions, then `FINISH` forever (guarantees loop termination). |
| `FakeReactAgent` | `create_react_agent` result | `.invoke` returns `{"messages": [...]}`; the node should surface only the last. |
| `FakeWriterAgent` | the writer chain | `.invoke` returns an `AIMessage` with fixed content. |

Shared fixtures live in `tests/conftest.py`:

- `settings` — a hermetic `Settings(_env_file=None)` with a test key and a small `recursion_limit`.
- `fake_deps` — a factory that assembles a `GraphDependencies` from the fakes, taking a `route_sequence` and canned outputs so a test can drive an exact path through the compiled graph.

## Layout

```
tests/
├── conftest.py                 # fixtures (settings, fake_deps)
├── fakes.py                    # test doubles
├── unit/
│   ├── test_constants.py       # roster SSOT; RouteResponse Literal matches ROUTE_OPTIONS
│   ├── test_config.py          # fail-fast, env overrides, SecretStr masking, caching
│   ├── test_state.py           # messages reducer appends
│   ├── test_llm.py             # role → (model, temperature) mapping; unknown role rejected
│   ├── test_search_tool.py     # configured max_results (no network)
│   ├── test_supervisor.py      # node returns {"next": …}, adds no messages
│   ├── test_researcher.py      # emits only last message, tagged name="Researcher"
│   ├── test_writer.py          # tags name="Writer"; real build path via fake chat model
│   └── test_graph_builder.py   # composition-root wiring + graph topology
└── integration/
    ├── test_graph_flow.py      # full compiled graph: routes Researcher→Writer→FINISH; recursion cap trips
    ├── test_cli.py             # main() prints answer / fails fast on config error
    └── test_api.py             # FastAPI TestClient: / redirect + POST /research/invoke
```

## Highest-value tests

- **`test_graph_flow.py`** exercises the entire wiring — conditional edges, worker→supervisor return edges, the `operator.add` reducer, and recursion termination — in one offline run with a scripted supervisor.
- **`test_api.py`** exercises the real LangServe schema generation (this is the test that caught the `typing_extensions.TypedDict` requirement on Python < 3.12).

## Writing new tests

- Never require a real key or network. Inject fakes via `fake_deps` / mock at the `GraphDependencies` boundary.
- Construct config with `Settings(_env_file=None)` + `monkeypatch.setenv(...)` so tests don't read the repo's real `.env`.
- Follow the project's TDD flow (see [development.md](development.md)): write the failing test first.

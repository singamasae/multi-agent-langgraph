# Development Guide

## Workflow: Explore → Plan → Code → Verify → Commit

1. **Explore** — read the relevant modules (and this folder) before changing anything. Reuse the existing `build_*` / `make_*` factories and the `Settings` seam rather than adding new ones.
2. **Plan** — state the approach and the test(s) before writing code.
3. **Code** — TDD: write the failing test first, then the implementation. All comments/descriptions in **English**. Never hardcode config (add a field to `Settings`); never construct a Gemini client or the search tool inside a node (inject via `GraphDependencies`).
4. **Verify** — `pytest -q` green **offline** (no `GOOGLE_API_KEY`), then `ruff` and `mypy` clean, then a manual smoke of the CLI and API.
5. **Commit** — only when the user asks. Conventional message.

## Invariants (do not break)

- Worker `AIMessage`s carry `name=` (`"Researcher"` / `"Writer"`) — routing and output depend on it.
- The researcher node surfaces only the ReAct agent's **last** message (intermediate tool chatter is dropped).
- The roster lives once in `constants.AgentName`; `MEMBERS` / `ROUTE_OPTIONS` derive from it, and `test_supervisor` guards that `RouteResponse`'s `Literal` still agrees.
- Tests must never require a real key or network — mock at the `GraphDependencies` boundary.
- Only `llm.py` constructs a Gemini client; only `graph/dependencies.py` assembles real agents/tools.

## Commands

```bash
# setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env            # set GOOGLE_API_KEY

# run
python main.py "Your research prompt here"    # CLI
python serve.py                               # API (host/port from config)

# verify
pytest -q
ruff check src tests main.py serve.py
mypy src/app
```

## Adding a new agent

The roster is centralised, so a new worker is a small, well-defined change:

1. **Register the name** in `constants.AgentName` and extend `RouteResponse`'s `Literal` in `agents/supervisor.py`. (`MEMBERS` / `ROUTE_OPTIONS` update automatically; `test_supervisor` verifies the two stay in sync.)
2. **Create `agents/<name>.py`** with:
   - `build_<name>_*(llm[, tools]) -> Runnable` (pure factory), and
   - `make_<name>_node(runnable) -> (state) -> {"messages": [AIMessage(..., name="<Name>")]}`.
3. **Wire it in the graph:**
   - add its runnable to `GraphDependencies` and build it in `build_dependencies` (`graph/dependencies.py`);
   - add the node and a `<Name> → Supervisor` edge in `build_graph` (`graph/builder.py`). The conditional map derives from `MEMBERS`.
4. **Test it** — a node-contract unit test plus a routing case in `test_graph_flow.py` using `fake_deps`.

## Entry points: why `main.py` / `serve.py` live at the repo root

They are **launch scripts, not library code** — how you *start* the app, not part of its importable API. Keeping them at the root (rather than inside `src/app/`) is intentional: putting `main.py` in the package would make it an importable `app.main` that should never be imported.

Each is a thin shim that adds `src/` to `sys.path` and calls into `interfaces/`. That `sys.path` insert is the one concession to the project not being pip-installable (deps are managed via `requirements.txt`, not `pyproject.toml`).

If the project should become truly installable later, the clean upgrade is a minimal `pyproject.toml` with `[project.scripts]` console entry points — that removes the `sys.path` shim entirely and lets `import app` work everywhere without `pytest.ini`'s `pythonpath`. Dependencies can stay in `requirements.txt`.

## Stack notes (Python 3.10)

- **LangChain 1.x / LangGraph 1.x** are installed (not the old 0.x). Consequences baked into the code:
  - `create_react_agent` uses `prompt=` (the old `state_modifier=` was removed).
  - `AgentState` uses `typing_extensions.TypedDict`, not `typing.TypedDict` — LangServe's pydantic schema generation requires it on Python < 3.12.
- The DuckDuckGo tool comes from `langchain-community` (being sunset) and now delegates to the **`ddgs`** package. Both are pinned in `requirements.txt`; the sunset `DeprecationWarning` is filtered in `pytest.ini`.
- `AgentName` subclasses `(str, Enum)` because `enum.StrEnum` is 3.11+.
- The langgraph `add_node` stubs don't infer plain `(state) -> dict` node callables, so those three calls in `graph/builder.py` carry a localised `# type: ignore[call-overload]` — this is third-party typing friction, not a real type error.

## Dependencies

- `requirements.txt` — runtime, pinned to tested versions.
- `requirements-dev.txt` — `pytest`, `pytest-mock`, `httpx`, `ruff`, `mypy`.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`aaas_mvp` ("Agent-as-a-Service" MVP) is a supervisor/worker multi-agent research-and-writing workflow built on LangGraph and Google Gemini, with DuckDuckGo web search. It runs as either a one-shot CLI or a LangServe REST API, over a single shared graph.

The codebase follows a clean-architecture layering with dependency injection, 12-factor configuration, and a test suite that runs fully offline.

## Project blueprint (read first)

The full design blueprint lives in **[`docs/`](docs/README.md)** — read it before non-trivial changes. This file is the quick reference; `docs/` is the deeper source of truth.

- [`docs/architecture.md`](docs/architecture.md) — layers, graph control flow, module responsibilities
- [`docs/configuration.md`](docs/configuration.md) — settings & environment variables
- [`docs/testing.md`](docs/testing.md) — test strategy and how to run
- [`docs/development.md`](docs/development.md) — workflow, invariants, adding an agent

## Commands

Setup (a `venv/` is committed; recreate if needed):

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # then set GOOGLE_API_KEY to a real Gemini key
```

Run:

```bash
python main.py "Your research prompt here"   # CLI; prints the final answer, diagnostics go to the log
python serve.py                               # API on the configured host/port (default 127.0.0.1:8000)
```

Verify (all run offline — no API key, no network):

```bash
pytest -q                                        # full suite
pytest tests/unit/test_supervisor.py -q          # one file
pytest tests/unit/test_config.py::test_missing_api_key_fails_fast   # one test
ruff check src tests main.py serve.py            # lint
mypy src/app                                    # type-check
```

## Architecture

Layered so that domain logic never touches external SDKs directly and the whole graph is testable with fakes.

```
src/app/
  constants.py        AgentName enum — single source of truth for the roster
  config.py           Settings (pydantic-settings) + get_settings()
  llm.py              build_chat_model(role, settings) — ONLY place a Gemini client is constructed
  logging_config.py   configure_logging(settings)
  state.py            AgentState (typing_extensions.TypedDict; messages reducer = operator.add)
  tools/search.py     build_search_tool(settings)
  agents/             supervisor / researcher / writer
  graph/              dependencies.py (composition root) + builder.py (topology)
  interfaces/         cli.py + api.py
main.py, serve.py     thin shims that add src/ to sys.path and call the interfaces
```

Dependency direction: `interfaces/` → `graph/` → `agents/` + `tools/`. `constants`/`config`/`llm`/`logging` are shared support the edges read.

**Control flow.** `build_graph(deps)` compiles a `StateGraph`: `START → Supervisor`; the supervisor (`gemini-1.5-flash`, structured `RouteResponse`) writes `state["next"]`; conditional edges route to a worker or to `END` on `FINISH`; every worker edges back to the supervisor. The loop is bounded by `settings.recursion_limit`, passed at invoke time. Researcher is a `create_react_agent` with search; Writer is a toolless `gemini-1.5-pro` chain.

**Dependency injection is the core seam.** Each agent module exposes a pure `build_*` factory (takes an injected model/tools, returns a runnable) and a `make_*_node` adapter (wraps it as a LangGraph node). `graph/dependencies.py::build_dependencies(settings)` is the *only* place real models/tools/agents are assembled into a `GraphDependencies`; `build_graph` consumes that dataclass. Tests inject a `GraphDependencies` full of fakes, so no test constructs a real model or hits the network.

## Configuration (12-factor)

All tunables live in `Settings` (`config.py`) and come from the environment (no prefix — each field maps to its uppercased name). `GOOGLE_API_KEY` is required and fail-fast (rejected if missing or still the `.env.example` placeholder). The rest are optional with defaults: `SUPERVISOR_MODEL`/`RESEARCHER_MODEL`/`WRITER_MODEL`, `*_TEMPERATURE`, `SEARCH_MAX_RESULTS`, `RECURSION_LIMIT`, `API_HOST`/`API_PORT`, `LOG_LEVEL`/`LOG_FORMAT`. See `.env.example` for the full list and defaults. The key is a `SecretStr` (never logged). Factories never call `get_settings()` — settings are read once at the edges and passed down.

## Workflow: Explore → Plan → Code → Verify → Commit

1. **Explore** — read the relevant modules before changing anything; reuse the existing `build_*`/`make_*` factories and the `Settings` seam rather than adding new ones.
2. **Plan** — state the approach and the test(s) before writing code.
3. **Code** — TDD: write the failing test first, then the implementation. All comments/descriptions in **English**. Never hardcode config (add a field to `Settings`); never construct a Gemini client or the search tool inside a node (inject it via `GraphDependencies`).
4. **Verify** — `pytest -q` green **offline** (no `GOOGLE_API_KEY`), `ruff` and `mypy` clean, then a manual smoke of the CLI and API.
5. **Commit** — only when the user asks. Conventional message.

## Invariants (do not break)

- **Never read, open, print, cat, log, or otherwise expose the contents of `.env`** (or any real secret value). `.env` holds live credentials. To learn what config exists, read `.env.example` (which contains only placeholders) — never the real `.env`. Do not echo secret values into terminal output, code, commits, test fixtures, or chat, even when debugging. `GOOGLE_API_KEY` is a `SecretStr` precisely so it stays out of logs and reprs; keep it that way.
- Worker `AIMessage`s carry `name=` (`"Researcher"`/`"Writer"`) — routing and output depend on it.
- The researcher node surfaces only the react agent's **last** message (intermediate tool chatter is dropped).
- The roster lives once in `constants.AgentName`; `MEMBERS`/`ROUTE_OPTIONS` derive from it, and `test_supervisor` guards that `RouteResponse`'s `Literal` still agrees.
- Tests must never require a real key or network — mock at the `GraphDependencies` boundary.

### Adding a new agent

1. Add the name to `constants.AgentName` and extend `RouteResponse`'s `Literal` in `agents/supervisor.py`.
2. Create `agents/<name>.py` with `build_<name>_*` + `make_<name>_node` returning `{"messages": [AIMessage(..., name="<Name>")]}`.
3. Wire it in `graph/dependencies.py` (build) and `graph/builder.py` (node + `→ Supervisor` edge). `MEMBERS` picks up the roster automatically.

## Stack notes (Python 3.10)

- LangChain **1.x** / LangGraph **1.x** are installed (not the old 0.x). Consequences baked into the code: `create_react_agent` uses `prompt=` (not the removed `state_modifier=`); `AgentState` uses `typing_extensions.TypedDict` (LangServe's pydantic schema generation requires it on Python < 3.12).
- The DuckDuckGo tool comes from `langchain-community` (being sunset) and now delegates to the `ddgs` package. Both are pinned in `requirements.txt`; the sunset `DeprecationWarning` is filtered in `pytest.ini`.
- `AgentName` subclasses `(str, Enum)` because `enum.StrEnum` is 3.11+.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`aaas_mvp` ("Agent-as-a-Service" MVP) is a supervisor/worker multi-agent research-and-writing workflow built on LangGraph, with pluggable LLM providers (Google Gemini and OpenAI, selectable per role) and DuckDuckGo web search. The research roster is a set of **topic specialists** (Science, Food & Beverage, Technology, Automotive, Art & Culture, Environment/Social); the supervisor analyses the prompt and routes to the best-fit specialist(s) before the Writer composes the answer. It runs as either a one-shot CLI or a LangServe REST API, over a single shared graph.

The codebase follows a clean-architecture layering with dependency injection, 12-factor configuration, and a test suite that runs fully offline.

## Project blueprint (read first)

The full design blueprint lives in **[`docs/`](docs/README.md)** — read it before non-trivial changes. This file is the quick reference; `docs/` is the deeper source of truth.

- [`docs/architecture.md`](docs/architecture.md) — layers, graph control flow, module responsibilities
- [`docs/configuration.md`](docs/configuration.md) — settings & environment variables
- [`docs/testing.md`](docs/testing.md) — test strategy and how to run
- [`docs/development.md`](docs/development.md) — workflow, invariants, adding an agent
- [`docs/deployment.md`](docs/deployment.md) — Docker / docker-compose deployment

## Commands

Setup (a `venv/` is committed; recreate if needed):

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # set GOOGLE_API_KEY (default provider); set OPENAI_API_KEY too if a role uses openai
```

Run:

```bash
python main.py "Your research prompt here"   # CLI; prints the final answer, diagnostics go to the log
python main.py "Your research prompt here" -o report   # write answer to OUTPUT_DIR/report.md (default download/)
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
  constants.py        AgentName enum + RESEARCH_TOPICS registry — single source of truth for the roster (6 topic researchers + writer)
  config.py           Settings (pydantic-settings) + get_settings()
  llm.py              build_chat_model(role, settings) — ONLY place a provider LLM client is built; dispatches per role to Gemini or OpenAI
  logging_config.py   configure_logging(settings)
  state.py            AgentState (typing_extensions.TypedDict; messages reducer = add_messages)
  tools/search.py     build_search_tool(settings)
  agents/             supervisor / researcher / writer
  graph/              dependencies.py (composition root) + builder.py (topology)
  interfaces/         cli.py + api.py
main.py, serve.py     thin shims that add src/ to sys.path and call the interfaces
```

Dependency direction: `interfaces/` → `graph/` → `agents/` + `tools/`. `constants`/`config`/`llm`/`logging` are shared support the edges read.

**Control flow.** `build_graph(deps)` compiles a `StateGraph`: `START → Supervisor`; the supervisor (structured `RouteResponse`; default `gemini-flash-lite-latest`) analyses the prompt and writes the best-fit specialist into `state["next"]`; conditional edges route to a worker or to `END` on `FINISH`; every worker edges back to the supervisor (so a cross-domain request can visit several specialists before the Writer). Deterministic guardrails: research must precede the Writer (a skip is overridden to `DEFAULT_RESEARCHER`), and a premature `FINISH` is redirected to the Writer. The loop is bounded by `settings.recursion_limit`, passed at invoke time. The six topic researchers share **one** `create_react_agent`-with-search implementation, differing only by a `build_topic_system_prompt` prompt; Writer is a toolless chain. Provider and model are per-role settings (`*_PROVIDER` + `*_MODEL`; the researcher settings drive all specialists — see [`docs/configuration.md`](docs/configuration.md)).

**Dependency injection is the core seam.** Each agent module exposes a pure `build_*` factory (takes an injected model/tools, returns a runnable) and a `make_*_node` adapter (wraps it as a LangGraph node). `graph/dependencies.py::build_dependencies(settings)` is the *only* place real models/tools/agents are assembled into a `GraphDependencies`; `build_graph` consumes that dataclass. Tests inject a `GraphDependencies` full of fakes, so no test constructs a real model or hits the network.

## Configuration (12-factor)

All tunables live in `Settings` (`config.py`) and come from the environment (no prefix — each field maps to its uppercased name). Each role picks a provider via `SUPERVISOR_PROVIDER`/`RESEARCHER_PROVIDER`/`WRITER_PROVIDER` (`"google"` | `"openai"`, default `google`). Provider keys `GOOGLE_API_KEY` and `OPENAI_API_KEY` are **fail-fast but only when a role actually uses that provider** (rejected if missing or still the `.env.example` placeholder) — a Gemini-only or OpenAI-only deployment needs just one. The rest are optional with defaults: `SUPERVISOR_MODEL`/`RESEARCHER_MODEL`/`WRITER_MODEL`, `*_TEMPERATURE`, `THINKING_BUDGET` (Gemini-only), `OPENAI_BASE_URL`, `SEARCH_MAX_RESULTS`, `RECURSION_LIMIT`, `OUTPUT_DIR` (CLI `-o` output folder, default `download`), `API_HOST`/`API_PORT`, `LOG_LEVEL`/`LOG_FORMAT`. See `.env.example` for the full list and defaults. Both keys are `SecretStr` (never logged). Factories never call `get_settings()` — settings are read once at the edges and passed down.

## Workflow: Explore → Plan → Code → Verify → Commit

1. **Explore** — read the relevant modules before changing anything; reuse the existing `build_*`/`make_*` factories and the `Settings` seam rather than adding new ones.
2. **Plan** — state the approach and the test(s) before writing code.
3. **Code** — TDD: write the failing test first, then the implementation. All comments/descriptions in **English**. Never hardcode config (add a field to `Settings`); never construct a provider LLM client (Gemini or OpenAI) or the search tool inside a node (inject it via `GraphDependencies`).
4. **Verify** — `pytest -q` green **offline** (no `GOOGLE_API_KEY`), `ruff` and `mypy` clean, then a manual smoke of the CLI and API.
5. **Commit** — only when the user asks. Conventional message.

## Invariants (do not break)

- **Never read, open, print, cat, log, or otherwise expose the contents of `.env`** (or any real secret value). `.env` holds live credentials. To learn what config exists, read `.env.example` (which contains only placeholders) — never the real `.env`. Do not echo secret values into terminal output, code, commits, test fixtures, or chat, even when debugging. `GOOGLE_API_KEY` and `OPENAI_API_KEY` are `SecretStr` precisely so they stay out of logs and reprs; keep it that way.
- Worker `AIMessage`s carry `name=` — a specialist's name (e.g. `"TechnologyResearcher"`) or `"Writer"` — routing and output depend on it; the supervisor's "has research happened?" check keys off the specialist names.
- The researcher node surfaces only the react agent's **last** message (intermediate tool chatter is dropped).
- The roster lives once in `constants.AgentName` + the `RESEARCH_TOPICS` registry; `RESEARCHER_MEMBERS`/`MEMBERS`/`ROUTE_OPTIONS`/`DEFAULT_RESEARCHER` derive from them, and `test_supervisor` guards that `RouteResponse`'s `Literal` still agrees.
- Tests must never require a real key or network — mock at the `GraphDependencies` boundary.

### Adding a new research topic

1. Add the enum member to `constants.AgentName` + a `RESEARCH_TOPICS` entry (focus description).
2. Extend `RouteResponse`'s `Literal` in `agents/supervisor.py` (keep it in `ROUTE_OPTIONS` order).

`build_dependencies` builds the specialist from the registry and `build_graph` adds its node + return edge automatically — no other code changes.

### Adding a new (non-researcher) agent

1. Add the name to `constants.AgentName` and extend `RouteResponse`'s `Literal` in `agents/supervisor.py`.
2. Create `agents/<name>.py` with `build_<name>_*` + `make_<name>_node` returning `{"messages": [AIMessage(..., name="<Name>")]}`.
3. Wire it in `graph/dependencies.py` (build) and `graph/builder.py` (node + `→ Supervisor` edge). `MEMBERS` picks up the roster automatically.

## Stack notes (Python 3.10)

- LangChain **1.x** / LangGraph **1.x** are installed (not the old 0.x). Consequences baked into the code: `create_react_agent` uses `prompt=` (not the removed `state_modifier=`); `AgentState` uses `typing_extensions.TypedDict` (LangServe's pydantic schema generation requires it on Python < 3.12).
- The DuckDuckGo tool comes from `langchain-community` (being sunset) and now delegates to the `ddgs` package. Both are pinned in `requirements.txt`; the sunset `DeprecationWarning` is filtered in `pytest.ini`.
- LLM providers are pluggable per role: `llm.py` builds a Gemini client (`langchain-google-genai`) or an OpenAI client (`langchain-openai`) from the role's `*_PROVIDER`. Both are pinned in `requirements.txt`. To add a provider, extend `VALID_PROVIDERS` in `config.py` and the dispatch in `llm.py` — nothing downstream changes.
- `AgentName` subclasses `(str, Enum)` because `enum.StrEnum` is 3.11+.

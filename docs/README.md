# Project Documentation

This folder is the **blueprint** for `aaas_mvp`. Read it before making changes; it is the source of truth for how the project is designed and why.

> For quick day-to-day commands and hard rules, see `../CLAUDE.md` at the repo root. This folder is the deeper reference `CLAUDE.md` summarises.

## What this project is

A supervisor/worker **multi-agent research-and-writing workflow** built on LangGraph and Google Gemini, with DuckDuckGo web search. A user gives a prompt; a supervisor routes between a **Researcher** (searches the web) and a **Writer** (synthesises a Markdown answer) until the work is done. It ships as both a one-shot **CLI** and a **LangServe HTTP API** over one shared graph.

## Documentation index

| Document | Read it when you need to… |
|----------|---------------------------|
| [architecture.md](architecture.md) | Understand the layers, the graph control flow, and where each responsibility lives. |
| [configuration.md](configuration.md) | Know which settings exist, how they're read (12-factor), and how to override them. |
| [testing.md](testing.md) | Understand the test strategy, what is mocked, and how to run tests. |
| [development.md](development.md) | Follow the workflow, respect the invariants, or add a new agent. |

## The 30-second mental model

- **One package, layered:** `src/app/` with `interfaces → graph → agents/tools`, plus cross-cutting support (`config`, `constants`, `llm`, `logging`, `state`).
- **Dependency injection is the spine.** Real models/tools/agents are assembled in exactly one place (`graph/dependencies.py`) and injected into the graph. Everything else receives its collaborators — so the whole graph is testable with fakes and **no test needs an API key or network**.
- **Config is 12-factor.** Every tunable lives in `Settings` (`config.py`) and comes from the environment. Nothing is hardcoded; nothing constructs a Gemini client except `llm.py`.
- **The roster has one source of truth:** `constants.AgentName`.

## Repository layout

```
aaas_mvp/
├── docs/                     # this folder — the project blueprint
├── CLAUDE.md                 # quick reference for agents (commands + rules)
├── main.py                   # CLI launch shim  -> app.interfaces.cli
├── serve.py                  # API launch shim  -> app.interfaces.api
├── requirements.txt          # runtime deps (pinned)
├── requirements-dev.txt      # test/lint/type-check deps
├── pytest.ini / mypy.ini     # tooling config
├── .env.example              # documented env vars
├── src/app/                  # the importable package (see architecture.md)
└── tests/                    # unit + integration tests (see testing.md)
```

# Configuration

The project follows **12-factor** config: every tunable comes from the environment, is typed and validated once at startup, and is never hardcoded in the domain.

## How it works

- All config lives in a single `Settings` class (`src/app/config.py`, built on `pydantic-settings`).
- Values are read from **environment variables** and/or a local **`.env`** file (env vars win).
- **No prefix** — each field maps to its uppercased name (`writer_model` → `WRITER_MODEL`).
- `get_settings()` returns a cached instance; tests build `Settings(_env_file=None)` for a hermetic read.
- **Factories never call `get_settings()`.** The composition root and the interfaces read settings once at the edges and pass concrete values down.

## Environment variables

| Variable | Default | Notes |
|----------|---------|-------|
| `GOOGLE_API_KEY` | *(required)* | Gemini API key. Stored as `SecretStr` (never logged). **Fail-fast**: missing or the `.env.example` placeholder raises at startup. |
| `SUPERVISOR_MODEL` | `gemini-1.5-flash` | Router model. |
| `RESEARCHER_MODEL` | `gemini-1.5-flash` | ReAct researcher model. |
| `WRITER_MODEL` | `gemini-1.5-pro` | Writer model. |
| `SUPERVISOR_TEMPERATURE` | `0.0` | |
| `RESEARCHER_TEMPERATURE` | `0.0` | |
| `WRITER_TEMPERATURE` | `0.7` | |
| `SEARCH_MAX_RESULTS` | `3` | DuckDuckGo result count. |
| `RECURSION_LIMIT` | `20` | Safety bound on the supervisor/worker loop. |
| `API_HOST` | `127.0.0.1` | Server bind host. Use `0.0.0.0` in containers. |
| `API_PORT` | `8000` | Server port. |
| `LOG_LEVEL` | `INFO` | Standard logging level. |
| `LOG_FORMAT` | `text` | `text` for local dev, `json` for structured logs. |

The canonical, commented list is in [`../.env.example`](../.env.example). Optional LangSmith tracing (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`) is env-only and not part of `Settings`.

## Usage

```bash
cp .env.example .env          # then set GOOGLE_API_KEY
# override anything inline:
WRITER_MODEL=gemini-1.5-flash SEARCH_MAX_RESULTS=1 LOG_FORMAT=json python main.py "…"
```

## Adding a new setting

1. Add a typed field (with a default) to `Settings` in `config.py`.
2. Read it where the value is used — thread it through `build_dependencies` / the interface, **not** by calling `get_settings()` inside a factory.
3. Document it in `.env.example` and in the table above.
4. Add a test in `tests/unit/test_config.py` (default applied, env override works).

## ⚠️ Trade-off: unprefixed variables

Because there is no namespace, generic names like `LOG_LEVEL`, `API_HOST`, and `API_PORT` can **collide** with variables already present in a deployment or CI environment, silently overriding the intended config. If that becomes a problem, reintroduce a prefix in one place — set `env_prefix="APP_"` in `SettingsConfigDict` (`config.py`) — and update `.env.example` + the config tests accordingly.

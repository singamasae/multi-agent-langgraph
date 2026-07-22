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
| `GOOGLE_API_KEY` | *(required if any role uses `google`)* | Gemini API key. Stored as `SecretStr` (never logged). **Fail-fast**: if a role targets `google` and this is missing or the `.env.example` placeholder, startup raises. |
| `OPENAI_API_KEY` | *(required if any role uses `openai`)* | OpenAI API key. Stored as `SecretStr`. Fail-fast when a role targets `openai`. |
| `OPENAI_BASE_URL` | *(unset)* | Optional override for OpenAI-compatible endpoints (Azure, proxies, local servers). |
| `SUPERVISOR_PROVIDER` | `google` | Router provider: `google` or `openai`. |
| `RESEARCHER_PROVIDER` | `google` | ReAct researcher provider: `google` or `openai`. |
| `WRITER_PROVIDER` | `google` | Writer provider: `google` or `openai`. |
| `SUPERVISOR_MODEL` | `gemini-flash-lite-latest` | Router model. Set to an OpenAI model (e.g. `gpt-4o-mini`) when its provider is `openai`. |
| `RESEARCHER_MODEL` | `gemini-flash-lite-latest` | ReAct researcher model. |
| `WRITER_MODEL` | `gemini-flash-lite-latest` | Writer model. |
| `SUPERVISOR_TEMPERATURE` | `0.0` | |
| `RESEARCHER_TEMPERATURE` | `0.0` | |
| `WRITER_TEMPERATURE` | `0.7` | |
| `THINKING_BUDGET` | `0` | **Gemini only.** "Thinking" tokens. `0` disables thinking so the model returns answer text; thinking-enabled models (e.g. `*-flash-lite`) can otherwise return reasoning-only content with no answer. `-1` = model's dynamic default. Ignored for OpenAI roles. |
| `SEARCH_MAX_RESULTS` | `3` | DuckDuckGo result count. |
| `RECURSION_LIMIT` | `50` | Safety bound on the supervisor/worker loop. |
| `API_HOST` | `127.0.0.1` | Server bind host. Use `0.0.0.0` in containers. |
| `API_PORT` | `8000` | Server port. |
| `LOG_LEVEL` | `INFO` | Standard logging level. |
| `LOG_FORMAT` | `text` | `text` for local dev, `json` for structured logs. |

The canonical, commented list is in [`../.env.example`](../.env.example). Optional LangSmith tracing (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`) is env-only and not part of `Settings`.

## Usage

```bash
cp .env.example .env          # then set the key(s) for the provider(s) in use
# override anything inline:
WRITER_TEMPERATURE=0.3 SEARCH_MAX_RESULTS=1 LOG_FORMAT=json python main.py "…"
# run the writer on OpenAI, keep routing/research on Gemini:
OPENAI_API_KEY=sk-... WRITER_PROVIDER=openai WRITER_MODEL=gpt-4o-mini python main.py "…"
```

## Adding a new setting

1. Add a typed field (with a default) to `Settings` in `config.py`.
2. Read it where the value is used — thread it through `build_dependencies` / the interface, **not** by calling `get_settings()` inside a factory.
3. Document it in `.env.example` and in the table above.
4. Add a test in `tests/unit/test_config.py` (default applied, env override works).

## ⚠️ Trade-off: unprefixed variables

Because there is no namespace, generic names like `LOG_LEVEL`, `API_HOST`, and `API_PORT` can **collide** with variables already present in a deployment or CI environment, silently overriding the intended config. If that becomes a problem, reintroduce a prefix in one place — set `env_prefix="APP_"` in `SettingsConfigDict` (`config.py`) — and update `.env.example` + the config tests accordingly.

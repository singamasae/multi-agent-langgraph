# Deployment

The API service (`serve.py` → LangServe) ships as a container. Deployment artifacts:

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds the production image (`python:3.10-slim`, non-root, healthcheck). |
| `docker-compose.yml` | Runs the image, maps the port, loads env from `.env`. |
| `.dockerignore` | Keeps `venv/`, `.git/`, caches, tests/docs, and **`.env`** out of the image. |

## Quick start

```bash
cp .env.example .env         # set GOOGLE_API_KEY (required)

docker compose up --build    # build + run in the foreground
docker compose up -d         # detached
docker compose logs -f api   # tail logs
docker compose down          # stop
```

Then:

- API docs (Swagger): http://localhost:8000/docs
- LangServe playground: http://localhost:8000/research/playground/
- Invoke: `POST http://localhost:8000/research/invoke` with
  `{"input": {"messages": [{"type": "human", "content": "…"}], "next": ""}}`

The host port follows `API_PORT` (default `8000`): `API_PORT=9000 docker compose up`.

## How config reaches the container

- **Secrets and overrides come from the runtime environment**, never baked into the image. `docker-compose.yml` loads them via `env_file: .env`; `.dockerignore` excludes `.env` from the build context so it can't be copied into an image layer.
- The container sets `API_HOST=0.0.0.0` (the app default `127.0.0.1` would be unreachable from outside the container). All other settings use the same env vars as elsewhere — see [configuration.md](configuration.md).
- **Fail-fast:** with no `GOOGLE_API_KEY`, the container prints a configuration error and exits non-zero (it does not start half-configured).

## Image details

- Multi-stage-friendly single `runtime` stage on `python:3.10-slim`; dependencies install in their own layer (`requirements.txt` copied first) for fast rebuilds.
- Runs as unprivileged user `appuser` (uid 1000).
- `HEALTHCHECK` polls `/docs`; `docker ps` shows `healthy` once the server is up.
- Only `src/`, `serve.py`, and `main.py` are copied into the image.

## Building the image directly (without compose)

```bash
docker build -t aaas-mvp-api .
docker run --rm -p 8000:8000 -e GOOGLE_API_KEY=... aaas-mvp-api
```

## Notes for real deployments

- Put the container behind a TLS-terminating reverse proxy / load balancer; the app serves plain HTTP.
- Inject `GOOGLE_API_KEY` via your platform's secret manager rather than a committed `.env`.
- The CLI (`main.py`) is not part of the served image's entrypoint; run it ad hoc with
  `docker run --rm -e GOOGLE_API_KEY=... aaas-mvp-api python main.py "…"`.

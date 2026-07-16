# Production image for the AaaS research API (serve.py / LangServe).
FROM python:3.10-slim AS runtime

# Predictable, quiet Python + pip behaviour.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install runtime dependencies first so this layer is cached across code changes.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy only what the service needs to run (tests, docs, .env are excluded via
# .dockerignore and are not copied here).
COPY src/ ./src/
COPY serve.py main.py ./

# Bind to all interfaces inside the container (the app default is 127.0.0.1,
# which would not be reachable from outside the container).
ENV API_HOST=0.0.0.0 \
    API_PORT=8000

# Run as an unprivileged user.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Liveness: the LangServe docs endpoint returns 200 once the server is up.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/docs', timeout=4).status == 200 else 1)"

# serve.py reads GOOGLE_API_KEY (and any overrides) from the environment and
# fails fast if the key is missing.
CMD ["python", "serve.py"]

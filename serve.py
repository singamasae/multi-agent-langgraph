"""API server entry-point shim.

The application factory lives in ``app.interfaces.api``; this file wires it to
uvicorn using the configured host/port so ``python serve.py`` works from the
repository root without installing the package.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from pydantic import ValidationError  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.interfaces.api import create_app  # noqa: E402

if __name__ == "__main__":
    import uvicorn

    try:
        settings = get_settings()
    except ValidationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    app = create_app(settings)
    print(f"Starting LangServe API at http://{settings.api_host}:{settings.api_port}")
    print(
        "Interactive playground at "
        f"http://{settings.api_host}:{settings.api_port}/research/playground"
    )
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)

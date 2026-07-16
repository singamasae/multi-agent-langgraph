"""CLI entry-point shim.

The implementation lives in ``app.interfaces.cli``; this file just makes
``python main.py "..."`` work from the repository root without installing the
package.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from app.interfaces.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

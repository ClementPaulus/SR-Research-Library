"""Command-line site generator.

Usage:
    python -m validators.build_site

Regenerates the public library surface (site/index.html and site/data/*.json)
entirely from the registry. The registry remains the source of truth; the
site is never a second independent database.
"""

from __future__ import annotations

import sys

from . import sitegen


def main() -> int:
    index_path = sitegen.generate_site()
    print(f"Site generated: {index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

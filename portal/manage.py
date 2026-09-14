#!/usr/bin/env python
"""Django management entry point for the Structura Reditus researcher portal."""
import os
import sys
from pathlib import Path


def main() -> None:
    # Make both the portal package and the research repository root importable
    # so the portal can import the existing ``validators`` engine unchanged.
    repo_root = Path(__file__).resolve().parent.parent
    for path in (str(repo_root), str(repo_root / "portal")):
        if path not in sys.path:
            sys.path.insert(0, path)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

"""Command-line validation runner.

Usage:
    python -m validators.validate

Runs every automated validation check against the registry and exits non-zero
if any issue is found.
"""

from __future__ import annotations

import sys

from . import checks


def main() -> int:
    report = checks.validate_registry()
    if report.ok:
        print("Registry validation: OK (no issues found)")
        return 0
    print(f"Registry validation: {len(report.issues)} issue(s) found")
    for issue in report.issues:
        print(f"  {issue}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

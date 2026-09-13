"""Command-line release-manifest generator.

Usage:
    python -m validators.release SR-LIBRARY.v0.1.0 [--seam "open seam text"]... [--note "migration note"]...

Builds a release manifest from the current registry state and writes it to
releases/manifests/. Open seams default to those marked open in
releases/open-seams.yaml when no --seam is given. Previous releases are never
silently rewritten.
"""

from __future__ import annotations

import json
import sys

from . import manifest


def main(argv: list = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    version = argv[0]
    seams, notes = [], []
    i = 1
    while i < len(argv):
        if argv[i] == "--seam" and i + 1 < len(argv):
            seams.append(argv[i + 1])
            i += 2
        elif argv[i] == "--note" and i + 1 < len(argv):
            notes.append(argv[i + 1])
            i += 2
        else:
            print(f"Unknown argument: {argv[i]}")
            return 2
    data = manifest.build_release_manifest(version, open_seams=seams or None, migration_notes=notes)
    path = manifest.write_release_manifest(data)
    print(f"Release manifest written: {path}")
    print(json.dumps({k: v for k, v in data.items() if k != "hashes"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

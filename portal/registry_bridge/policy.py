"""Path policy for runtime-generated Git changes.

A submission may only touch reviewed registry, receipt, reservation, and
generated-site paths with text content types. Schemas, taxonomies, engine
code, workflows, permissions, portal code, and documentation change only
through separate maintainer-reviewed development pull requests. The same
policy is enforced in CI (.github/workflows/validate.yml).
"""

from __future__ import annotations

import posixpath

ALLOWED_PREFIXES = (
    "registry/authors/",
    "registry/objects/",
    "registry/sources/",
    "registry/relations/",
    "registry/reservations/",
    "receipts/accepted/",
    "receipts/repair/",
    "receipts/rejected/",
    "receipts/executions/",
    "site/",
)
ALLOWED_SUFFIXES = (".json", ".md", ".html")
FORBIDDEN_PREFIXES = (".github/", "schema/", "taxonomy/", "validators/", "portal/", "tests/", "docs/", "releases/",
                      "registry/governing/", "registry/objects/history/../")


class PolicyViolation(RuntimeError):
    pass


def is_publishable(path: str) -> bool:
    normalized = posixpath.normpath(path)
    if normalized.startswith("/") or normalized.startswith("..") or "\x00" in normalized:
        return False
    if normalized != path.rstrip("/"):
        return False
    if any(normalized.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        return False
    if not any(normalized.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return False
    return normalized.endswith(ALLOWED_SUFFIXES)


def filter_publishable(files: dict) -> dict:
    """Raise if any changed path is outside policy; otherwise return the files unchanged."""
    bad = sorted(p for p in files if not is_publishable(p))
    if bad:
        raise PolicyViolation("submission attempted to change paths outside the publication policy: " + ", ".join(bad[:10]))
    return files

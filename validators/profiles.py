"""Author-profile generation for the Structura Reditus Research Library.

Profiles are generated entirely from registry objects and contain only
reconstructible quantities: total registered authored objects and normalized
distributions over primary domain, Tier-2 class, structural focus, evidence
mode, provenance, and maturity.

There is no universal author score. Prestige, credentials, degree level,
institutional affiliation, citations, originality, quality, importance, and
author rank are never numerically weighted. Credentials appear only as
provenance metadata with their verification state. The library is an even
Tier-2 organizational surface, not a prestige hierarchy.
"""

from __future__ import annotations

from collections import Counter

from . import loader


def _normalize(counter: Counter, total: int) -> dict:
    if total == 0:
        return {}
    return {key: round(count / total, 6) for key, count in sorted(counter.items())}


def build_author_profile(author_id: str, registry: dict = None) -> dict:
    """Build the reconstructible profile for a registered author."""
    if registry is None:
        registry = loader.load_registry()

    author = None
    for record in registry["authors"].values():
        if record.get("author_id") == author_id:
            author = record
            break
    if author is None:
        raise KeyError(f"AuthorID '{author_id}' is not registered")

    authored = [
        obj for obj in registry["objects"].values()
        if author_id in (obj.get("authors") or [])
    ]
    total = len(authored)

    domains = Counter((o.get("domain") or {}).get("primary") for o in authored)
    tier2 = Counter((o.get("tier2_class") or {}).get("primary") for o in authored)
    focuses = Counter((o.get("structural_focus") or {}).get("primary") for o in authored)
    evidence = Counter((o.get("evidence_mode") or {}).get("primary") for o in authored)
    provenance = Counter(o.get("provenance") for o in authored)
    maturity = Counter(o.get("maturity") for o in authored)

    return {
        "author_id": author["author_id"],
        "display_name": author["display_name"],
        "orcid": author.get("orcid"),
        "status": author["status"],
        "credentials": author.get("credentials", []),
        "total_registered_authored_objects": total,
        "primary_domain_distribution": _normalize(domains, total),
        "tier2_class_distribution": _normalize(tier2, total),
        "structural_focus_distribution": _normalize(focuses, total),
        "evidence_mode_distribution": _normalize(evidence, total),
        "provenance_distribution": _normalize(provenance, total),
        "maturity_distribution": _normalize(maturity, total),
        "note": (
            "This profile contains only quantities reconstructible from the registry. "
            "It contains no universal author score and no weighting of prestige, "
            "credentials, degree level, institutional affiliation, citations, "
            "originality, quality, importance, or rank."
        ),
    }


def build_all_profiles(registry: dict = None) -> dict:
    if registry is None:
        registry = loader.load_registry()
    return {
        record["author_id"]: build_author_profile(record["author_id"], registry)
        for record in registry["authors"].values()
        if record.get("author_id")
    }

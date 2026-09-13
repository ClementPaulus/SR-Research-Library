"""Deterministic, review-only structural bridge detection.

The functions in this module produce a rebuildable projection. They never
write registry records and similarity is not treated as a research claim.
"""

from __future__ import annotations

import re
import unicodedata
from itertools import combinations


LOW = "LOW"
MEDIUM = "MEDIUM"
HIGH = "HIGH"
QUESTION_OVERLAP_THRESHOLD = 0.35
OBJECT_STUDY_OVERLAP_THRESHOLD = 0.50
BURDEN_OVERLAP_THRESHOLD = 0.10
MIN_SHARED_TOKENS = 2

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "does", "for",
    "from", "how", "in", "is", "it", "of", "on", "or", "that", "the", "their",
    "this", "to", "under", "what", "when", "which", "with", "why",
}
NOT_ESTABLISHED = [
    "shared mechanism",
    "scientific equivalence",
    "causation",
    "declared relation",
]


def normalize_tokens(value: object) -> set[str]:
    """Return a small, standard-library-only token set for free text."""
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = "".join(" " if unicodedata.category(char).startswith(("P", "S")) else char
                   for char in text)
    tokens = {token for token in re.split(r"\s+", text) if token and token not in STOP_WORDS}
    normalized = set()
    for token in tokens:
        if token.endswith("ied") and len(token) > 5:
            token = token[:-3] + "y"
        elif token.endswith("ed") and len(token) > 5:
            token = token[:-2]
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        normalized.add(token)
    return normalized


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _field_tokens(record: dict, field: str) -> set[str]:
    value = record.get(field)
    if isinstance(value, dict):
        values = [value.get("primary", "")] + list(value.get("secondary", []))
        return set().union(*(normalize_tokens(item) for item in values))
    if isinstance(value, list):
        return set().union(*(normalize_tokens(item) for item in value))
    return normalize_tokens(value)


def _text(record: dict, fields: tuple[str, ...]) -> set[str]:
    return set().union(*(_field_tokens(record, field) for field in fields))


def _signal(signal_type: str, evidence: str, strength: str = "moderate") -> dict:
    return {"type": signal_type, "strength": strength, "evidence": evidence}


def _structural_signals(left: dict, right: dict) -> list[dict]:
    left_focus = _field_tokens(left, "structural_focus")
    right_focus = _field_tokens(right, "structural_focus")
    left_primary = (left.get("structural_focus") or {}).get("primary")
    right_primary = (right.get("structural_focus") or {}).get("primary")
    signals = []
    if left_primary and left_primary == right_primary:
        signals.append(_signal("shared_structural_focus", f"Both objects declare primary structural focus '{left_primary}'.", "strong"))
    elif left_focus & right_focus:
        shared = sorted(left_focus & right_focus)
        signals.append(_signal("structural_focus_overlap", f"Structural focus terms overlap: {', '.join(shared)}."))
    return signals


def _question_signals(left: dict, right: dict) -> list[dict]:
    left_questions = [_field_tokens(left, "main_question")] + [_field_tokens({"value": q}, "value") for q in left.get("secondary_questions", [])]
    right_questions = [_field_tokens(right, "main_question")] + [_field_tokens({"value": q}, "value") for q in right.get("secondary_questions", [])]
    best = max((_jaccard(a, b), a & b) for a in left_questions for b in right_questions)
    overlap, shared = best
    if overlap >= QUESTION_OVERLAP_THRESHOLD and len(shared) >= MIN_SHARED_TOKENS:
        return [_signal("shared_question", f"Question vocabulary overlaps on: {', '.join(sorted(shared))}.")]
    return []


def _handoff_signal(source: dict, target: dict) -> list[dict]:
    burden = _field_tokens(source, "next_burden")
    target_parts = _text(target, ("main_question", "object_of_study", "structural_focus"))
    shared = burden & target_parts
    overlap = len(shared) / min(len(burden), len(target_parts)) if burden and target_parts else 0.0
    if overlap >= BURDEN_OVERLAP_THRESHOLD and len(shared) >= MIN_SHARED_TOKENS:
        return [_signal("burden_handoff", f"{source['object_id']} next burden overlaps {target['object_id']} on: {', '.join(sorted(shared))}.", "strong")]
    return []


def _object_study_signal(left: dict, right: dict) -> list[dict]:
    left_study, right_study = _field_tokens(left, "object_of_study"), _field_tokens(right, "object_of_study")
    shared = left_study & right_study
    if _jaccard(left_study, right_study) >= OBJECT_STUDY_OVERLAP_THRESHOLD and len(shared) >= MIN_SHARED_TOKENS:
        return [_signal("object_of_study_similarity", f"Object-of-study terms overlap on: {', '.join(sorted(shared))}.")]
    return []


def _classification_signal(left: dict, right: dict) -> list[dict]:
    fields = ("domain", "tier2_class", "evidence_mode", "provenance", "maturity", "functional_locus")
    shared = [field for field in fields if _field_tokens(left, field) & _field_tokens(right, field)]
    if shared:
        return [_signal("classification_overlap", f"Registered classification fields overlap: {', '.join(shared)}.", "weak")]
    return []


def _declared_pairs(relations: list[dict]) -> set[frozenset[str]]:
    return {frozenset((r.get("from_id"), r.get("to_id"))) for r in relations
            if r.get("from_id") and r.get("to_id")}


def _lineage_signal(left: dict, right: dict) -> list[dict]:
    """Recognize only explicit references to the other registered object."""
    signals = []
    lineage_words = re.compile(r"\b(sequel|predecessor|next part|previous part|extension|handoff|historical predecessor)\b", re.I)
    for source, target in ((left, right), (right, left)):
        fields = " ".join(str(source.get(field, "")) for field in ("title", "main_question", "next_burden", "notes"))
        if target.get("object_id") in fields and lineage_words.search(fields):
            signals.append(_signal("explicit_lineage", f"{source['object_id']} explicitly names {target['object_id']} with lineage language.", "strong"))
    return signals


def _strength(signals: list[dict]) -> str:
    strong = sum(signal["strength"] == "strong" for signal in signals)
    moderate = sum(signal["strength"] == "moderate" for signal in signals)
    types = {signal["type"] for signal in signals}
    specific_support = types & {"shared_question", "object_of_study_similarity", "shared_structural_focus", "explicit_lineage"}
    if "explicit_lineage" in types or ("burden_handoff" in types and specific_support) or strong + moderate >= 3:
        return HIGH
    if strong or strong + moderate >= 2:
        return MEDIUM
    return LOW


def _candidate(left: dict, right: dict, signals: list[dict], declared: set[frozenset[str]]) -> dict:
    handoff = next((signal for signal in signals if signal["type"] == "burden_handoff"), None)
    direction = f"{left['object_id']} -> {right['object_id']}" if handoff else f"{left['object_id']} <-> {right['object_id']}"
    relation_types = sorted({"handoff_to" if signal["type"] == "burden_handoff" else
                             "shares_focus_with" if signal["type"] in {"shared_structural_focus", "structural_focus_overlap"} else
                             "shares_question_with" if signal["type"] == "shared_question" else "structurally_adjacent"
                             for signal in signals if signal["type"] != "classification_overlap"})
    return {
        "object_a": left["object_id"],
        "object_b": right["object_id"],
        "direction": direction,
        "strength": _strength(signals),
        "candidate_relation_types": relation_types,
        "signals": [{key: value for key, value in signal.items() if key != "strength"} for signal in signals],
        "not_established": list(NOT_ESTABLISHED),
        "already_declared": frozenset((left["object_id"], right["object_id"])) in declared,
    }


def generate_bridge_candidates(objects: list[dict] | dict, relations: list[dict] | dict | None = None) -> list[dict]:
    """Generate stable pair candidates from current registered object records."""
    records = list(objects.values()) if isinstance(objects, dict) else list(objects or [])
    records.sort(key=lambda record: record.get("object_id", ""))
    relation_records = list(relations.values()) if isinstance(relations, dict) else list(relations or [])
    declared = _declared_pairs(relation_records)
    candidates = []
    for left, right in combinations(records, 2):
        signals = _structural_signals(left, right) + _question_signals(left, right) + _object_study_signal(left, right)
        signals += _classification_signal(left, right) + _lineage_signal(left, right)
        forward = _handoff_signal(left, right)
        reverse = _handoff_signal(right, left)
        if forward:
            candidates.append(_candidate(left, right, signals + forward, declared))
        elif reverse:
            candidates.append(_candidate(right, left, signals + reverse, declared))
        elif signals and any(signal["type"] != "classification_overlap" for signal in signals):
            candidates.append(_candidate(left, right, signals, declared))
    return sorted(candidates, key=lambda candidate: (candidate["object_a"], candidate["object_b"]))


def build_bridge_projection(registry: dict) -> dict:
    """Return the complete generated JSON projection for a registry."""
    return {"generated": True, "source": "registry",
            "candidates": generate_bridge_candidates(registry.get("objects", {}), registry.get("relations", {}))}
"""Admission-gate evaluation for the Structura Reditus Research Library.

Exactly seven gates are evaluated:

  Gate A: Identity
  Gate B: Tier placement
  Gate C: Source and provenance
  Gate D: Classification
  Gate E: Boundary and missingness
  Gate F: Relation integrity
  Gate G: Library durability

Outcomes are exactly ACCEPTED, RETURNED_FOR_REPAIR, or REJECTED.

Decision logic:

  ACCEPTED             — all active gates pass and no evaluability-blocking
                         missingness remains.
  RETURNED_FOR_REPAIR  — required structure is missing or incomplete, the gap
                         blocks admission, and the same object can reasonably
                         return through declared repair (gate state BLOCKED).
  REJECTED             — an evaluable admission gate fails because the
                         submitted object violates the active library contract
                         (gate state FAIL).

RETURNED_FOR_REPAIR is never collapsed into REJECTED.

The gates evaluate organizational structure only. They never evaluate whether
a claim is true, whether it agrees with GCD, whether the result is negative or
reports non-return, whether the work is controversial or unconventional,
whether it challenges another Tier-2 work, or whether the author is external.
Disagreement is not an admission failure. Every author — including AUTH-0001 —
is evaluated by the same gates; there are no founder exceptions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import jsonschema

from . import loader
from .checks import TIMESTAMP_RE, VERSION_RE

PASS, FAIL, BLOCKED = "PASS", "FAIL", "BLOCKED"

GATE_NAMES = {
    "A": "Identity",
    "B": "Tier placement",
    "C": "Source and provenance",
    "D": "Classification",
    "E": "Boundary and missingness",
    "F": "Relation integrity",
    "G": "Library durability",
}

OBJECT_ID_RE = re.compile(r"^SR-OBJ-[0-9]{6}$")
AUTHOR_ID_RE = re.compile(r"^AUTH-[0-9]{4}$")


@dataclass
class GateResult:
    gate: str
    name: str
    result: str = PASS
    details: list = field(default_factory=list)

    def block(self, message: str) -> None:
        """Missing/incomplete structure: repairable, blocks admission."""
        if self.result != FAIL:
            self.result = BLOCKED
        self.details.append(message)

    def fail(self, message: str) -> None:
        """Evaluable contract violation: fails the gate."""
        self.result = FAIL
        self.details.append(message)


@dataclass
class GateEvaluation:
    decision: str
    gates: dict
    missingness_notes: list = field(default_factory=list)

    @property
    def failed_gates(self) -> list:
        return [g for g in self.gates.values() if g.result == FAIL]

    @property
    def blocked_gates(self) -> list:
        return [g for g in self.gates.values() if g.result == BLOCKED]


def _missing(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _gate_a_identity(record: dict, registry: dict, gate: GateResult) -> None:
    object_id = record.get("object_id")
    if _missing(object_id):
        gate.block("object_id is missing")
    elif not OBJECT_ID_RE.match(object_id):
        gate.fail(f"object_id '{object_id}' violates the SR-OBJ identifier namespace")
    if _missing(record.get("title")):
        gate.block("title is missing")
    authors = record.get("authors")
    if not authors:
        gate.block("authors list is missing or empty")
    else:
        registered = {a.get("author_id") for a in registry["authors"].values()}
        for author_id in authors:
            if not isinstance(author_id, str) or not AUTHOR_ID_RE.match(author_id):
                gate.fail(f"author reference '{author_id}' violates the AUTH identifier namespace")
            elif author_id not in registered:
                gate.block(f"AuthorID '{author_id}' is not registered; register the author first")


def _gate_b_tier_placement(record: dict, gate: GateResult) -> None:
    authority = record.get("authority") or {}
    tier = authority.get("tier")
    if _missing(tier):
        gate.block("authority.tier is missing")
    elif tier != "tier-2":
        gate.fail(
            f"authority.tier '{tier}' violates the library contract: the Research Library "
            "registers Tier-2 research records only and does not create new authority tiers"
        )


def _gate_c_source_and_provenance(record: dict, registry: dict, taxonomies: dict, gate: GateResult) -> None:
    provenance = record.get("provenance")
    if _missing(provenance):
        gate.block("provenance is missing")
    elif provenance not in set(taxonomies["provenance_types"]):
        gate.fail(f"provenance '{provenance}' is not a controlled provenance type")
    source_ids = record.get("source_ids")
    if source_ids is None:
        gate.block("source_ids is missing (declare an empty list if the object has no sources)")
    else:
        registered = {s.get("source_id") for s in registry["sources"].values()}
        for source_id in source_ids:
            if source_id not in registered:
                gate.block(f"SourceID '{source_id}' is not registered; register the source first")
    if _missing(record.get("source_boundary")):
        gate.block("source_boundary is missing: the object must state what its sources "
                   "do and do not establish")
    # External-source discipline: claim layers must keep source observation
    # distinct from local interpretation. Structure is checked; content is not judged.
    for entry in record.get("claim_layers", []) or []:
        if isinstance(entry, dict) and _missing(entry.get("layer")):
            gate.block("claim_layers entry is missing its layer declaration "
                       "(source-observation vs local-interpretation must remain distinct)")


def _gate_d_classification(record: dict, taxonomies: dict, gate: GateResult) -> None:
    bindings = [
        ("tier2_class.primary", (record.get("tier2_class") or {}).get("primary"), "tier2_classes"),
        ("domain.primary", (record.get("domain") or {}).get("primary"), "domains"),
        ("structural_focus.primary", (record.get("structural_focus") or {}).get("primary"), "focuses"),
        ("evidence_mode.primary", (record.get("evidence_mode") or {}).get("primary"), "evidence_modes"),
        ("maturity", record.get("maturity"), "maturity_states"),
        ("functional_locus", record.get("functional_locus"), "functional_loci"),
        ("publication_state", record.get("publication_state"), "publication_states"),
    ]
    for field_name, value, taxonomy_name in bindings:
        if _missing(value):
            gate.block(f"{field_name} is missing")
        elif value not in set(taxonomies[taxonomy_name]):
            gate.fail(f"{field_name} value '{value}' is not a controlled term in "
                      f"taxonomy '{taxonomy_name}'")
    for axis, taxonomy_name in (("tier2_class", "tier2_classes"),
                                ("domain", "domains"),
                                ("structural_focus", "focuses"),
                                ("evidence_mode", "evidence_modes")):
        for value in ((record.get(axis) or {}).get("secondary") or []):
            if value not in set(taxonomies[taxonomy_name]):
                gate.fail(f"{axis}.secondary value '{value}' is not a controlled term in "
                          f"taxonomy '{taxonomy_name}'")
    if _missing(record.get("main_question")):
        gate.block("main_question is missing")


def _gate_e_boundary_and_missingness(record: dict, gate: GateResult, notes: list) -> None:
    if _missing(record.get("authority_boundary")):
        gate.block("authority_boundary is missing: the object must state what it does "
                   "not claim authority over")
    if _missing(record.get("scope")):
        gate.block("scope is missing")
    missingness = record.get("missingness")
    if missingness is None:
        gate.block("missingness is missing (declare an empty list if nothing is missing)")
        return
    for entry in missingness:
        if not isinstance(entry, dict):
            gate.block("missingness entry is not a structured declaration")
            continue
        cls = entry.get("class")
        item = entry.get("item", "<undeclared item>")
        if cls not in loader.MISSINGNESS_CLASSES:
            gate.block(f"missingness entry '{item}' uses unknown class '{cls}'")
        elif cls == "CONTRACT_VIOLATING":
            gate.fail(f"declared missingness '{item}' is CONTRACT_VIOLATING under the "
                      "active library contract")
        elif cls in ("EVALUABILITY_BLOCKING", "REPAIRABLE"):
            gate.block(f"missingness '{item}' ({cls}) blocks evaluability and must be "
                       "repaired or reclassified before admission")
        else:
            notes.append(f"{item} ({cls})")


def _gate_f_relation_integrity(record: dict, registry: dict, taxonomies: dict, gate: GateResult) -> None:
    relations = record.get("relations")
    if relations is None:
        gate.block("relations is missing (declare an empty list if the object has no relations)")
        return
    # Governing references constrain the record; they never transfer authority (Gate B keeps tier-2).
    governing_ids = {g.get("governing_id") for g in (registry.get("governing") or {}).values()}
    for governing_id in record.get("governing_refs") or []:
        if governing_id not in governing_ids:
            gate.block(f"governing reference '{governing_id}' does not resolve to a registered SR-GOV record")
    registered = {r.get("relation_id"): r for r in registry["relations"].values()}
    object_ids = {o.get("object_id") for o in registry["objects"].values()}
    object_ids.add(record.get("object_id"))
    source_ids = {s.get("source_id") for s in registry["sources"].values()}
    for relation_id in relations:
        relation = registered.get(relation_id)
        if relation is None:
            gate.block(f"RelationID '{relation_id}' is not registered; register the relation first")
            continue
        relation_type = relation.get("relation_type")
        if relation_type not in set(taxonomies["relation_types"]):
            gate.fail(f"relation '{relation_id}' uses relation_type '{relation_type}', "
                      "which is not a controlled relation type")
        for endpoint_field in ("from_id", "to_id"):
            endpoint = relation.get(endpoint_field)
            if isinstance(endpoint, str) and endpoint.startswith("SR-OBJ-"):
                if endpoint not in object_ids:
                    gate.block(f"relation '{relation_id}' {endpoint_field} '{endpoint}' "
                               "does not resolve to a registered object")
            elif isinstance(endpoint, str) and endpoint.startswith("SRC-"):
                if endpoint not in source_ids:
                    gate.block(f"relation '{relation_id}' {endpoint_field} '{endpoint}' "
                               "does not resolve to a registered source")


def _gate_g_library_durability(record: dict, schemas: dict, gate: GateResult) -> None:
    version = record.get("version")
    if _missing(version):
        gate.block("version is missing")
    elif not VERSION_RE.match(version):
        gate.fail(f"version '{version}' violates the MAJOR.MINOR.PATCH version contract")
    date = record.get("date")
    if _missing(date):
        gate.block("date is missing")
    elif not TIMESTAMP_RE.match(date):
        gate.fail(f"date '{date}' violates the ISO 8601 timestamp contract "
                  "(YYYY-MM-DDThh:mm:ss with an explicit Z or +/-HH:MM time zone)")
    for field_name in ("next_burden", "repair_route", "preserved_meaning",
                       "object_of_study", "lens", "distortion_or_substitution_risk"):
        if _missing(record.get(field_name)):
            gate.block(f"{field_name} is missing")
    for field_name in ("secondary_questions", "claim_layers", "exclusions", "notes"):
        if field_name not in record:
            gate.block(f"{field_name} is missing (declare it explicitly, even if empty)")
    validator = jsonschema.Draft202012Validator(schemas["object"])
    for error in validator.iter_errors(record):
        path = "/".join(str(p) for p in error.absolute_path) or "<root>"
        message = f"schema durability: {path}: {error.message}"
        if error.validator == "required":
            gate.block(message)
        elif error.validator in ("pattern", "enum", "type", "additionalProperties"):
            gate.fail(message)
        else:
            gate.block(message)


def evaluate_object(record: dict, registry: dict = None, schemas: dict = None,
                    taxonomies: dict = None) -> GateEvaluation:
    """Evaluate a submitted research-object record against the seven gates."""
    if registry is None:
        registry = loader.load_registry()
    if schemas is None:
        schemas = loader.load_schemas()
    if taxonomies is None:
        taxonomies = loader.load_taxonomies()

    gates = {key: GateResult(key, GATE_NAMES[key]) for key in "ABCDEFG"}
    missingness_notes: list = []

    _gate_a_identity(record, registry, gates["A"])
    _gate_b_tier_placement(record, gates["B"])
    _gate_c_source_and_provenance(record, registry, taxonomies, gates["C"])
    _gate_d_classification(record, taxonomies, gates["D"])
    _gate_e_boundary_and_missingness(record, gates["E"], missingness_notes)
    _gate_f_relation_integrity(record, registry, taxonomies, gates["F"])
    _gate_g_library_durability(record, schemas, gates["G"])

    if any(g.result == FAIL for g in gates.values()):
        decision = "REJECTED"
    elif any(g.result == BLOCKED for g in gates.values()):
        decision = "RETURNED_FOR_REPAIR"
    else:
        decision = "ACCEPTED"

    return GateEvaluation(decision=decision, gates=gates, missingness_notes=missingness_notes)

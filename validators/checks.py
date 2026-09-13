"""Automated validation checks for the Structura Reditus Research Library.

Every check returns Issue records instead of raising, so a full validation
run reports all problems at once. Checks cover: schema validity, unique IDs,
AuthorID/SourceID/RelationID references, taxonomy references, required fields,
date formats, version formats, duplicate object collisions, broken relations,
and the mandatory presence checks (primary Tier-2 class, primary domain,
structural focus, main question, evidence mode, provenance, authority
boundary, next burden).

Validation is organizational only. No check evaluates whether a research
claim is true, whether it agrees with GCD, or whether its author holds any
credential.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import jsonschema

from . import loader

ID_PATTERNS = {
    "authors": re.compile(r"^AUTH-[0-9]{4}$"),
    "objects": re.compile(r"^SR-OBJ-[0-9]{6}$"),
    "sources": re.compile(r"^SRC-[0-9]{6}$"),
    "relations": re.compile(r"^REL-[0-9]{6}$"),
}

ID_FIELDS = {
    "authors": "author_id",
    "objects": "object_id",
    "sources": "source_id",
    "relations": "relation_id",
}

SCHEMA_FOR_KIND = {
    "authors": "author",
    "objects": "object",
    "sources": "source",
    "relations": "relation",
}

# Registry event timestamps carry an explicit time-zone designator; date-only values are ambiguous.
TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


@dataclass
class Issue:
    check: str
    record: str
    message: str
    blocking: bool = True

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"[{self.check}] {self.record}: {self.message}"


@dataclass
class ValidationReport:
    issues: list = field(default_factory=list)

    def add(self, check: str, record: str, message: str, blocking: bool = True) -> None:
        self.issues.append(Issue(check, record, message, blocking))

    @property
    def ok(self) -> bool:
        return not self.issues

    def for_check(self, check: str) -> list:
        return [i for i in self.issues if i.check == check]


def check_schema_validity(registry: dict, schemas: dict, report: ValidationReport) -> None:
    for kind, records in registry.items():
        schema = schemas[SCHEMA_FOR_KIND[kind]]
        validator = jsonschema.Draft202012Validator(schema)
        for filename, record in records.items():
            for error in validator.iter_errors(record):
                path = "/".join(str(p) for p in error.absolute_path) or "<root>"
                report.add("schema-validity", f"{kind}/{filename}", f"{path}: {error.message}")


def check_unique_ids(registry: dict, report: ValidationReport) -> None:
    seen: dict = {}
    for kind, records in registry.items():
        id_field = ID_FIELDS[kind]
        for filename, record in records.items():
            record_id = record.get(id_field)
            if not isinstance(record_id, str):
                continue
            if not ID_PATTERNS[kind].match(record_id):
                report.add("id-namespace", f"{kind}/{filename}",
                           f"{id_field} '{record_id}' does not match the {kind} identifier namespace")
            if record_id in seen:
                report.add("unique-ids", f"{kind}/{filename}",
                           f"duplicate identifier '{record_id}' also declared in {seen[record_id]}")
            else:
                seen[record_id] = f"{kind}/{filename}"


def _ids(registry: dict, kind: str) -> set:
    id_field = ID_FIELDS[kind]
    return {r.get(id_field) for r in registry[kind].values() if isinstance(r.get(id_field), str)}


def check_references(registry: dict, report: ValidationReport) -> None:
    author_ids = _ids(registry, "authors")
    source_ids = _ids(registry, "sources")
    relation_ids = _ids(registry, "relations")
    object_ids = _ids(registry, "objects")

    for filename, record in registry["objects"].items():
        rec = f"objects/{filename}"
        for author_id in record.get("authors", []) or []:
            if author_id not in author_ids:
                report.add("author-references", rec, f"AuthorID '{author_id}' is not registered")
        for source_id in record.get("source_ids", []) or []:
            if source_id not in source_ids:
                report.add("source-references", rec, f"SourceID '{source_id}' is not registered")
        for relation_id in record.get("relations", []) or []:
            if relation_id not in relation_ids:
                report.add("relation-references", rec, f"RelationID '{relation_id}' is not registered")
        supersedes = record.get("supersedes")
        if supersedes and supersedes not in object_ids:
            report.add("supersession-references", rec,
                       f"superseded ObjectID '{supersedes}' is not registered")

    for filename, record in registry["relations"].items():
        rec = f"relations/{filename}"
        for endpoint_field in ("from_id", "to_id"):
            endpoint = record.get(endpoint_field)
            if not isinstance(endpoint, str):
                continue
            if endpoint.startswith("SR-OBJ-") and endpoint not in object_ids:
                report.add("broken-relations", rec,
                           f"{endpoint_field} '{endpoint}' does not resolve to a registered object")
            elif endpoint.startswith("SRC-") and endpoint not in source_ids:
                report.add("broken-relations", rec,
                           f"{endpoint_field} '{endpoint}' does not resolve to a registered source")


TAXONOMY_BINDINGS = [
    # (record path extractor description, taxonomy name, getter)
    ("domain.primary", "domains", lambda r: [(r.get("domain") or {}).get("primary")]),
    ("domain.secondary", "domains", lambda r: (r.get("domain") or {}).get("secondary") or []),
    ("tier2_class.primary", "tier2_classes", lambda r: [(r.get("tier2_class") or {}).get("primary")]),
    ("tier2_class.secondary", "tier2_classes", lambda r: (r.get("tier2_class") or {}).get("secondary") or []),
    ("structural_focus.primary", "focuses", lambda r: [(r.get("structural_focus") or {}).get("primary")]),
    ("structural_focus.secondary", "focuses", lambda r: (r.get("structural_focus") or {}).get("secondary") or []),
    ("evidence_mode.primary", "evidence_modes", lambda r: [(r.get("evidence_mode") or {}).get("primary")]),
    ("evidence_mode.secondary", "evidence_modes", lambda r: (r.get("evidence_mode") or {}).get("secondary") or []),
    ("provenance", "provenance_types", lambda r: [r.get("provenance")]),
    ("maturity", "maturity_states", lambda r: [r.get("maturity")]),
    ("publication_state", "publication_states", lambda r: [r.get("publication_state")]),
    ("functional_locus", "functional_loci", lambda r: [r.get("functional_locus")]),
]


def check_taxonomy_references(registry: dict, taxonomies: dict, report: ValidationReport) -> None:
    """Controlled values must come from the controlled taxonomies.

    Free text never replaces controlled values for primary domain, Tier-2
    class, structural focus, evidence mode, provenance, maturity, relation
    type, publication state, and functional locus.
    """
    for filename, record in registry["objects"].items():
        rec = f"objects/{filename}"
        for field_name, taxonomy_name, getter in TAXONOMY_BINDINGS:
            allowed = set(taxonomies[taxonomy_name])
            for value in getter(record):
                if value is None:
                    continue
                if value not in allowed:
                    report.add("taxonomy-references", rec,
                               f"{field_name} value '{value}' is not a controlled term "
                               f"in taxonomy '{taxonomy_name}'")
    for filename, record in registry["relations"].items():
        rec = f"relations/{filename}"
        relation_type = record.get("relation_type")
        if relation_type is not None and relation_type not in set(taxonomies["relation_types"]):
            report.add("taxonomy-references", rec,
                       f"relation_type '{relation_type}' is not a controlled term "
                       "in taxonomy 'relation_types'")


REQUIRED_PRESENCE = [
    ("missing-primary-tier2-class", lambda r: (r.get("tier2_class") or {}).get("primary"),
     "primary Tier-2 class is missing"),
    ("missing-primary-domain", lambda r: (r.get("domain") or {}).get("primary"),
     "primary domain is missing"),
    ("missing-structural-focus", lambda r: (r.get("structural_focus") or {}).get("primary"),
     "primary structural focus is missing"),
    ("missing-main-question", lambda r: r.get("main_question"),
     "main question is missing"),
    ("missing-evidence-mode", lambda r: (r.get("evidence_mode") or {}).get("primary"),
     "primary evidence mode is missing"),
    ("missing-provenance", lambda r: r.get("provenance"),
     "provenance is missing"),
    ("missing-authority-boundary", lambda r: r.get("authority_boundary"),
     "authority boundary is missing"),
    ("missing-source-boundary", lambda r: r.get("source_boundary"),
     "source boundary is missing"),
    ("missing-next-burden", lambda r: r.get("next_burden"),
     "next burden is missing"),
]


def check_required_fields(registry: dict, report: ValidationReport) -> None:
    for filename, record in registry["objects"].items():
        rec = f"objects/{filename}"
        for check_name, getter, message in REQUIRED_PRESENCE:
            value = getter(record)
            if value is None or (isinstance(value, str) and not value.strip()):
                report.add(check_name, rec, message)


def check_date_formats(registry: dict, report: ValidationReport) -> None:
    date_fields = {
        "authors": ["registered"],
        "objects": ["date"],
        "relations": ["declared"],
    }
    for kind, fields in date_fields.items():
        for filename, record in registry[kind].items():
            for field_name in fields:
                value = record.get(field_name)
                if isinstance(value, str) and not TIMESTAMP_RE.match(value):
                    report.add("date-formats", f"{kind}/{filename}",
                               f"{field_name} '{value}' is not an ISO 8601 timestamp with an "
                               "explicit time zone (YYYY-MM-DDThh:mm:ssZ or +/-HH:MM)")


def check_version_formats(registry: dict, report: ValidationReport) -> None:
    for filename, record in registry["objects"].items():
        value = record.get("version")
        if isinstance(value, str) and not VERSION_RE.match(value):
            report.add("version-formats", f"objects/{filename}",
                       f"version '{value}' is not a semantic version (MAJOR.MINOR.PATCH)")


def check_duplicate_object_collisions(registry: dict, report: ValidationReport) -> None:
    """Detect distinct object records that collide on (title, version)."""
    seen: dict = {}
    for filename, record in registry["objects"].items():
        title = record.get("title")
        version = record.get("version")
        if not isinstance(title, str) or not isinstance(version, str):
            continue
        key = (title.strip().lower(), version)
        if key in seen and seen[key][1] != record.get("object_id"):
            report.add("duplicate-object-collisions", f"objects/{filename}",
                       f"title/version collision with {seen[key][0]} "
                       f"(both declare title '{title}' at version {version})")
        else:
            seen.setdefault(key, (f"objects/{filename}", record.get("object_id")))


def check_missingness_classes(registry: dict, report: ValidationReport) -> None:
    for filename, record in registry["objects"].items():
        rec = f"objects/{filename}"
        for entry in record.get("missingness", []) or []:
            cls = entry.get("class") if isinstance(entry, dict) else None
            if cls not in loader.MISSINGNESS_CLASSES:
                report.add("missingness-classes", rec,
                           f"missingness class '{cls}' is not a declared missingness class")


def validate_registry(registry: dict = None, schemas: dict = None, taxonomies: dict = None) -> ValidationReport:
    """Run every automated validation check and return the full report."""
    if registry is None:
        registry = loader.load_registry()
    if schemas is None:
        schemas = loader.load_schemas()
    if taxonomies is None:
        taxonomies = loader.load_taxonomies()

    report = ValidationReport()
    check_schema_validity(registry, schemas, report)
    check_unique_ids(registry, report)
    check_references(registry, report)
    check_taxonomy_references(registry, taxonomies, report)
    check_required_fields(registry, report)
    check_date_formats(registry, report)
    check_version_formats(registry, report)
    check_duplicate_object_collisions(registry, report)
    check_missingness_classes(registry, report)
    return report

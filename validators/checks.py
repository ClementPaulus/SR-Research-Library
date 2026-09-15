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

import hashlib
import json
import re
from dataclasses import dataclass, field

import jsonschema

from . import loader

ID_PATTERNS = {
    "authors": re.compile(r"^AUTH-[0-9]{4}$"),
    "objects": re.compile(r"^SR-OBJ-[0-9]{6}$"),
    "sources": re.compile(r"^SRC-[0-9]{6}$"),
    "relations": re.compile(r"^REL-[0-9]{6}$"),
    "governing": re.compile(r"^SR-GOV-[0-9]{6}$"),
}

ID_FIELDS = {
    "authors": "author_id",
    "objects": "object_id",
    "sources": "source_id",
    "relations": "relation_id",
    "governing": "governing_id",
}

SCHEMA_FOR_KIND = {
    "authors": "author",
    "objects": "object",
    "sources": "source",
    "relations": "relation",
    "governing": "governing",
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
    governing_ids = _ids(registry, "governing") if "governing" in registry else set()

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
        for governing_id in record.get("governing_refs", []) or []:
            if governing_id not in governing_ids:
                report.add("governing-references", rec,
                           f"governing reference '{governing_id}' does not resolve to a registered SR-GOV record")
        supersedes = record.get("supersedes")
        if supersedes and supersedes not in object_ids:
            report.add("supersession-references", rec,
                       f"superseded ObjectID '{supersedes}' is not registered")

    for filename, record in (registry.get("governing") or {}).items():
        rec = f"governing/{filename}"
        source_id = record.get("source_id")
        if isinstance(source_id, str) and source_id not in source_ids:
            report.add("source-references", rec, f"SourceID '{source_id}' is not registered")

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
        "governing": ["active_from"],
    }
    for kind, fields in date_fields.items():
        for filename, record in (registry.get(kind) or {}).items():
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
    for kind in ("objects", "governing"):
        for filename, record in (registry.get(kind) or {}).items():
            rec = f"{kind}/{filename}"
            for entry in record.get("missingness", []) or []:
                cls = entry.get("class") if isinstance(entry, dict) else None
                if cls not in loader.MISSINGNESS_CLASSES:
                    report.add("missingness-classes", rec,
                               f"missingness class '{cls}' is not a declared missingness class")


# Fields a released governing record may still change: everything else is its historical meaning.
GOVERNING_MUTABLE_FIELDS = ("status", "superseded_by")


def governing_immutable_hash(record: dict) -> str:
    """SHA-256 of a governing record's immutable content (all fields except status/superseded_by)."""
    frozen = {k: v for k, v in record.items() if k not in GOVERNING_MUTABLE_FIELDS}
    payload = json.dumps(frozen, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _governing_view(filename: str) -> str:
    parts = filename.replace("\\", "/").split("/")
    return parts[0] if len(parts) > 1 else ""


def check_governing(registry: dict, report: ValidationReport, released_hashes: dict = None) -> None:
    """View placement, authority-scope explicitness, supersession integrity, and released-record immutability."""
    governing = registry.get("governing") or {}
    if released_hashes is None:
        released_hashes = loader.released_governing_hashes()
    by_id = {r.get("governing_id"): r for r in governing.values() if isinstance(r.get("governing_id"), str)}

    for filename, record in governing.items():
        rec = f"governing/{filename}"
        scope = record.get("authority_scope") or {}
        tier_1, tier_0 = scope.get("tier_1"), scope.get("tier_0")
        if not isinstance(tier_1, list) or not isinstance(tier_0, list):
            report.add("governing-authority-scope", rec,
                       "authority_scope must declare tier_1 and tier_0 burden lists explicitly (either may be empty)")
            continue
        view = _governing_view(filename)
        expected = {"tier-1": (True, False), "tier-0": (False, True), "mixed": (True, True), "": (False, False)}
        if view not in expected:
            report.add("governing-view", rec, f"unknown governing view directory '{view}'")
        elif expected[view] != (bool(tier_1), bool(tier_0)):
            report.add("governing-view", rec,
                       f"view directory '{view or '(root)'}' does not match authority_scope "
                       f"(tier_1 {'declared' if tier_1 else 'empty'}, tier_0 {'declared' if tier_0 else 'empty'}); "
                       "views are tier-1/, tier-0/, mixed/, or the root for records with no Tier-1/Tier-0 burden")

        gid = record.get("governing_id")
        status = record.get("status")
        supersedes, superseded_by = record.get("supersedes"), record.get("superseded_by")
        if supersedes:
            old = by_id.get(supersedes)
            if old is None:
                report.add("governing-supersession", rec,
                           f"supersedes '{supersedes}' but that record is not preserved in the registry")
            else:
                if old.get("superseded_by") != gid:
                    report.add("governing-supersession", rec,
                               f"supersedes '{supersedes}' but that record's superseded_by is '{old.get('superseded_by')}'")
                if old.get("status") not in ("superseded", "historical"):
                    report.add("governing-supersession", rec,
                               f"supersedes '{supersedes}' but that record's status is '{old.get('status')}'")
        if superseded_by:
            new = by_id.get(superseded_by)
            if new is None or new.get("supersedes") != gid:
                report.add("governing-supersession", rec,
                           f"superseded_by '{superseded_by}' is not a registered record that supersedes this one")
            if status == "active":
                report.add("governing-supersession", rec, "an active record cannot be superseded_by another record")
        elif status == "superseded":
            report.add("governing-supersession", rec, "status is superseded but superseded_by is null")

        if gid in released_hashes and governing_immutable_hash(record) != released_hashes[gid]:
            report.add("governing-immutability", rec,
                       f"released governing record '{gid}' was edited in place; only status and superseded_by "
                       "may change after release. Issue a new SR-GOV record that supersedes it.")

    for gid in released_hashes:
        if gid not in by_id:
            report.add("governing-immutability", f"governing/{gid}",
                       f"released governing record '{gid}' has been removed; superseded records must be preserved")


DOI_RESOLVER = "https://doi.org/"


def check_source_links(registry: dict, report: ValidationReport) -> None:
    """Outbound links: at most one preferred per source; DOI resolver must match identifier.doi."""
    for filename, record in registry["sources"].items():
        rec = f"sources/{filename}"
        links = record.get("links") or []
        if not isinstance(links, list):
            continue
        preferred = [l for l in links if isinstance(l, dict) and l.get("preferred") is True]
        if len(preferred) > 1:
            report.add("source-links", rec,
                       f"{len(preferred)} links are marked preferred; at most one is allowed")
        urls = [l.get("url") for l in links if isinstance(l, dict)]
        for url in set(urls):
            if urls.count(url) > 1:
                report.add("source-links", rec, f"duplicate link url '{url}'")
        doi = (record.get("identifier") or {}).get("doi")
        for link in links:
            if not isinstance(link, dict):
                continue
            url = link.get("url") or ""
            if url.startswith(DOI_RESOLVER) and doi and url != DOI_RESOLVER + doi:
                report.add("source-links", rec,
                           f"DOI link '{url}' does not resolve identifier.doi '{doi}'")


def check_source_lineage(registry: dict, report: ValidationReport) -> None:
    """Typed source lineage: DOI consistency and append-preserving supersession between source records."""
    sources = registry["sources"]
    by_id = {r.get("source_id"): r for r in sources.values() if isinstance(r.get("source_id"), str)}
    for filename, record in sources.items():
        rec = f"sources/{filename}"
        doi = (record.get("identifier") or {}).get("doi")
        concept, version = record.get("concept_doi"), record.get("version_doi")
        if doi and (concept or version) and doi not in (concept, version):
            report.add("source-lineage", rec,
                       f"identifier.doi '{doi}' is neither concept_doi nor version_doi; the anchoring DOI must be one of them")
        if concept and version and concept == version:
            report.add("source-lineage", rec, "concept_doi and version_doi are identical; a concept DOI is not a deposited version")
        related = {r.get("doi") for r in record.get("related_dois") or [] if isinstance(r, dict)}
        for d in related & {doi, concept, version} - {None}:
            report.add("source-lineage", rec, f"related_dois repeats this record's own DOI '{d}'")
        sid, status = record.get("source_id"), record.get("status", "active")
        for old_id in record.get("supersedes") or []:
            old = by_id.get(old_id)
            if old is None:
                report.add("source-lineage", rec, f"supersedes '{old_id}' but that record is not preserved in the registry")
            else:
                if old.get("superseded_by") != sid:
                    report.add("source-lineage", rec, f"supersedes '{old_id}' but that record's superseded_by is '{old.get('superseded_by')}'")
                if old.get("status", "active") == "active":
                    report.add("source-lineage", rec, f"supersedes '{old_id}' but that record is still active")
        newer = record.get("superseded_by")
        if newer:
            new = by_id.get(newer)
            if new is None or sid not in (new.get("supersedes") or []):
                report.add("source-lineage", rec, f"superseded_by '{newer}' is not a registered record that supersedes this one")
            if status == "active":
                report.add("source-lineage", rec, "an active source cannot be superseded_by another record")
        elif status == "superseded":
            report.add("source-lineage", rec, "status is superseded but superseded_by is null")


def check_reserved_identities(registry: dict, report: ValidationReport, receipts: dict = None) -> None:
    """An ObjectID named on a non-accepted receipt stays reserved for that submission's work."""
    if receipts is None:
        receipts = loader.load_receipts()
    reserved: dict = {}
    for receipt in receipts.values():
        if receipt.get("decision") == "ACCEPTED":
            continue
        ident = receipt.get("provisional_object_id") or receipt.get("submission_identity")
        if isinstance(ident, str) and ident.startswith("SR-OBJ-"):
            reserved.setdefault(ident, receipt.get("receipt_id"))
    accepted = {r.get("object_id") for r in receipts.values() if r.get("decision") == "ACCEPTED"}
    for filename, record in registry["objects"].items():
        oid = record.get("object_id")
        if oid in reserved and oid not in accepted:
            report.add("reserved-identities", f"objects/{filename}",
                       f"'{oid}' is reserved by non-accepted receipt {reserved[oid]} and has no ACCEPTED receipt; "
                       "resubmit the same work through admission or allocate a fresh ObjectID")


def validate_registry(registry: dict = None, schemas: dict = None, taxonomies: dict = None,
                      released_hashes: dict = None, receipts: dict = None,
                      reservations: dict = None) -> ValidationReport:
    """Run every automated validation check and return the full report.

    Released-governing-record immutability is enforced against the release
    manifests when the live registry is validated (registry is None). Callers
    supplying their own registry pass ``released_hashes`` explicitly. The
    identifier reservation ledger is checked the same way.
    """
    from . import allocation

    if registry is None:
        registry = loader.load_registry()
        if released_hashes is None:
            released_hashes = loader.released_governing_hashes()
        if receipts is None:
            receipts = loader.load_receipts()
        if reservations is None:
            reservations = allocation.load_reservations()
    if released_hashes is None:
        released_hashes = {}
    if receipts is None:
        receipts = {}
    if reservations is None:
        reservations = {}
    if schemas is None:
        schemas = loader.load_schemas()
    if taxonomies is None:
        taxonomies = loader.load_taxonomies()
    registry.setdefault("governing", {})

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
    check_source_links(registry, report)
    check_source_lineage(registry, report)
    check_reserved_identities(registry, report, receipts)
    check_governing(registry, report, released_hashes)
    allocation.check_reservations(registry, receipts, reservations, report)
    return report

# Identifier Rules

- `AUTH-0001` and upward: stable author entities.
- `SR-GOV-000001` and upward: governing references (canon-facing, constitutional, authority-axis, functional-source, kernel-reference, protocol, specification, publication-protocol, ingress, language-contact). Immutable once released; superseded by a new `SR-GOV-*`, never rewritten.
- `SR-OBJ-000001` and upward: stable Tier-2 research-object families. `SR-OBJ-*` is exclusively Tier-2 research.
- `SRC-000001` and upward: source objects (archival identity: DOI, archive, labeled outbound links).
- `REL-000001` and upward: typed relations.
- `RCPT-000001` and upward: admission receipts.

Identifiers establish identity only. They do not encode prestige, evidence strength, truth, maturity, or authority beyond the record's explicit fields.

The three identities are independent and not interchangeable. A work may hold `SRC-*` archival identity, `SR-GOV-*` governing identity, and `SR-OBJ-*` research identity in any combination; a governing work normally has no `SR-OBJ-*`, and a Tier-2 object that lists `governing_refs` inherits none of their authority.

A DOI identifies an external archival anchor, not a library record. One DOI may anchor several member works (shared-archive DOI); each keeps its own `SRC-*`, and the shared condition is recorded in notes and typed `shared_archive` in `related_dois`. Alternate, earlier, or disputed DOIs are typed `related_dois` entries; only genuinely unresolved identity questions go to `releases/open-seams.yaml`. Nothing is silently reconciled, and DOIs are never invented for works whose source does not establish them.

Revisions normally retain an ObjectID and change the version; the previous state is preserved under `registry/objects/history/`. A materially changed object, contract, authority role, or publication role requires a new ObjectID or explicit seam.

An ObjectID named on a non-accepted receipt (RETURNED_FOR_REPAIR, REJECTED) is reserved for that submission and is never reallocated to a different work; it enters the registry only when the same work is re-admitted. The validator (`reserved-identities`) rejects a registered object that carries such an ID without an ACCEPTED receipt.

Source identity (`SRC-*`) is distinct from the archive concept (`concept_doi`) and from a specific deposited version (`version_doi`). A later edition of the same named work normally advances `version` on the same `SRC-*` (or supersedes it with a new `SRC-*` that lists the old one in `supersedes`); a new version DOI alone never creates a new source or research object.

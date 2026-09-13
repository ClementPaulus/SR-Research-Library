# Identifier Rules

- `AUTH-0001` and upward: stable author entities.
- `SR-GOV-000001` and upward: governing references (canon-facing, constitutional, authority-axis, functional-source, kernel-reference, protocol, specification, publication-protocol, ingress, language-contact). Immutable once released; superseded by a new `SR-GOV-*`, never rewritten.
- `SR-OBJ-000001` and upward: stable Tier-2 research-object families. `SR-OBJ-*` is exclusively Tier-2 research.
- `SRC-000001` and upward: source objects (archival identity: DOI, archive, labeled outbound links).
- `REL-000001` and upward: typed relations.
- `RCPT-000001` and upward: admission receipts.

Identifiers establish identity only. They do not encode prestige, evidence strength, truth, maturity, or authority beyond the record's explicit fields.

The three identities are independent and not interchangeable. A work may hold `SRC-*` archival identity, `SR-GOV-*` governing identity, and `SR-OBJ-*` research identity in any combination; a governing work normally has no `SR-OBJ-*`, and a Tier-2 object that lists `governing_refs` inherits none of their authority.

A DOI identifies an external archival anchor, not a library record. One DOI may anchor several member works (shared-archive DOI); each keeps its own `SRC-*`, and the shared condition is recorded in notes. Alternate or disputed DOIs are preserved in `identifier.other`, `missingness`, and `releases/open-seams.yaml`, never silently reconciled. DOIs are never invented for works whose source does not establish them.

Revisions normally retain an ObjectID and change the version; the previous state is preserved under `registry/objects/history/`. A materially changed object, contract, authority role, or publication role requires a new ObjectID or explicit seam.

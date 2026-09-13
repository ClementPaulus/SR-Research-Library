# Structura Reditus Research Library — Library Specification

Specification version: SR-LIBRARY.v1.0.0
Schema version: SR-SCHEMA.v0.4.0
Taxonomy version: SR-TAXONOMY.v0.2.0

Governing flow:
`IDENTIFY -> REGISTER -> CLASSIFY -> RELATE -> VALIDATE RECORD -> ACCEPT / RETURN FOR REPAIR / REJECT -> RETRIEVE`

## 1. Object and placement

The Structura Reditus Research Library is a **Tier-0 organizational and
retrieval system** for registering, classifying, relating, validating,
historizing, and retrieving **Tier-2 research works**.

The library does **not** determine how research is performed and does **not**
decide whether a scientific claim is true. **Library admission means only that
a research record satisfies the library's organizational contract.**

### 1.1 Governing hierarchy

- **Reditus** = the object: admissible return through collapse under declared
  conditions.
- **Structura Reditus** = the field.
- **Generative Collapse Dynamics (GCD)** = foundational theory.
- **Tier-1 / Tier-0 / Tier-2** = authority architecture.
- **UMCP / RCFT / ULRC** = functional systems.
- **Tier-2** = Translation and Expansion Authority.
- **The Research Library** = Tier-0 organizational infrastructure for Tier-2
  research records.

The library does not create a new authority tier, theory, functional system,
or replacement for Structura Reditus. This repository is independent of, and
does not modify, GCD v2.3.3 or any historical GCD release.

### 1.2 Preserved distinctions

The library preserves the distinction between:

1. author identity;
2. research object;
3. source object;
4. relation;
5. authority status;
6. evidence status;
7. library-admission status.

No tool in this repository conflates any of these.

## 2. Identifier namespaces

| Entity          | Namespace     | Example         |
|-----------------|---------------|-----------------|
| Author          | `AUTH-NNNN`   | `AUTH-0001`     |
| Governing reference | `SR-GOV-NNNNNN` | `SR-GOV-000001` |
| Research object | `SR-OBJ-NNNNNN` | `SR-OBJ-000001` |
| Source          | `SRC-NNNNNN`  | `SRC-000001`    |
| Relation        | `REL-NNNNNN`  | `REL-000001`    |
| Receipt         | `RCPT-NNNNNN` | `RCPT-000001`   |

Identifiers are stable. Author identity remains stable while contribution
history changes. `SR-OBJ-*` is reserved exclusively for Tier-2 research;
`SR-GOV-*` for governing-reference identity; `SRC-*` for source/archive
identity. A work may hold these identities in any combination and they are
never interchangeable.

## 3. Registry as source of truth

The library is a **three-surface architecture**:

1. **Governing Reference Registry** (`registry/governing/`, `SR-GOV-*`) —
   canon-facing, constitutional, authority-axis, functional-source,
   kernel-reference, protocol, specification, publication-protocol, ingress,
   and language-contact references. Not research objects. Immutable once
   released; supersession creates a new record and preserves the old one.
2. **Tier-2 Research Object Registry** (`registry/objects/`, `SR-OBJ-*`) —
   the living research body.
3. **Source / Archive Registry** (`registry/sources/`, `SRC-*`) — where a
   work actually lives; canonical DOI/archive identity and labeled outbound
   links; never mirrors whole papers.

The files under `registry/` are the **source of truth**:

- `registry/authors/` — author records (JSON, `author.schema.json`).
- `registry/governing/` — governing references (JSON, `governing.schema.json`);
  `tier-1/`, `tier-0/`, `mixed/` are organizational views selected by the
  record's `authority_scope`, and records with no Tier-1/Tier-0 burden sit at
  the root. The validator checks that view and scope agree.
- `registry/objects/` — current research-object records (JSON,
  `object.schema.json`).
- `registry/objects/history/` — preserved historical object states
  (never rewritten).
- `registry/sources/` — source records (JSON, `source.schema.json`).
- `registry/relations/` — relation records (JSON, `relation.schema.json`).

The public surface under `site/` is **generated from** the registry
(`python -m validators.build_site`) and is never a second independent
database.

An ACCEPTED record enters the registry through
`python -m validators.admit <record> --register`, which archives any
previously registered version of the same object to
`registry/objects/history/` before writing the new state. A registered state
is never rewritten at the same version; RETURNED_FOR_REPAIR and REJECTED
records are never registered. Their submissions are archived for audit beside
their receipts (`receipts/repair/RCPT-NNNNNN.submission.json`).

### 3.1 Governing-reference contract

A governing record carries: `governing_id`, `title`, `source_id`, `version`,
`status` (`active` | `superseded` | `historical` | `candidate` | `unresolved`),
`governing_role`, `authority_scope` (`tier_1[]`, `tier_0[]`), `source_role`,
`immutable_record`, `active_from`, `supersedes`, `superseded_by`, `doi`,
`canonical_link`, `scope`, `non_goal`, `missingness`, `notes`.

- **Authority belongs to the admitted burden.** A whole source is never
  classified Tier-1 because it contains Tier-1 material, nor Tier-0 because
  it contains protocol material. `authority_scope` states exactly which
  Tier-1 and Tier-0 burdens the source admits; either list may be empty and
  both may be populated (mixed).
- **Candidates are not authority.** Repair or adoption candidates carry
  `status: candidate`; sources that disagree on role, version, DOI, or
  adoption status yield `status: unresolved`. Nothing is promoted to active
  authority without an adoption record.
- **Immutability.** Once a governing record is listed in a release manifest
  (`governing_immutable_hashes`), its historical meaning is not edited in
  place; only `status` and `superseded_by` may change. A later active record
  must name the old one in `supersedes`; the old record is preserved with
  `superseded_by` set and `status: superseded`. The validator enforces both
  the hash and the supersession pointers.
- **No inheritance.** Tier-2 objects may list `governing_refs`; each must
  resolve to an existing `SR-GOV-*` record (Gate F blocks otherwise). The
  reference constrains the object and transfers no authority —
  `authority.tier` remains `tier-2`.
- **No invented DOIs.** `doi` is recorded only when the supplied source
  establishes it.

### 3.2 Sources, external links, and shared DOIs

Source records expose labeled outbound `links`
(`label`, `type` ∈ {canonical, archive, full_text, publisher, code, data,
supplement, project_page}, `url`, `preferred`). At most one link per source
is preferred; for DOI-bearing works the DOI resolver is normally the
preferred canonical link, and a DOI link must resolve `identifier.doi`. Archive
landing pages are added only when known or resolvable; full-text, code, data,
and supplement URLs are never guessed. PDFs are never stored or mirrored.
External-link failure never deletes a source; DOI identity survives a broken
web link.

A DOI may legitimately identify an archive containing several distinct works.
Each member work keeps its own SourceID and the shared-archive condition is
recorded in `notes` and typed `shared_archive` in `related_dois`; member works
are neither collapsed into one object nor counted as separate DOI deposits.
Alternate or disputed DOIs are preserved as typed `related_dois` entries and,
where genuinely unresolved, in `releases/open-seams.yaml`; they are never
silently reconciled.

### 3.3 Source lineage

Source identity (`SRC-*`) ≠ archive concept (`concept_doi`) ≠ specific
deposited version (`version_doi`). Source records carry `version`, `status`
(`active` | `superseded` | `historical`), `concept_doi`, `version_doi`, typed
`related_dois[]` (`earlier_version`, `later_version`, `alternate_record`,
`shared_archive`, `first_edition`, `external_metadata`, `software`, `other`),
and append-preserving `supersedes[]` / `superseded_by`. The anchoring
`identifier.doi` must be the concept or the version DOI; the two are never
collapsed; a superseded source is preserved with `status: superseded`. A new
version DOI alone never creates a new source or research object: the same
named work advances `version` (or is superseded by a new `SRC-*` that names
the old one), and the corresponding Tier-2 object, if its library description
changes, advances its record version with the prior state archived.

## 4. Schemas

JSON Schema (draft 2020-12) validation exists for authors, governing
references, objects, sources, relations, and receipts under `schema/`.
Registry records are deterministic machine-readable JSON (YAML is also
accepted by the loaders).

### 4.1 Timestamps

Every registry event field — `registered` (author), `date` (object version),
`declared` (relation), and `generated` (receipt, release manifest) — is an
ISO 8601 timestamp with an explicit time-zone designator:
`YYYY-MM-DDThh:mm:ssZ` or `YYYY-MM-DDThh:mm:ss±HH:MM`. Date-only values are
rejected by the schemas, the validators, and Gate G, because a bare date
leaves its time basis (UTC versus local) ambiguous. Either UTC (`Z`) or local
time with its offset is acceptable; the offset must be written, never
assumed.

## 5. Controlled taxonomies

Controlled taxonomies live under `taxonomy/` and govern the main
classification axes. Unrestricted free text may **not** replace controlled
values for:

- primary domain (`domains.yaml`)
- Tier-2 class (`tier2_classes.yaml`)
- structural focus (`focuses.yaml`)
- evidence mode (`evidence_modes.yaml`)
- provenance (`provenance_types.yaml`)
- maturity (`maturity_states.yaml`)
- relation type (`relation_types.yaml`)
- publication state (`publication_states.yaml`)
- functional locus (`functional_loci.yaml`)

Free-text explanatory fields supplement controlled values; they never replace
them.

Every proposal to add or deprecate a controlled term is recorded in
`taxonomy/extensions.yaml` (term, taxonomy, definition, insufficiency of
existing terms, nearest terms, examples, ambiguity risk,
backward-compatibility effect, decision, version introduced). A term enters a
taxonomy file only once its extension record is `accepted`, and
`taxonomy/VERSION` is bumped with it.

### 5.1 Tier-2 primary classes

Tier-2 supports exactly seven primary classes:

1. `domain-translation`
2. `diagnostic`
3. `language-contact`
4. `pedagogical`
5. `candidate`
6. `external-ingress`
7. `handoff`

Each research object has **exactly one** primary Tier-2 class. Secondary
classes are allowed.

## 6. Research-object record contract

Each research object contains at least:
`object_id`, `title`, `authors`, `authority.tier`, `tier2_class.primary`,
`tier2_class.secondary`, `functional_locus`, `source_ids`, `lens`,
`domain.primary`, `domain.secondary`, `object_of_study`,
`structural_focus.primary`, `structural_focus.secondary`, `main_question`,
`secondary_questions`, `claim_layers`, `evidence_mode.primary`,
`evidence_mode.secondary`, `provenance`, `maturity`, `relations`, `version`,
`date`, `publication_state`, `source_boundary`, `authority_boundary`,
`scope`, `exclusions`, `preserved_meaning`, `missingness`,
`distortion_or_substitution_risk`, `next_burden`, `repair_route`, `notes`.

See `schema/object.schema.json` for the authoritative field definitions.

## 7. External-source discipline (mandatory)

External work remains an **external source object** (`registry/sources/`).
A Structura Reditus record may cite, compare, translate, map, or construct a
local Tier-2 closure around an external source, but it must preserve:

- original authorship;
- source-native claims;
- original source identity;
- the distinction between source observation and local interpretation
  (via `claim_layers` layer declarations);
- unavailable evidence or missingness;
- an explicit authority boundary.

A Structura Reditus or GCD interpretation is **never** attributed to an
external author unless the source actually makes that interpretation.

## 8. Automated validators

`python -m validators.validate` runs checks for at least:

schema validity; unique IDs; AuthorID references; SourceID references;
RelationID references; taxonomy references; required fields; date formats;
version formats; duplicate object collisions; broken relations; missing
primary Tier-2 class; missing primary domain; missing structural focus;
missing main question; missing evidence mode; missing provenance; missing
authority boundary; missing source boundary; missing next burden.

Validation is organizational only. No check evaluates whether a research
claim is true, whether it agrees with GCD, or whether its author holds any
credential.

## 9. Admission gates

Exactly seven admission gates (`validators/gates.py`):

| Gate | Name |
|------|------|
| A | Identity |
| B | Tier placement |
| C | Source and provenance |
| D | Classification |
| E | Boundary and missingness |
| F | Relation integrity |
| G | Library durability |

Admission outcomes are exactly: `ACCEPTED`, `RETURNED_FOR_REPAIR`,
`REJECTED`.

Decision logic:

- **ACCEPTED** — all active gates pass and no evaluability-blocking
  missingness remains.
- **RETURNED_FOR_REPAIR** — required structure is missing or incomplete, the
  gap blocks admission, and the same object can reasonably return through
  declared repair.
- **REJECTED** — an evaluable admission gate fails because the submitted
  object violates the active library contract.

`RETURNED_FOR_REPAIR` is never collapsed into `REJECTED`.

Work is **never** rejected because it disagrees with GCD, is controversial,
comes from an external author, is unconventional, has a negative result,
reports non-return, or challenges another Tier-2 work. **Disagreement is not
an admission failure.**

AUTH-0001 receives the same admission requirements as every future author.
There are no founder exceptions.

## 10. Missingness classes

- `NON_BLOCKING`
- `EVALUABILITY_BLOCKING`
- `CONTRACT_VIOLATING`
- `AUTHORITY_BOUNDARY`
- `SOURCE_BOUNDARY`
- `PUBLICATION_BOUNDARY`
- `REPAIRABLE`
- `UNRESOLVED_SEAM`

Missingness is preserved, never silently filled. When information is missing,
the gap is preserved and the affected record is marked for repair. Nothing is
guessed; inconsistent source data is never silently reconciled.

## 11. Receipts

Every admission decision generates a human-readable (`.md`) and
machine-readable (`.json`) receipt (`validators/receipts.py`), stored under
`receipts/accepted/`, `receipts/repair/`, or `receipts/rejected/`.

- An **accepted** receipt states the decision, ObjectID, title, AuthorID(s),
  version, date, authority, primary Tier-2 class, functional locus, primary
  domain, structural focus, main question, evidence mode, provenance,
  maturity, SourceIDs, RelationIDs, publication state, per-gate PASS results,
  non-blocking missingness, open burdens, and next burden. It explicitly says
  that library admission means organizational conformance only and does not
  imply scientific truth, endorsement, Tier-0 adoption, or Tier-1 admission.
- A **repair** receipt states the decision, submission identity, provisional
  ObjectID, AuthorID(s), version, failed or blocked gates, missing structure,
  missingness class, affected burden, why it blocks admission, exact repair
  required, permitted source/evidence, whether repair changes the object,
  whether a new ObjectID is required, whether a seam declaration is required,
  fields already accepted, fields still blocked, and the exact resubmission
  condition.
- A **rejection** receipt states the decision, submission identity, failed
  gates, established violation, violation class, why admission is not
  permitted, whether the same object can be repaired, whether a new
  object/version/seam is required, and resubmission conditions. It explicitly
  states that rejection concerns library admission only and does not by
  itself establish that the underlying research claim is false.

## 12. Author profiles

`validators/profiles.py` generates author profiles from registry objects
only. A profile contains only reconstructible quantities:

- total registered authored objects;
- normalized primary-domain distribution;
- normalized Tier-2-class distribution;
- normalized structural-focus distribution;
- normalized evidence-mode distribution;
- normalized provenance distribution;
- normalized maturity distribution.

There is **no universal author score**. Prestige, credentials, degree level,
institutional affiliation, citations, originality, quality, importance, and
author rank are never numerically weighted. Credentials may be shown as
provenance metadata with a verification state (`unverified`,
`self-declared`, `externally-verified`).

The library is an **even Tier-2 organizational surface**, not a prestige
hierarchy.

## 13. Retrieval and cross-domain transfer

The public surface supports browsing/filtering by: author, domain, subdomain
(secondary domain), object of study, structural focus, main question, Tier-2
class, evidence mode, provenance, maturity, relation, source, and date.

Cross-domain retrieval follows the conceptual route:

```
FIND -> COMPARE -> EXTRACT TRANSFERABLE STRUCTURE
     -> REINSTANTIATE LOCALLY -> VALIDATE LOCALLY
```

The library never automatically transfers: thresholds; adapters; closure
gates; evidence standards; causal claims; ontological claims; source
authority.

## 14. History

Historical states are supported rather than overwritten. The library
preserves: first registration; object revisions
(`registry/objects/history/`); supersessions (`supersedes` field and
`supersedes` relations); relation additions; taxonomy changes (taxonomy files
are versioned); classification changes; source-boundary changes;
publication-state changes. `validators.loader.archive_object_version` refuses
to rewrite an existing historical state.

## 15. Releases

The library is versioned independently, beginning with the pre-releases
`SR-LIBRARY.v0.1.0` and `SR-LIBRARY.v0.2.0` and the first release
`SR-LIBRARY.v1.0.0`. Each release manifest
(`python -m validators.release <version> [--final]`) records: schema version; taxonomy
version; author count; object count; source count; relation count;
governing count; receipt count; manifest of IDs; governing immutable hashes;
date/timezone; open seams; migration notes; and
SHA-256 hashes of schema, taxonomy, and registry files. Previous releases are
never silently rewritten.

Unresolved contract decisions are tracked as seams in
`releases/open-seams.yaml` (`SEAM-NNNN`, area, description, status) and
copied into each release manifest. Closed seams remain in the file with
status `closed`; they are never deleted.

## 16. Admission authority exclusions

Publication status, credentials, citation counts, and agreement with GCD are
**never** used as admission authority. Independent researchers and groups can
work within their own domains while their research remains structurally
searchable and comparable across Structura Reditus.

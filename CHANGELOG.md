# Changelog

All notable changes to the Structura Reditus Research Library are documented
here. The library is versioned independently of GCD and of any other
Structura Reditus artifact. Previous releases are never silently rewritten.

## SR-LIBRARY.v1.0.0 — 2026-09-13

First release (non-pre-release). Registry state is that of SR-LIBRARY.v0.2.0
plus the items below; nothing in a previous manifest was rewritten.

### Added

- Open seams SEAM-0018..0021 carried from corpus census working package
  v0.2: casepack archive lineage (earlier version DOIs 19703023 and 19701729
  verified as versions under the same Zenodo concepts as the listed DOIs),
  Provenance & Canon Note DOI 17925173 (v1.0 under concept 17925172), the
  Saturn decagon public-only `SOURCE_NEEDED` queue item, and the deferred
  census candidates. Sources SRC-000012/013/023 annotated in `missingness`.
- `python -m validators.release --final` writes a non-pre-release manifest.

### Removed

- Placeholder `.gitkeep` files from populated directories; the archived rc1
  engine zip (recoverable from commit `c8a87f1`). Handoff and census working
  packages are git-ignored and not part of the release.

### Release notes

- 46 sources, 16 registered Tier-2 objects (3 RETURNED_FOR_REPAIR archived
  beside their receipts), 3 relations, 18 governing references (13 active,
  3 candidate, 2 unresolved), 22 receipts, 1 author.
- Open seams SEAM-0002..0021 are carried in the manifest. A release does not
  imply that every work in it is true, validated, conformant under UMCP, or
  endorsed by Structura Reditus; admission is organizational conformance
  only.

## SR-LIBRARY.v0.2.0 — 2026-09-13 (pre-release)

First populated release: the verified DOI-bearing corpus and the governing
reference layer.

### Added

- **Governing Reference Registry** (`registry/governing/`, `SR-GOV-*`,
  `schema/governing.schema.json`): 18 records populated from the full-text
  governing sources supplied in handoff bundle
  `SR_LIBRARY_GOVERNING_CORE_HANDOFF_v1_0` (Summa Reditus, Reditus &
  Structura Reditus, GCD Canon Placement, Functional Systems of GCD, the
  Threefold Authority Order, UMCP/RCFT/ULRC Operating Systems, Liber Collapsus
  v2.0, GCD/UMCP Whitepaper v2.1.5, Structura Collapsus, UMCP Kernel
  Specification rc2 and its Repair Audit, both Publishing Protocol documents,
  the Ingress Paper, Ingress/Publication Architecture, Refusal as Structure).
  Each record carries its exact admitted burden in `authority_scope`; view
  directories `tier-1/`, `tier-0/`, `mixed/` follow that scope. Statuses:
  13 active, 3 candidate, 2 unresolved. Records are immutable once released
  (`governing_immutable_hashes` in the manifest) and superseded, never
  rewritten; the validator enforces immutability, supersession pointers, and
  view placement.
- Optional `governing_refs` on Tier-2 objects; each must resolve to an
  `SR-GOV-*` record (Gate F blocks otherwise) and transfers no authority.
- **Source registry populated**: 46 sources (`SRC-000001..046`) — the
  verified Zenodo/Research Square corpus (34) and the governing-handoff
  sources (12). Every DOI was resolved against public Zenodo/Crossref
  metadata; observed titles, creators, dates, landing pages, and archive file
  listings are recorded on the records. Shared-archive DOIs (four-paper
  release, Orientation Series, Episteme Construction/Common Doorway,
  Provenance Note/Geometry of Admissible Seams) are recorded per member work.
- Optional labeled outbound `links` on sources (`canonical`, `archive`,
  `full_text`, `publisher`, `code`, `data`, `supplement`, `project_page`;
  at most one preferred; DOI links must resolve `identifier.doi`), validated
  by `check_source_links`. No PDFs are stored.
- **Tier-2 objects**: 19 submitted through the seven gates; 16 ACCEPTED and
  registered (`SR-OBJ-000001..015`, `SR-OBJ-000018`), 3 RETURNED_FOR_REPAIR
  (`SR-OBJ-000016` DOI/title mismatch; `SR-OBJ-000017`, `SR-OBJ-000019`
  candidate-class works whose sources state no next burden). Non-accepted
  submissions are archived beside their receipts as
  `receipts/repair/RCPT-NNNNNN.submission.json`. Objects `SR-OBJ-000001..003`
  revised to 1.0.1 with `governing_refs: [SR-GOV-000010]` (Zenodo
  isSupplementTo), version 1.0.0 preserved in `registry/objects/history/`.
- 3 relations (`REL-000001..003`, `extends`); 22 receipts (`RCPT-000001..022`).
- Public site rebuilt as three surfaces — Governing References, Tier-2
  Research, Sources & Archives — with per-entity pages for governing
  references, objects, sources, authors, and receipts; per-axis views
  (domain, structural focus, Tier-2 class, evidence mode, maturity), a
  timeline, a historical/prefreeze source view, governing filter chips, and
  labeled external links. A source is never shown with a Tier-2
  classification.
- Open seams SEAM-0008..0017 (shared DOIs, DOI lineage 18819238/18819239,
  Liber Collapsus title/edition, Collapse Formalism DOI mismatch, title
  variance, candidate next-burden repairs, DOI verification queue with
  observed Zenodo titles, publishing-protocol adoption status, ingress
  supersession, handoff evidence not committed). SEAM-0001 closed.
- Loader helpers for receipts and release manifests; `loader.load_registry`
  now returns a `governing` kind.

### Changed

- Schema SR-SCHEMA.v0.2.0 → SR-SCHEMA.v0.3.0 (source `links`, object
  `governing_refs`, new governing schema).
- Release manifests record `governing_count`, `id_manifest.governing`, and
  `governing_immutable_hashes`; receipt counting ignores archived
  submissions.

### Not done, deliberately

- No PDF or full text from the handoff bundle is committed; the bundle is
  ignored by git and referenced by SHA-256 on each new source record.
- No DOI was invented for works whose supplied source does not establish one.
- No candidate or unresolved governing record was promoted to active.

## Unreleased (pre-v0.2.0 integration)

Unified the two implementation branches
(`copilot/build-initial-implementation` and
`copilot/create-structura-reditus-library`) and the uploaded
`SR-LIBRARY.v0.1.0-rc1` engine package into a single library.

### Added

- Full governing specification `docs/SR-RESEARCH-LIBRARY-SPEC.v0.1.md`,
  `ENGINE_CONTRACT.md`, and `docs/` (identifiers, receipts, main-branch
  protection ruleset) from the rc1 engine package. The package zip was kept
  under `releases/archive/` through SR-LIBRARY.v0.2.0 and then removed once
  fully integrated; it remains recoverable from git history (commit
  `c8a87f1`).
- CI workflow (`.github/workflows/validate.yml`), pull-request template, and
  taxonomy-extension issue form; `pyproject.toml`, `requirements*.txt`.
- `taxonomy/missingness_classes.yaml`: missingness classes are now a
  controlled taxonomy file (loaded by `validators.loader`) rather than a
  hard-coded list.
- `examples/OBJECT_TEMPLATE.json`: blank record with every required field.
- `python -m validators.admit --register`: places an ACCEPTED record into
  `registry/objects/`, archiving any previously registered version to
  `registry/objects/history/` first. Non-accepted records are never
  registered.
- `taxonomy/extensions.yaml`: machine-readable record of every taxonomy term
  proposal and its outcome (EXT-0001–EXT-0006).
- `releases/open-seams.yaml`: tracked open seams (SEAM-0001–SEAM-0007),
  copied into release manifests.
- `registry/README.md` and `site/README.md` describing the source of truth
  and the generated projection (including the site route-family contract).
- Tests for registration, extension-record consistency, and seam records.

### Changed

- Schema SR-SCHEMA.v0.1.0 → SR-SCHEMA.v0.2.0: registry event fields
  (`authors.registered`, `objects.date`, `relations.declared`) are now ISO
  8601 timestamps with an explicit time-zone designator (`Z` or `±HH:MM`)
  instead of date-only values, whose time basis was ambiguous. The
  validators and Gate G enforce the same pattern.
- `AUTH-0001.registered` repaired from `2026-09-13` to `2026-09-13T02:48:30Z`,
  the recorded time of the commit that created the record
  (`2026-09-12T21:48:30-05:00` America/Chicago).
- Taxonomy SR-TAXONOMY.v0.1.0 → SR-TAXONOMY.v0.2.0: added domains
  `systems-theory`, `cognitive-science`, `social-science`; added publication
  states `draft`, `internal`, `archived`. No existing terms removed or
  redefined.

## SR-LIBRARY.v0.1.0 — 2026-09-13 (pre-release)

First working implementation.

### Added

- Repository structure: `schema/`, `taxonomy/`, `registry/`, `receipts/`,
  `validators/`, `tests/`, `releases/manifests/`, `site/`, `examples/`.
- Full library specification (`LIBRARY_SPECIFICATION.md`).
- JSON Schemas (draft 2020-12) for authors, objects, sources, relations, and
  receipts (`schema/`, SR-SCHEMA.v0.1.0).
- Controlled taxonomies for domains, structural focuses, Tier-2 classes,
  evidence modes, provenance types, maturity states, relation types,
  publication states, and functional loci (`taxonomy/`, SR-TAXONOMY.v0.1.0).
- First author record AUTH-0001 (Clement Paulus, ORCID 0009-0000-6069-8234,
  status active) with only the supplied identity fields.
- Automated validators (`python -m validators.validate`): schema validity,
  unique IDs, AuthorID/SourceID/RelationID references, taxonomy references,
  required fields, date formats, version formats, duplicate object
  collisions, broken relations, and required-presence checks.
- Seven admission gates (A–G) with exactly three outcomes (ACCEPTED /
  RETURNED_FOR_REPAIR / REJECTED) and eight missingness classes
  (`python -m validators.admit`).
- Human-readable and machine-readable receipt generation for all three
  decisions.
- Author-profile generation with reconstructible quantities only (no author
  score, no prestige weighting).
- Release-manifest generation with counts, ID manifest, open seams,
  migration notes, and SHA-256 hashes (`python -m validators.release`).
- Static public library surface generated from the registry
  (`python -m validators.build_site`).
- Test suite covering all contract scenarios (`tests/`).
- Documentation: `README.md`, `CONTRIBUTING.md`.
- Synthetic example submissions and receipts, explicitly marked synthetic
  (`examples/`).

### Notes

- The registry contains no research objects, sources, or relations yet:
  no actual source metadata was supplied, and records are never
  bulk-populated or fabricated.
- GCD v2.3.3 and historical GCD objects are not contained in and were not
  modified by this repository.

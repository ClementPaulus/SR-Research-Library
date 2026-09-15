# Changelog

All notable changes to the Structura Reditus Research Library are documented
here. The library is versioned independently of GCD and of any other
Structura Reditus artifact. Previous releases are never silently rewritten.

## Unreleased — toward SR-LIBRARY.v1.1.0 (foundation for the corpus expansion)

### Added (2026-09-14 researcher portal — infrastructure, additive)

- `portal/`: public Django 5.2 LTS researcher portal (accounts with automatic
  AuthorID registration, guided uploads and source-grounded preparation,
  immutable revisions, the unchanged admission engine run in isolated pinned
  checkouts, receipts, repair, GitHub App publication with verification,
  search, handoff export, review queue). 39 portal tests; browser acceptance
  evidence under `docs/portal-evidence/browser/`.
- `validators/allocation.py` + `python -m validators.reserve`: repository-wide
  identifier allocation and the additive reservation ledger
  `registry/reservations/` (`schema/reservation.schema.json`,
  SR-RESERVATION.v0.1.0); `check_reservations` in the validator.
- `validators/execution.py` + `schema/execution.schema.json`
  (SR-EXECUTION.v0.1.0): companion execution manifests under
  `receipts/executions/` binding a receipt to its submission hash, source-file
  hashes, engine revision, schema/taxonomy versions, and registry base.
- `admit --write` now preserves the exact submitted-record snapshot for every
  decision (accepted included) and writes bundles atomically; existing receipt
  IDs are never overwritten. `admit.evaluate_and_write` is the single entry
  point for CLI and portal.
- `validators/search.py`: shared search index (`site/data/search_index.json`)
  and documented matching semantics; `site/search.html`. Baseline misses
  (“physically constrained”, “Clement”, `REL-000006`) resolved.
- Receipt selection on object pages by version and chronology; all attempts
  listed. Census tests refactored: exact 2026-09 facts moved to
  `tests/fixtures/census_2026_09_snapshot.json`; live tests permit
  evidence-backed growth.
- `docs/portal-evidence/baseline-810f4222.json` + `tests/test_baseline_preservation.py`
  (225 historical artifacts byte-identical).
- Automatic preparation as the default experience (`portal/submissions/preparation.py`):
  recorded preparation steps with live progress, DOI/arXiv/version identification,
  duplicate checks against the committed registry, explainable keyword-based
  classification suggestions (always uncertain), automatic source proposal from
  the files' own statements, readiness assessment with why/blocks/resolves
  questions, confirmation-without-retyping, repair reuse with receipt-flagged
  fields, journey stepper, required resolutions for version ambiguity and
  possible duplicates, `manage.py reconcile`. Four browser journeys
  (`portal/tests/run_journeys.sh`) documented in `docs/PORTAL_WALKTHROUGH.md`.
- Docs: PORTAL_IMPLEMENTATION, PORTAL_OPERATIONS, PORTAL_CONTRIBUTING,
  PORTAL_WALKTHROUGH, PORTAL_ACCEPTANCE; MAIN_PROTECTION_RULESET (effective check name `validate`),
  RECEIPTS and IDENTIFIERS clarifications; issue forms fixed (`description`)
  and extended. CI: portal job and runtime path-policy diff.

No released record, receipt, schema, taxonomy, or manifest was rewritten;
`schema/VERSION` stays SR-SCHEMA.v0.4.0 because no record schema changed.

Additive cleanup on top of the frozen v1.0.0 release; no released manifest or
released governing record was rewritten.

### Added (2026-09 Tier-2 census, repair, and ingress pass)

- Tier-2 admission decision rule (tests A–H and census processing order) in
  `LIBRARY_SPECIFICATION.md` §6.1; readback report
  `docs/TIER2_CENSUS_2026-09.md`.
- Repairs under reserved identities: `SR-OBJ-000017` (Collapse Calculus) and
  `SR-OBJ-000019` (A Geometry of Admissible Seams) resubmitted as 1.0.1 with
  source-stated next burdens and ACCEPTED (RCPT-000023, RCPT-000024); the
  RETURNED_FOR_REPAIR receipts are preserved. `SR-OBJ-000016` (The Collapse
  Formalism) stays RETURNED_FOR_REPAIR — no source resolves to the titled work
  (SEAM-0011).
- Eleven new Tier-2 objects `SR-OBJ-000020..030` (RCPT-000025..035): The
  First Seam-Chain Casepack; Nested Return in a Composite Diamond Clock;
  Recursive Accelerating Return; Identifiable Return in Memristive Associative
  Memory; Language Across Articulation; Empirical Regime Auditing v2.0 (on the
  existing `SRC-000046`); Confinement as Integrity Collapse (historical);
  Contract-First Epistemology full course, Semester I, Semester II, and the
  Syllabus and Audit Receipt.
- Thirteen sources `SRC-000047..059`, including the first two external
  sources (`SRC-000048` Lourette et al., `SRC-000051` He et al.) whose DOIs
  stay with the external articles, and `SRC-000059` (Saturn Southern Decagon,
  source only). `SRC-000019` (DMT) carries the v1.0 record as
  `earlier_version`; no duplicate DMT object.
- Relations `REL-000004` (Seam-Chain Casepack extends the Welded Seam
  Casepack) and `REL-000005` (Semester II extends Semester I), both stated by
  the sources.
- Bridge-detection projection (`validators/bridges.py`,
  `site/data/bridge_candidates.json`): retrieval adjacency ≠ candidate
  relation ≠ declared relation; rebuilt with the new objects.
- Tests `tests/test_census_2026_09.py` and `tests/test_bridges.py`.

### Changed (2026-09 census pass)

- SEAM-0013 closed (next burdens read from the deposited PDFs). SEAM-0011,
  SEAM-0020, SEAM-0021 updated in place with the pass results; all remain
  open. Next free identifiers: `SR-OBJ-000031`, `SRC-000060`, `SR-GOV-000020`,
  `REL-000006`, `RCPT-000036`.
- Publication update, Identifiable Return in Memristive Associative Memory:
  Version 1.2 (frozen 9 September 2026) is publicly deposited on Zenodo as
  10.5281/zenodo.22695434 (concept 22695433; verified by API 2026-09-13).
  `SRC-000052` gains the DOI lineage, venue, and links; `SR-OBJ-000023`
  resubmitted as 1.0.1 with `publication_state: archived` (RCPT-000036
  ACCEPTED; RCPT-000028 and the 1.0.0 state in `registry/objects/history/`
  preserved). Metadata only — manuscript text, evidence boundary,
  retrospective analysis, frozen run, claims, authority, and unresolved
  burdens are unchanged; the DOI locates the frozen v1.2 and is not a new
  scientific version. Next free receipt: `RCPT-000037`.
- `ENGINE_CONTRACT.md`: the engine MAY compute provisional structural
  adjacency for retrieval and review and SHALL NOT convert it into a relation
  or any scientific claim.

### Added (2026-09-14 ingress — Prospective Identifiable Return in Associative Memory)

- New distinct Tier-2 object `SR-OBJ-000031` (Prospective Identifiable Return
  in Associative Memory: A Completed Prospective Computational Test of
  Identity, Correction, Discrimination, and Reliability; Final Publication
  Edition v1.0, 14 September 2026) — diagnostic (+external-ingress,
  +domain-translation), locus umcp, domain computer-science, focus return,
  evidence simulation (+prospective-protocol, +computational-reproduction),
  provenance externally-anchored-derivative, maturity prospectively-tested,
  publication state archived. `RCPT-000037` ACCEPTED, all seven gates PASS.
  §6.1 Test A satisfied by a new frozen contract (PIR-COMP-2026-09-14-v1.0),
  new run (PIR-COMP-R1), fresh development and untouched confirmation
  evidence, and a new concept DOI; not a version update of `SR-OBJ-000023`.
- Source `SRC-000060` (corpus-native; Zenodo 10.5281/zenodo.22739943 version,
  10.5281/zenodo.22739942 concept; verified by API 2026-09-14; Preprint,
  CC-BY-4.0; deposited PDF and publication bundle read, not mirrored).
  `SRC-000051` (He et al.) reused as external anchor; `SRC-000052` not
  duplicated and not superseded.
- Relation `REL-000006`: `SR-OBJ-000031` extends `SR-OBJ-000023`, as stated
  by the source (predecessor retained as a separate retrospective object; no
  `supersedes`).
- Recorded result profile as stated by the source: 5,711/6,000 exact
  intended-target recoveries (95.1833%); recurrence gain 0.5520 [0.541667,
  0.562504]; joint-model log loss 0.134226 beating all three simple models;
  reliability partial — 9/10 targets pass, MU-01 fails (159/200, lower bound
  0.712291) as an observed negative result; p = 0.50 control 71/2,000, no
  leakage trigger; procedural stance CONFORMANT. Not physical hardware
  validation; canonical UMCP return/weld not activated.
- New open seam `SEAM-0023` (prospective physical-hardware branch of the
  Identifiable Return lineage stays open; not closed by the computational
  run). Readback surfaces updated (`docs/TIER2_CENSUS_2026-09.md`,
  `registry/README.md`, `tests/test_census_2026_09.py`); site regenerated.
  Next free identifiers: `SR-OBJ-000032`, `SRC-000061`, `SR-GOV-000020`,
  `REL-000007`, `RCPT-000038`.

### Added (v1.1 foundation)

- Typed source lineage on `schema/source.schema.json`: `version`, `status`
  (`active` | `superseded` | `historical`), `concept_doi`, `version_doi`,
  typed `related_dois[]`, `supersedes[]`, `superseded_by`; enforced by
  `check_source_lineage` (anchoring DOI must be concept or version; never
  identical; append-preserving supersession). Populated for every Zenodo
  source from the 2026-09-13 verification (concept vs version resolution),
  including the whitepaper, Finite-Return Casepack, Heterogeneous Local Pass,
  Provenance & Canon Note, Liber Collapsus, DMT, and the empirical-auditing
  companion.
- `check_reserved_identities`: an ObjectID on a non-accepted receipt stays
  reserved for that submission (`SR-OBJ-000016/000017/000019`); next free
  IDs are `SR-OBJ-000020`, `SRC-000047`, `SR-GOV-000020`.
- `/questions/<slug>` route with the slug policy recorded on SEAM-0007.
  Source pages show status, version, and a lineage table.
- `SR-GOV-000019` (GCD/UMCP whitepaper) supersedes the released
  `SR-GOV-000010` with the resolved DOI lineage; the old record is preserved
  with `status: superseded`.
- Liber Collapsus v2.0 (`SRC-000018`) `source_native_claims` populated from
  the supplied full text (Axiom of Reditus, the three requirements of
  return, idem/ipse identity, contract-before-judgment, bounded trace,
  edition boundary).
- `docs/MAIN_PROTECTION_RULESET.md` now names the required CI check
  (`validate`) and gives the ruleset payload to require PRs and green checks
  on `main`.

### Changed

- Schema SR-SCHEMA.v0.3.0 → SR-SCHEMA.v0.4.0 (optional source lineage fields).
- Seams closed in place (closed_by attributes the branch/PR; the release
  generator records where a closure first appears): SEAM-0002 and SEAM-0005
  (site now has per-entity pages), SEAM-0007 (questions route), SEAM-0008
  (handled by shared-archive policy), SEAM-0009 (whitepaper DOI: 18819238
  concept/canonical; 18819239 historical version metadata only), SEAM-0010
  (Liber canonical DOI decision only: 22310064), SEAM-0015 (SR-GOV-000014
  active, SR-GOV-000015 candidate; status-only changes), SEAM-0018 and
  SEAM-0019 (lineage typed on the records). New SEAM-0022 keeps the Zenodo
  record relationship 22310064 <-> 22310544 open as a non-blocking
  UNRESOLVED_SEAM. SEAM-0011 (Collapse Formalism DOI) stays open by design.
- `SRC-000015` missingness no longer calls the DOI lineage unresolved;
  `SRC-000018` stays active on 22310064 with the record relationship
  referred to SEAM-0022. `SRC-000023` (Provenance & Canon Note):
  `version_doi` is 17925173 (the deposit the PDF names), with 17980036 typed
  `later_version` (the shared archive state that also carries A Geometry of
  Admissible Seams, `SRC-000024`).
- Release manifests now record `closed_seams` and
  `closures_first_recorded_in_this_release`.
- `SR-OBJ-000011` (DMT) is unchanged: `SRC-000019` resolves through its
  concept DOI to the Version 2.0 record (22086947); no evidence that the
  library description changed, so no record revision was issued.

### Still pending for v1.1.0

- Source-native claims for works whose full text is not held here
  (Universal Collapse Diagnostics, The Common Doorway, the UMCP CasePack
  anchor, The Collapse Formalism); their missingness lines remain. Collapse
  Calculus and A Geometry of Admissible Seams now carry claims read from
  their deposited PDFs.
- The remaining census candidates without acquired sources (SEAM-0014,
  SEAM-0021), the Saturn object pending owner classification (SEAM-0020),
  and the v1.1.0 manifest.

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

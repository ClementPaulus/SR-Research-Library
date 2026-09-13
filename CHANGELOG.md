# Changelog

All notable changes to the Structura Reditus Research Library are documented
here. The library is versioned independently of GCD and of any other
Structura Reditus artifact. Previous releases are never silently rewritten.

## Unreleased

Unified the two implementation branches
(`copilot/build-initial-implementation` and
`copilot/create-structura-reditus-library`) and the uploaded
`SR-LIBRARY.v0.1.0-rc1` engine package into a single library.

### Added

- Full governing specification `docs/SR-RESEARCH-LIBRARY-SPEC.v0.1.md`,
  `ENGINE_CONTRACT.md`, and `docs/` (identifiers, receipts, main-branch
  protection ruleset) from the rc1 engine package; the package itself is
  preserved under `releases/archive/`.
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

# Changelog

All notable changes to the Structura Reditus Research Library are documented
here. The library is versioned independently of GCD and of any other
Structura Reditus artifact. Previous releases are never silently rewritten.

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

# Structura Reditus Research Library

The Structura Reditus Research Library is an independent repository-level Tier-0 organizational protocol and registry surface for Tier-2 research objects.

It is intentionally separate from GCD v2.3.3 and historical GCD releases.

## Architecture summary

Governing flow:

`IDENTIFY -> REGISTER -> CLASSIFY -> RELATE -> VALIDATE RECORD -> ACCEPT / RETURN FOR REPAIR / REJECT -> RETRIEVE`

Source of truth:
- `registry/` (authors, objects, sources, relations)
- `receipts/` (admission outcomes)
- `taxonomy/` and `schema/` (controlled structure)

Generated/public view:
- `site/` (public-library projection and route guidance)

Validation surface:
- `validators/` (schema, ID, taxonomy, relation, and release validation)
- `tests/` (targeted validator tests)

## Active versions

- Schema version: `SR-SCHEMA.v0.1.0`
- Taxonomy version: `SR-TAXONOMY.v0.1.0`
- Library pre-release manifest: `releases/SR-LIBRARY.v0.1.0-pre.manifest.yaml`

## Quickstart

```bash
python3 validators/run_validators.py
python3 -m unittest discover -s tests -v
```

## Required initial author

- AuthorID: `AUTH-0001`
- Display name: `Clement Paulus`
- ORCID: `0009-0000-6069-8234`
- Status: `active`

Registered at: `registry/authors/AUTH-0001.yaml`.

## Adding a new author

1. Create `registry/authors/AUTH-XXXX.yaml` using `schema/author.schema.json`.
2. Use the next stable ID (`AUTH-` + 4 digits).
3. Include identity, verification states, timestamps, and status.
4. Run validators and tests.
5. Commit and produce/update a release manifest and receipt references as needed.

## Submitting a new Tier-2 object

1. Prepare submission package in `fixtures/submissions/` or your ingestion path:
   - object record
   - author records if new
   - source records if new
   - relation records if claimed
   - full text or stable source reference
   - version and publication state
2. Ensure one primary Tier-2 class, domain, structural focus, and evidence mode.
3. Declare authority boundary, missingness, distortion/substitution risk, and next burden.
4. Run validators.
5. Issue a receipt in one of:
   - `receipts/accepted/`
   - `receipts/repair/`
   - `receipts/rejected/`

## Receipt examples

- ACCEPTED: `receipts/accepted/EXAMPLE-ACCEPTED.yaml`
- RETURNED_FOR_REPAIR: `receipts/repair/EXAMPLE-RETURNED_FOR_REPAIR.yaml`
- REJECTED: `receipts/rejected/EXAMPLE-REJECTED.yaml`

## Unresolved seams / decisions

Current open seams are tracked in `releases/open-seams.yaml`.

## Confirmation

This repository does not modify GCD v2.3.3 or any historical GCD release.

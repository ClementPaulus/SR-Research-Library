# Structura Reditus Research Library

**SR-LIBRARY.v0.1.0 (pre-release)** · Schema SR-SCHEMA.v0.1.0 · Taxonomy SR-TAXONOMY.v0.2.0

Governing flow:

```
IDENTIFY -> REGISTER -> CLASSIFY -> RELATE -> VALIDATE RECORD
         -> ACCEPT / RETURN FOR REPAIR / REJECT -> RETRIEVE
```

## What the Research Library is

The Structura Reditus Research Library is a **Tier-0 organizational and
retrieval system** for registering, classifying, relating, validating,
historizing, and retrieving **Tier-2 research works** within the Structura
Reditus field.

It gives every research record a stable identity, a controlled
classification, explicit boundaries, preserved history, and a documented
admission decision — so that independent researchers and groups can work in
their own domains while their research remains structurally searchable and
comparable across Structura Reditus.

## What it is not

- It does **not** determine how research is performed.
- It does **not** decide whether a scientific claim is true.
- It is **not** a new authority tier, theory, functional system, or
  replacement for Structura Reditus.
- It is **not** a prestige hierarchy: there is no author score, no ranking,
  and no weighting of credentials, citations, or affiliation.
- Library admission means **only** that a record satisfies the library's
  organizational contract. It does not imply scientific truth, endorsement,
  Tier-0 adoption, or Tier-1 admission.

## Hierarchy and Tier-2 placement

- **Reditus** = the object: admissible return through collapse under declared
  conditions.
- **Structura Reditus** = the field.
- **Generative Collapse Dynamics (GCD)** = foundational theory.
- **Tier-1 / Tier-0 / Tier-2** = authority architecture.
- **UMCP / RCFT / ULRC** = functional systems.
- **Tier-2** = Translation and Expansion Authority.
- **The Research Library** = Tier-0 organizational infrastructure for Tier-2
  research records.

This repository is independent and does not contain or modify GCD v2.3.3 or
any historical GCD release.

## Identifier system

| Entity          | Namespace       | Example         |
|-----------------|-----------------|-----------------|
| Author          | `AUTH-NNNN`     | `AUTH-0001`     |
| Research object | `SR-OBJ-NNNNNN` | `SR-OBJ-000001` |
| Source          | `SRC-NNNNNN`    | `SRC-000001`    |
| Relation        | `REL-NNNNNN`    | `REL-000001`    |
| Receipt         | `RCPT-NNNNNN`   | `RCPT-000001`   |

## Repository layout

```
schema/       JSON Schemas for authors, objects, sources, relations, receipts
taxonomy/     Controlled taxonomies for all main classification axes
              (+ extensions.yaml: record of every term proposal and outcome)
registry/     THE SOURCE OF TRUTH: authors, objects (+history), sources, relations
receipts/     Admission receipts: accepted/, repair/, rejected/
validators/   Validation, admission gates, receipts, profiles, manifests, site
tests/        Test suite (pytest)
releases/     Release manifests (manifests/) and open-seams.yaml
site/         Public library surface, generated from the registry
examples/     Synthetic example submissions and receipts (explicitly synthetic)
```

## Submission process

1. Register (or already have) an `AUTH-NNNN` author record.
2. Register any external sources as `SRC-NNNNNN` source records.
3. Declare any relations as `REL-NNNNNN` relation records.
4. Prepare the research-object record against `schema/object.schema.json`,
   using controlled taxonomy values for every classification axis.
5. Run the validators locally: `python -m validators.validate`.
6. Evaluate admission: `python -m validators.admit path/to/object.json`.
   Add `--write` to store the receipt and `--register` to place an ACCEPTED
   record into `registry/objects/` (prior versions are archived, never
   overwritten).
7. Submit the record (pull request adding files under `registry/` and
   `receipts/`).

Exact steps are in [CONTRIBUTING.md](CONTRIBUTING.md). The full contract is
in [LIBRARY_SPECIFICATION.md](LIBRARY_SPECIFICATION.md).

## Admission outcomes

Seven gates are evaluated — A: Identity, B: Tier placement, C: Source and
provenance, D: Classification, E: Boundary and missingness, F: Relation
integrity, G: Library durability. Outcomes are exactly:

- **ACCEPTED** — all gates pass; no evaluability-blocking missingness remains.
- **RETURNED_FOR_REPAIR** — required structure is missing or incomplete; the
  same object can return through the declared repair. This is **not** a
  rejection.
- **REJECTED** — an evaluable gate fails because the record violates the
  library contract. Rejection concerns library admission only; it does not
  establish that the underlying research claim is false.

Work is never rejected for disagreeing with GCD, being controversial, coming
from an external author, being unconventional, having a negative result,
reporting non-return, or challenging another Tier-2 work. Every author —
including AUTH-0001 — is held to the same gates; there are no founder
exceptions.

## Repair receipts

Every decision produces a human-readable and machine-readable receipt. A
`RETURNED_FOR_REPAIR` receipt lists the blocked gates, the exact missing
structure, the missingness class, the exact repair required, which fields are
already accepted, which are still blocked, and the exact resubmission
condition — so repair never requires live explanation from a maintainer.

## External-source policy

External work stays an external **source object**. Library records may cite,
compare, translate, map, or build a local Tier-2 closure around an external
source, but they must preserve original authorship, source-native claims,
source identity, the distinction between source observation and local
interpretation, missingness, and an explicit authority boundary. A Structura
Reditus or GCD interpretation is never attributed to an external author
unless the source actually makes that interpretation.

## Author profiles

Profiles are computed from the registry only and contain only reconstructible
quantities: total registered authored objects and normalized distributions
over primary domain, Tier-2 class, structural focus, evidence mode,
provenance, and maturity. There is no universal author score. Credentials may
appear as provenance metadata with a verification state.

## Cross-domain search

The generated site supports browsing/filtering by author, domain, subdomain,
object of study, structural focus, main question, Tier-2 class, evidence
mode, provenance, maturity, relation, source, and date. Cross-domain
retrieval follows:

```
FIND -> COMPARE -> EXTRACT TRANSFERABLE STRUCTURE
     -> REINSTANTIATE LOCALLY -> VALIDATE LOCALLY
```

Thresholds, adapters, closure gates, evidence standards, causal claims,
ontological claims, and source authority are never transferred automatically.

## Versioning

The library is versioned independently (currently `SR-LIBRARY.v0.1.0`,
pre-release). Every release records schema/taxonomy versions, entity counts,
the full ID manifest, date/timezone, open seams, migration notes, and file
hashes. Previous releases and historical object states are never silently
rewritten.

## Proposing taxonomy additions

Controlled taxonomies live in `taxonomy/*.yaml`. To propose a term, record
the proposal in `taxonomy/extensions.yaml` (term, definition, why existing
terms are insufficient, nearest terms, examples, ambiguity risk,
backward-compatibility effect), then open a pull request that adds the term
(id, label, optional description) to the relevant taxonomy file and bumps
`taxonomy/VERSION`. Existing terms are never silently
removed or redefined; superseded terms are deprecated in place. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## Open seams

Unresolved contract decisions are tracked in `releases/open-seams.yaml` and
copied into each release manifest. Seams are closed in place, never deleted.

## Running locally

Requires Python 3.10+ with `jsonschema` and `pyyaml` (and `pytest` for
tests):

```
pip install jsonschema pyyaml pytest
python -m validators.validate          # validate the registry
python -m validators.admit FILE        # evaluate an admission (--write stores receipts, --register registers ACCEPTED records)
python -m validators.build_site        # regenerate site/ from the registry
python -m validators.release VERSION   # write a release manifest
python -m pytest tests/               # run the test suite
```

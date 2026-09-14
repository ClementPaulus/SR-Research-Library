# Structura Reditus Research Library

**SR-LIBRARY.v1.0.0** · Schema SR-SCHEMA.v0.4.0 · Taxonomy SR-TAXONOMY.v0.2.0

**[Browse research](site/search.html)** · **Create your profile** · **Log in** · **Upload research** —
the researcher portal (`portal/`) gives every contributor a persistent account, an automatically
assigned public AuthorID, guided uploads, source-grounded record preparation, the existing admission
engine, receipts, repair, and registration in this repository — with no GitHub account, terminal, or
JSON editing. Signed-in researchers land in their workspace. See
[docs/PORTAL_CONTRIBUTING.md](docs/PORTAL_CONTRIBUTING.md) (researcher guide and direct route),
[docs/PORTAL_IMPLEMENTATION.md](docs/PORTAL_IMPLEMENTATION.md), [docs/PORTAL_OPERATIONS.md](docs/PORTAL_OPERATIONS.md),
and [docs/PORTAL_ACCEPTANCE.md](docs/PORTAL_ACCEPTANCE.md) for what is verified and what still needs owner provisioning.

Governing flow:

```
IDENTIFY -> REGISTER -> CLASSIFY -> RELATE -> VALIDATE RECORD
         -> ACCEPT / RETURN FOR REPAIR / REJECT -> RETRIEVE
```

## Three registries, one library

| Surface | Identity | What it preserves |
|---|---|---|
| **Governing References** | `SR-GOV-*` | canon-facing, constitutional, authority-axis, functional-source, kernel-reference, protocol, specification, publication-protocol, ingress, and language-contact references with their **exact admitted burden** (`authority_scope.tier_1` / `tier_0`). Immutable once released; superseded, never rewritten. Not research objects. |
| **Tier-2 Research** | `SR-OBJ-*` | the living research body: domain, focus, question, evidence, provenance, maturity, missingness, authority boundary, next burden, admission receipt. May list `governing_refs` that constrain it without transferring authority. |
| **Sources & Archives** | `SRC-*` | where a work actually lives: DOI, archive, publisher, data, code, labeled outbound `links`. The paper stays on its DOI/archive platform; the library never mirrors it. |

A work may hold any combination of these identities. *Summa Reditus* has an
`SRC-*` and an `SR-GOV-*` record and no `SR-OBJ-*`; a domain paper has an
`SRC-*` and an `SR-OBJ-*` and no `SR-GOV-*`. Relations use `REL-*`.

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
| Governing reference | `SR-GOV-NNNNNN` | `SR-GOV-000001` |
| Research object | `SR-OBJ-NNNNNN` | `SR-OBJ-000001` |
| Source          | `SRC-NNNNNN`    | `SRC-000001`    |
| Relation        | `REL-NNNNNN`    | `REL-000001`    |
| Receipt         | `RCPT-NNNNNN`   | `RCPT-000001`   |

A DOI identifies an external archival anchor; a SourceID identifies the named
work. One DOI may legitimately anchor several member works (a coordinated
release, a multi-part series); such works keep separate SourceIDs and the
shared-archive condition is recorded in their notes. They are neither
collapsed into one object nor counted as separate DOI deposits. DOI identity
survives a broken web link; a link failure never deletes a source.

## Repository layout

```
schema/       JSON Schemas for authors, governing references, objects, sources, relations, receipts,
              plus infrastructure schemas (execution manifests, identifier reservations)
taxonomy/     Controlled taxonomies for all main classification axes
              (+ extensions.yaml: record of every term proposal and outcome)
registry/     THE SOURCE OF TRUTH: authors, governing (tier-1/ tier-0/ mixed/ views),
              objects (+history), sources, relations, reservations (identifier ledger)
receipts/     Admission receipts: accepted/, repair/, rejected/ (+ .submission.json snapshots),
              executions/ (companion execution manifests)
validators/   Validation, admission gates, receipts, allocation, execution manifests, search, profiles, site
portal/       Public researcher portal (Django): accounts, submissions, registry bridge, catalog, tests
tests/        Engine test suite (pytest); tests/fixtures/ holds immutable census snapshots
releases/     Release manifests (manifests/) and open-seams.yaml
site/         Public library surface, generated from the registry (incl. search.html + data/search_index.json)
examples/     Synthetic example submissions, receipts, and OBJECT_TEMPLATE.json
docs/         Governing specification, supporting rules, portal docs, portal-evidence/ (baseline hashes, browser run)
.github/      CI validation + portal workflow, PR template, issue forms
```

## Governing documents

- [docs/SR-RESEARCH-LIBRARY-SPEC.v0.1.md](docs/SR-RESEARCH-LIBRARY-SPEC.v0.1.md) —
  the full governing specification (registry, admission, indexing, repair,
  release).
- [LIBRARY_SPECIFICATION.md](LIBRARY_SPECIFICATION.md) — the implemented
  contract of this repository, section by section.
- [ENGINE_CONTRACT.md](ENGINE_CONTRACT.md) — what automated code may and may
  not decide.
- [docs/IDENTIFIERS.md](docs/IDENTIFIERS.md), [docs/RECEIPTS.md](docs/RECEIPTS.md),
  [docs/MAIN_PROTECTION_RULESET.md](docs/MAIN_PROTECTION_RULESET.md).
- [docs/TIER2_CENSUS_2026-09.md](docs/TIER2_CENSUS_2026-09.md) — readback of
  the 2026-09 Tier-2 census, repair, and ingress pass (registry state is the
  source of truth; the report is a readback).
- [CONTRIBUTING.md](CONTRIBUTING.md) — exact steps for adding authors,
  sources, relations, objects, and taxonomy terms.

## Submission process

**Portal route (primary).** Create your profile once → verify your email (an AuthorID is assigned
automatically) → *Upload research* → review the prepared record and answer the remaining questions →
*Submit this revision to the public research library* → read the receipt → repair if asked → find the
registered result. Full guide: [docs/PORTAL_CONTRIBUTING.md](docs/PORTAL_CONTRIBUTING.md).

**Direct repository route.** Both routes use the same schemas, taxonomies, engine, identifier
reservations, receipts, and preservation rules.

1. Register (or already have) an `AUTH-NNNN` author record; reserve it with
   `python -m validators.reserve AUTH --purpose "author registration"`.
2. Search for duplicate work, then reserve `SR-OBJ`/`SRC`/`REL` identifiers the same way.
3. Register any external sources as `SRC-NNNNNN` source records and relations as `REL-NNNNNN`.
4. Prepare the research-object record against `schema/object.schema.json`,
   using controlled taxonomy values for every classification axis.
5. Evaluate admission: `python -m validators.admit path/to/object.json --write`
   stores the receipt, the exact submission snapshot, and the execution manifest;
   add `--register` to place an ACCEPTED record into `registry/objects/` (prior
   versions are archived, never overwritten; the reservation is marked published).
6. Run the validators: `python -m validators.validate`; regenerate the projection:
   `python -m validators.build_site`.
7. Submit the record (pull request adding files under `registry/`, `receipts/`, and `site/`).

Exact steps are in [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/PORTAL_CONTRIBUTING.md](docs/PORTAL_CONTRIBUTING.md).
The full contract is in [LIBRARY_SPECIFICATION.md](LIBRARY_SPECIFICATION.md).

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

The portal (`/research`) and the generated site (`site/search.html`, `site/data/search_index.json`)
share one index and one set of matching rules: every unquoted term must match somewhere in a record's
public fields (title, all questions, object of study, classifications, authors, sources and DOIs,
relations, missingness, next burden); `"quoted text"` is a phrase; identifiers and DOIs match exactly;
filters combine by AND across axes and OR within an axis (primary or secondary values); ranking is
retrieval relevance only. Browse/filter by author, domain, subdomain, object of study, structural focus,
main question, Tier-2 class, evidence mode, provenance, maturity, relation, source, and date.
Cross-domain retrieval follows:

```
FIND -> COMPARE -> EXTRACT TRANSFERABLE STRUCTURE
     -> REINSTANTIATE LOCALLY -> VALIDATE LOCALLY
```

Thresholds, adapters, closure gates, evidence standards, causal claims,
ontological claims, and source authority are never transferred automatically.

## Versioning

The library is versioned independently (currently `SR-LIBRARY.v1.0.0`, the
first release; `v0.1.0` and `v0.2.0` were pre-releases). Every release records
schema/taxonomy versions, entity counts,
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
pip install -r requirements-dev.txt
python -m validators.validate          # validate the registry
python -m validators.admit FILE        # evaluate an admission (--write stores receipt + snapshot + execution manifest, --register registers ACCEPTED records)
python -m validators.reserve NS ...    # reserve an identifier through the shared ledger (AUTH, SR-OBJ, SRC, REL, RCPT, SR-GOV)
python -m validators.build_site        # regenerate site/ from the registry
python -m validators.release VERSION   # write a release manifest (--final for a non-pre-release)
python -m pytest tests/               # run the engine test suite
```

Researcher portal (Python 3.12; see [docs/PORTAL_OPERATIONS.md](docs/PORTAL_OPERATIONS.md)):

```
docker compose -f portal/compose.yaml up --build   # web :8000, worker, PostgreSQL, Redis, MinIO, Mailpit :8025
make -C portal venv test                            # hashed-lock install and the portal test suite
```

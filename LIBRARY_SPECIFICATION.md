# Structura Reditus Research Library Specification

This file captures the governing implementation specification for the independent Structura Reditus Research Library.

## 1) Governing placement

- Reditus is the object.
- Structura Reditus is the field.
- GCD is foundational theory.
- Tier-1, Tier-0, Tier-2 remain authority roles.
- UMCP, RCFT, ULRC remain functional systems.
- Summa Reditus / Architecture Freeze v1.0 remains canon-facing treatise.
- This library is a Tier-0 organizational protocol and registry surface for Tier-2 objects.

Compression:

`IDENTIFY -> REGISTER -> CLASSIFY -> RELATE -> VALIDATE RECORD -> ACCEPT / RETURN FOR REPAIR / REJECT -> RETRIEVE`

Admission indicates organizational conformance only.

## 2) Tier-2 meaning

Tier-2 is Translation and Expansion Authority with explicit authority limits and no implicit promotion.

Primary classes (exactly one required):
1. domain-translation material
2. diagnostic material
3. language-contact material
4. pedagogical material
5. candidate material
6. external-ingress material
7. handoff material

Every object declares role, authority limit, preserved meaning/source, risk, and next burden.

## 3) Repository structure

Required structure is implemented in this repository with:
- top-level governance docs
- `schema/`, `taxonomy/`, `registry/`, `receipts/`, `validators/`, `releases/`, `site/`, `tests/`

Registry is source of truth; site is generated/public projection.

## 4) Stable identifiers

- AuthorID: `AUTH-0001+`
- ObjectID: `SR-OBJ-000001+`
- SourceID: `SRC-000001+`
- RelationID: `REL-000001+`

IDs never encode prestige, rank, truth, or importance.

## 5) Author schema

Author records support identity, aliases, ORCID, entity type, affiliations, roles, domains, credential provenance, verification state, timestamps, status, and notes.

Credentials are provenance metadata only and never grant authority.

## 6) Research object schema

Object records include Tier-2 placement, classification, source references, domain/focus/questions, evidence/provenance/maturity, boundaries, missingness/risk, next burden, versioning, and notes.

Objects are inadmissible if reconstructibility requirements are not met without live author mediation.

## 7) Controlled taxonomies

Primary classification axes must use controlled values for domain, Tier-2 class, structural focus, evidence mode, provenance, maturity, relation, publication state, and functional locus.

Taxonomy extensions follow the explicit proposal process in `CONTRIBUTING.md` and `taxonomy/extensions.yaml`.

## 8) Primary domain

Exactly one primary domain required; optional secondary domains permitted.

## 9) Structural focus

Exactly one primary structural focus required; optional secondary focuses permitted.

## 10) Main question

One complete, bounded, neutral primary question required.

## 11) Evidence mode

Exactly one primary evidence mode required, with optional secondary modes.

## 12) Provenance

Exactly one provenance type required, with claim-layer separation for externally anchored work.

## 13) Maturity

Exactly one maturity state required; maturity is not authority rank.

## 14) Relations

Relations are explicit, typed, and directional as needed, and cannot imply stronger claims than evidence permits.

## 15) External-source discipline

External sources remain external; preserve source-native claims and attribution boundaries.

## 16) Author profiles

Profiles are generated from registered object metadata only. No universal author score.

## 17) Historical preservation

Append-preserving history for registrations, revisions, supersessions, relation/classification/taxonomy changes, and boundary/publication changes.

## 18) Cross-domain retrieval

Public retrieval supports author/domain/object/focus/question/class/evidence/provenance/maturity/relation/source/date.

Cross-domain transfer requires local reinstantiation and local validation.

## 19) Submission package

Submission includes object record, new author/source/relation records where applicable, text/source reference, version, and publication state.

## 20) Admission gates

Seven gates are enforced:
A Identity
B Tier placement
C Source/provenance
D Classification
E Boundary/missingness
F Relation integrity
G Library durability

## 21) Admission outcomes

Exactly three outcomes:
- ACCEPTED
- RETURNED_FOR_REPAIR
- REJECTED

RETURNED_FOR_REPAIR is not REJECTED.

## 22) Missingness classes

At least:
- NON_BLOCKING
- EVALUABILITY_BLOCKING
- CONTRACT_VIOLATING
- AUTHORITY_BOUNDARY
- SOURCE_BOUNDARY
- PUBLICATION_BOUNDARY
- REPAIRABLE
- UNRESOLVED_SEAM

## 23) Receipts

Every admission decision yields human-readable and machine-readable receipt content.

## 24) Review order

Review order is fixed:

Identity -> Object/version -> Tier placement -> Primary Tier-2 class -> Source/provenance -> Domain/object of study -> Structural focus -> Main question -> Evidence mode -> Maturity -> Scope/exclusions -> Authority boundary -> Missingness -> Relations -> Next burden -> Durability -> Admission decision -> Receipt

## 25) Formal admission logic

- ACCEPTED iff all active gates pass and no evaluability-blocking missingness remains.
- RETURNED_FOR_REPAIR iff structure is missing and repair possible without falsified provenance.
- REJECTED iff evaluable gate failure violates active contract.

## 26) Neutrality rule

No privilege for founder identity, credentials, prestige, popularity, venue, chronology, or GCD agreement.

## 27) Validators

Automated validators include schema validity, ID uniqueness/references, taxonomy terms, required fields, format checks, collisions, and relation integrity. They do not decide truth/novelty/importance/sufficiency.

## 28) Human review

Human review checks provenance honesty, placement/classification consistency, claim/evidence separation, authority boundaries, missingness, relation wording, and repairability.

## 29) Public site

Public routes and object/author pages are generated from registry data. No universal author score.

## 30) Release discipline

Independent library versioning, frozen manifests/snapshots, append-preserving history, and explicit open seams/migration notes.

## 31) First implementation sequence

Implemented sequence:
1. Separate repository scaffold.
2. This specification.
3. Schemas + taxonomies.
4. Seed `AUTH-0001` only from supplied facts.
5. Build validators + tests before bulk object registration.
6. Receipts and release pre-manifest.

## 32) Foundational library laws

Implemented as repository constraints:
- Identity before aggregation
- Provenance before comparison
- Classification before retrieval
- Relation before transfer
- Missingness before rejection
- Admission is not endorsement
- Author identity is not authority
- History is append-preserving
- Tier-2 remains Tier-2
- The object comes first

## 33) Completion condition

For a release, every admitted object must be identifiable, classifiable, source-preserving, relationally legible, versioned, receipted, and retrievable.

## 34) Required implementation outputs

Repository includes:
- architecture summary (`README.md`)
- final tree (derivable from repository)
- active schema/taxonomy versions (manifest + README)
- initial author record (`registry/authors/AUTH-0001.yaml`)
- validators/tests
- pre-release manifest (`releases/SR-LIBRARY.v0.1.0-pre.manifest.yaml`)
- unresolved seams (`releases/open-seams.yaml`)
- instructions for adding author and submitting Tier-2 work (`README.md`)
- example receipts (`receipts/`)
- explicit non-modification statement for GCD v2.3.3/history (`README.md`)

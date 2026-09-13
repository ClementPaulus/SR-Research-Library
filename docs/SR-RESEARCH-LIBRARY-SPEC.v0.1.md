# Structura Reditus Research Library
## Registry, Admission, Indexing, Repair, and Release Specification

**Specification ID:** `SR-RESEARCH-LIBRARY-SPEC.v0.1`  
**Status:** Tier-0 organizational protocol candidate; not Tier-1 canon and not a publication verdict engine  
**Prepared:** 2026-09-12, America/Chicago  
**Primary burden:** Govern how Tier-2 research objects are identified, registered, classified, related, retrieved, repaired, accepted into the library, and versioned without changing their local authority or evidentiary burden.  
**Field placement:** Structura Reditus is the field; Reditus is the object; GCD is the foundational theory; Tier-2 is the translation and expansion authority under which most library research objects are registered.  
**Boundary:** Library admission means organizational conformance only. It does not prove a scientific, mathematical, philosophical, historical, pedagogical, or domain-native claim; it does not grant Tier-1 or Tier-0 authority; and it does not imply endorsement of an author, theory, institution, or conclusion.

---

# 0. Governing doctrine

The Structura Reditus Research Library is an organizational memory and retrieval surface.

Its work is:

```text
IDENTIFY -> REGISTER -> CLASSIFY -> RELATE -> VALIDATE RECORD -> ACCEPT / RETURN / REJECT -> RETRIEVE
```

Its work is not:

```text
DECIDE TRUTH
RANK AUTHORS
WEIGHT PRESTIGE
PROMOTE TIER-2 TO TIER-1
PROMOTE TIER-2 TO TIER-0
REPLACE DOMAIN EVIDENCE STANDARDS
REASSIGN AUTHORSHIP
TURN ANALOGY INTO CLOSURE
TURN LIBRARY PRESENCE INTO ENDORSEMENT
```

The library preserves a strict distinction among:

1. the research object;
2. the source object;
3. the author or authors;
4. the Structura Reditus record;
5. the authority status of the object;
6. the evidentiary status of the claims;
7. the library admission decision.

A work may be admitted to the library while remaining disputed, exploratory, externally authored, non-GCD, non-UMCP, or nonconformant under a separate scientific or evaluative burden, provided its library record accurately declares those conditions.

---

# 1. Canonical placement

The library SHALL preserve the mature order:

```text
Reditus -> Structura Reditus -> GCD
```

and SHALL preserve the two orthogonal architectures:

```text
Authority axis:
Tier-1 -> Tier-0 -> Tier-2

Functional axis:
UMCP -> RCFT -> ULRC
```

The library SHALL NOT treat UMCP, RCFT, or ULRC as authority tiers.

The library SHALL NOT treat Tier-1, Tier-0, or Tier-2 as functional systems.

The library SHALL treat Tier-2 as the principal authority class for registered research translations, diagnostics, domain closures, external-ingress objects, candidate structures, pedagogical objects, language-contact objects, and handoff objects.

---

# 2. Tier-2 library meaning

For library purposes, Tier-2 SHALL mean:

> Translation and expansion authority: the conditional authority under which domains, readers, datasets, diagnostics, translations, public surfaces, pedagogical objects, candidate extensions, external sources, and applied research works become legible without redefining Tier-1 or acquiring Tier-0 protocol authority by implication.

Every Tier-2 record SHALL state:

- its role;
- its authority limit;
- the meaning, source, or structure it preserves;
- the missingness, distortion, or substitution risk it carries;
- the next burden required before any stronger operational or canonical claim.

The library SHALL recognize the following seven primary Tier-2 classes:

1. **Domain-translation material**
2. **Diagnostic material**
3. **Language-contact material**
4. **Pedagogical material**
5. **Candidate material**
6. **External-ingress material**
7. **Handoff material**

Each registered Tier-2 object SHALL have exactly one primary class.

Secondary classes MAY be declared where useful, but secondary classification SHALL NOT obscure the primary burden.

---

# 3. Registry objects and identifiers

The library SHALL maintain four minimum identifier namespaces.

## 3.1 Author identity

Format:

```text
AUTH-0001
AUTH-0002
AUTH-0003
...
```

An `AuthorID` identifies a stable author entity.

The AuthorID SHALL remain invariant across:

- new publications;
- revisions;
- domain changes;
- affiliation changes;
- credential changes;
- role changes;
- library releases.

An AuthorID SHALL NOT encode prestige, seniority, institutional rank, or authority.

### Initial frozen author identity

```text
AuthorID: AUTH-0001
Display name: Clement Paulus
ORCID: 0009-0000-6069-8234
Status: active
```

## 3.2 Research object identity

Format:

```text
SR-OBJ-000001
SR-OBJ-000002
...
```

One distinct registered research object SHALL receive one stable `ObjectID`.

A new edition or revision SHALL normally retain the same ObjectID and receive a new version state unless the object, contract, authority role, or publication role has materially changed.

A materially changed object SHALL receive a new ObjectID or a declared seam from the predecessor.

## 3.3 Source identity

Format:

```text
SRC-000001
SRC-000002
...
```

A `SourceID` identifies the source object from which a library object may derive evidence, comparison, translation, external ingress, or lineage.

Examples include:

- paper;
- dataset;
- repository;
- book;
- technical report;
- historical source;
- external theory document;
- experiment;
- code archive.

A source object SHALL retain its original authorship and source-native meaning.

## 3.4 Relation identity

Format:

```text
REL-000001
REL-000002
...
```

A `RelationID` identifies a declared relation between two or more registered objects or sources.

Allowed relation types SHALL come from a controlled relation taxonomy.

---

# 4. Required author record

Every AuthorID SHALL have a minimum author record containing:

```yaml
author_id:
display_name:
alternate_names: []
orcid:
entity_type: person | group | institution | historical | anonymous | other
affiliations: []
declared_roles: []
declared_domains: []
credential_records: []
verification_state:
  identity:
  orcid:
  affiliation:
  credentials:
created_at:
updated_at:
status: active | inactive | historical | unresolved
notes:
```

## 4.1 Credential rule

Credentials MAY be displayed for provenance and reader orientation.

Credentials SHALL NOT:

- increase Tier authority;
- increase evidence weight automatically;
- determine admission;
- determine rank;
- determine truth;
- substitute for source evidence.

Credential fields SHALL carry a verification state such as:

```text
source-verified
ORCID-verified
institutionally-stated
author-declared
unverified
unresolved
```

---

# 5. Required research object record

Every candidate library object SHALL provide:

```yaml
object_id:
title:
authors:
  - author_id:
    contribution_role:
    contribution_share: optional
authority:
  tier: 2
tier2_class:
  primary:
  secondary: []
functional_locus:
  primary: UMCP | RCFT | ULRC | cross-functional | none-declared
  secondary: []
source_ids: []
lens:
  primary:
  secondary: []
domain:
  primary:
  secondary: []
object_of_study:
structural_focus:
  primary:
  secondary: []
main_question:
secondary_questions: []
claim_layers: []
evidence_mode:
  primary:
  secondary: []
provenance:
maturity:
relations: []
version:
date:
publication_state:
source_boundary:
authority_boundary:
scope:
exclusions:
preserved_meaning:
missingness:
distortion_or_substitution_risk:
next_burden:
repair_route:
notes:
```

No object SHALL be admitted without a recoverable answer to:

```text
Who produced it?
What is the object?
What source or sources govern it?
What domain does it inhabit?
What is its structural focus?
What question does it ask?
What Tier-2 role does it perform?
What evidence does it carry?
What authority does it not have?
What remains unresolved?
What is the next burden?
```

---

# 6. Controlled classification axes

The library SHALL maintain controlled taxonomies rather than unrestricted free-text categories for the following:

1. primary domain;
2. Tier-2 class;
3. structural focus;
4. evidence mode;
5. provenance type;
6. maturity state;
7. relation type;
8. publication state.

Free-text notes MAY supplement these fields but SHALL NOT replace controlled classification.

New taxonomy terms SHALL enter only through a declared taxonomy-extension record.

A taxonomy extension SHALL state:

```text
Term proposed:
Taxonomy:
Definition:
Reason existing term is insufficient:
Nearest existing terms:
Examples:
Ambiguity risk:
Backward-compatibility effect:
Decision:
Version introduced:
```

---

# 7. Primary domain rule

Every object SHALL declare exactly one primary domain.

Secondary domains MAY be listed.

The primary domain SHALL answer:

> In what established or declared field is the object principally situated?

The library SHALL NOT assign numerical domain weights by default.

Cross-domain objects SHALL retain one declared primary domain plus secondary domains unless a future adopted schema explicitly authorizes another representation.

---

# 8. Structural focus rule

Every object SHALL declare exactly one primary structural focus.

The focus SHALL answer:

> What structural problem or behavior is this work principally concerned with?

Examples MAY include:

```text
return
identity
continuity
recovery
compression
heterogeneity
translation
failure
causation
recurrence
memory
robustness
residual migration
boundary
missingness
adaptation
```

Secondary focuses MAY be declared.

Structural focus SHALL be the principal cross-domain retrieval axis.

---

# 9. Main-question rule

Every object SHALL contain one primary research question in ordinary language.

The question SHALL be:

- grammatically complete;
- specific enough to distinguish the object from neighboring work;
- neutral with respect to the desired answer;
- bounded by the declared scope;
- answerable or explicitly marked as open.

A question SHALL NOT be accepted if it merely restates a conclusion.

Example of acceptable form:

> Under what declared conditions can an identifiable target be recovered after perturbation?

Example of unacceptable form:

> Why does GCD prove identifiable recovery?

---

# 10. Evidence-mode rule

Every object SHALL declare one primary evidence mode.

Controlled evidence modes MAY include:

```text
formal proof
formal derivation
experimental
primary empirical
secondary empirical
retrospective analysis
prospective protocol
simulation
computational reproduction
source synthesis
conceptual argument
phenomenological
historical
pedagogical
translation-only
no empirical validation
```

Secondary evidence modes MAY be declared.

Evidence mode SHALL describe what the object actually carries, not what it hopes to establish later.

---

# 11. Provenance rule

Every object SHALL declare one provenance type.

Minimum provenance types:

```text
corpus-native
externally-anchored derivative
external source-native
collaborative
historical-source anchored
dataset-derived
translation-derived
synthetic test object
```

For externally anchored work, the record SHALL distinguish:

```text
SOURCE OBSERVATION
DERIVED MATHEMATICS
STRUCTURA REDITUS / GCD MAPPING
MECHANISM HYPOTHESIS
GENERALIZATION
ONTOLOGICAL CLAIM
OPEN BURDEN
```

The library SHALL reject any record that attributes a Structura Reditus interpretation to an external author who did not make it.

---

# 12. Maturity rule

Every object SHALL declare a current maturity state.

Minimum states:

```text
exploratory
candidate
articulated
source-bounded
frozen local object
retrospectively evaluated
prospectively testable
prospectively tested
reproduced
contradicted
unresolved
superseded
historical
```

Maturity SHALL NOT be treated as authority rank.

A mature Tier-2 work remains Tier-2 unless a separate authorized adoption or admission path succeeds.

---

# 13. Relation rule

Relations SHALL be explicit, typed, and directional where appropriate.

Allowed examples:

```text
supports
contrasts_with
extends
reproduces
challenges
translates
maps_to
shares_focus_with
shares_question_with
derived_from
source_of
supersedes
historical_predecessor_of
candidate_for
handoff_to
incompatible_under_current_contract
unresolved_relation
```

A relation SHALL NOT imply causation, proof, identity, or validation unless the relation type explicitly states that burden and the source record supports it.

---

# 14. External-source rule

External work SHALL remain external.

The library MAY create a source-preserving Tier-2 record around external work.

The record SHALL:

1. identify the external source;
2. preserve original authorship;
3. preserve source-native claims;
4. declare the local analytic lens;
5. distinguish source observation from local mapping;
6. declare evidence limitations;
7. state any unacquired or unavailable material;
8. state what the local record does not attribute to the source;
9. state the next burden.

External authors SHALL NOT be described as members of Structura Reditus merely because their work is indexed.

---

# 15. Author profile generation

Author profiles SHALL be generated from registered objects rather than manually ranking the author.

For author `a` at time `t`:

```text
P_a(t) = { O_j in L_T2 : a is an author of O_j and object date <= t }
```

Minimum quantifiable author state:

```text
A_a(t) = [
  N_a(t),
  D_a(t),
  R_a(t),
  F_a(t),
  E_a(t),
  P_a(t),
  M_a(t)
]
```

where:

```text
N = number of registered authored objects
D = normalized domain distribution
R = normalized Tier-2 role distribution
F = normalized structural-focus distribution
E = normalized evidence-mode distribution
P = normalized provenance distribution
M = normalized maturity distribution
```

For any categorical axis `X`:

```text
c_(a,k)^(X) = count of authored objects in category k

p_(a,k)^(X) = c_(a,k)^(X) / N_a

sum_k p_(a,k)^(X) = 1
```

The minimum quantitative profile SHALL include only values deterministically reconstructible from registered object records.

The initial core SHALL NOT numerically score:

- prestige;
- institutional status;
- degree level;
- citations;
- originality;
- quality;
- importance;
- universal relevance;
- author rank;
- conclusion strength.

---

# 16. Historical-state rule

The library SHALL preserve author and object histories.

A stable AuthorID SHALL permit reconstruction of:

```text
P_a(t0) -> P_a(t1) -> ... -> P_a(t)
```

The library SHALL preserve:

- first registration date;
- object additions;
- object revisions;
- supersessions;
- relation additions;
- classification changes;
- taxonomy-version changes;
- source-boundary changes;
- publication-state changes.

Historical states SHALL NOT be silently overwritten.

---

# 17. Cross-domain retrieval rule

The library SHALL permit retrieval by structure, not only by domain.

A comparative view MAY filter by any declared combination of:

```text
author
domain
object of study
structural focus
main question
Tier-2 class
evidence mode
provenance
maturity
relation
date
```

Cross-domain retrieval SHALL support the route:

```text
FIND
-> COMPARE
-> EXTRACT TRANSFERABLE STRUCTURE
-> REINSTANTIATE LOCALLY
-> VALIDATE LOCALLY
```

A cross-domain precedent SHALL NOT authorize direct import of:

- local thresholds;
- adapters;
- domain-specific evidence rules;
- closure gates;
- causal conclusions;
- ontological conclusions;
- source authority.

Transfer SHALL create a new local object or candidate where the receiving domain changes the governing contract.

---

# 18. Submission package

A work submitted for library admission SHALL include:

## 18.1 Minimum submission

```text
Object record
Author record(s), if new
Source record(s), if new
Relation record(s), if claimed
Full text or stable source link/reference
Version and publication state
```

## 18.2 Required declaration block

```text
Object:
ObjectID: [assigned or pending]
AuthorID(s):
Title:
Version:
Tier:
Primary Tier-2 class:
Functional locus:
Primary domain:
Object of study:
Primary structural focus:
Main question:
Primary evidence mode:
Provenance:
Maturity:
Source boundary:
Authority boundary:
Preserved meaning:
Missingness:
Distortion/substitution risk:
Next burden:
Repair route:
```

---

# 19. Admission gates

A work SHALL be accepted only when every active admission gate passes.

## Gate A - Identity

PASS requires:

- unique or correctly reused ObjectID;
- resolvable author identity;
- no duplicate object masquerading as new;
- declared version state;
- source identity where applicable.

FAIL examples:

- ambiguous authorship;
- duplicate object;
- fabricated identity;
- silent replacement of an existing object.

## Gate B - Tier placement

PASS requires:

- Tier-2 authority correctly declared;
- one primary Tier-2 class;
- no Tier-1 redefinition;
- no Tier-0 protocol claim without adoption;
- explicit authority limit.

FAIL examples:

- diagnostic presented as kernel identity;
- local closure presented as canon;
- candidate validator presented as adopted protocol.

## Gate C - Source and provenance

PASS requires:

- source set declared;
- external authorship preserved;
- source-native claims distinguishable from local interpretation;
- inaccessible or missing sources typed;
- provenance declared.

FAIL examples:

- unsupported attribution;
- source laundering;
- hidden external dependence;
- missing source that blocks the record.

## Gate D - Classification

PASS requires:

- primary domain;
- object of study;
- primary focus;
- main question;
- primary evidence mode;
- maturity;
- publication state.

FAIL examples:

- only vague keywords;
- question is actually a conclusion;
- maturity exceeds evidence;
- evidence mode misdescribed.

## Gate E - Boundary and missingness

PASS requires:

- scope;
- exclusions;
- preserved meaning;
- authority boundary;
- missingness;
- distortion/substitution risk;
- next burden.

FAIL examples:

- hidden missingness;
- unbounded generalization;
- replacement of the source by the local mapping;
- unknown next burden where stronger use is implied.

## Gate F - Relation integrity

PASS requires:

- every claimed relation is typed;
- relation target exists or is explicitly pending;
- relation does not imply stronger evidence than declared;
- causal, validation, or identity relations have sufficient support.

FAIL examples:

- "supports" used where only analogy exists;
- "reproduces" used without reproduction;
- "validates" used where only conceptual compatibility exists.

## Gate G - Library durability

PASS requires:

- another reader can recover the record without live author mediation;
- required fields are machine-readable;
- title and identifiers are stable;
- version lineage is recoverable;
- repair route is declared.

FAIL examples:

- essential meaning exists only in private explanation;
- classification cannot be reconstructed;
- no version identity;
- no repair path for a blocking gap.

---

# 20. Admission outcomes

The library SHALL derive one of three admission outcomes.

## 20.1 ACCEPTED

Use when:

- all active admission gates pass;
- no blocking missingness remains;
- the record is internally consistent;
- the object is assigned or retains a stable ObjectID.

Meaning:

> The work is admitted to the Structura Reditus Research Library under its declared Tier-2 role and metadata.

ACCEPTED does not mean:

- true;
- proven;
- endorsed;
- canonical;
- Tier-0 adopted;
- Tier-1 admitted.

## 20.2 RETURNED_FOR_REPAIR

Use when:

- required structure is missing;
- classification cannot yet be completed;
- a source or boundary gap blocks admission;
- the defect is repairable without falsifying provenance;
- the record can become admissible after declared completion.

This is the library analogue of evaluability-blocking missingness.

The object is not admitted as complete.

A repair receipt SHALL be issued.

## 20.3 REJECTED

Use only when an evaluable admission gate is violated in a way that is incompatible with library admission under the submitted object.

Examples:

- fabricated authorship or source;
- deliberate source misattribution;
- refusal to preserve external provenance;
- Tier-2 object presented as Tier-1 despite correction request;
- persistent hidden substitution;
- duplicate or fraudulent object identity;
- unrepaired authority overreach;
- record designed to misrepresent another author's work.

Where rejection is repairable only by materially changing the object, the receipt SHALL state that a new submission or declared seam is required.

---

# 21. Missingness classes for library admission

Every admission gap SHALL be typed.

```text
NON_BLOCKING
EVALUABILITY_BLOCKING
CONTRACT_VIOLATING
AUTHORITY_BOUNDARY
SOURCE_BOUNDARY
PUBLICATION_BOUNDARY
REPAIRABLE
UNRESOLVED_SEAM
```

Default effects:

| Missingness class | Library consequence |
|---|---|
| NON_BLOCKING | Record and continue |
| EVALUABILITY_BLOCKING | RETURNED_FOR_REPAIR |
| CONTRACT_VIOLATING | REJECTED when violation is established |
| AUTHORITY_BOUNDARY | Block affected classification or stronger claim |
| SOURCE_BOUNDARY | RETURNED_FOR_REPAIR or narrow the record |
| PUBLICATION_BOUNDARY | Block publication metadata claim only |
| REPAIRABLE | Issue explicit repair route |
| UNRESOLVED_SEAM | Preserve alternatives; do not force reconciliation |

---

# 22. Acceptance receipt

Every accepted work SHALL receive a machine-readable and human-readable receipt.

```text
STRUCTURA REDITUS RESEARCH LIBRARY
ADMISSION RECEIPT

Decision: ACCEPTED

ObjectID:
Title:
AuthorID(s):
Version:
Date:
Authority: Tier-2
Primary Tier-2 class:
Functional locus:
Primary domain:
Structural focus:
Main question:
Evidence mode:
Provenance:
Maturity:
Source IDs:
Relation IDs:
Publication state:

Admission gates:
A Identity: PASS
B Tier placement: PASS
C Source/provenance: PASS
D Classification: PASS
E Boundary/missingness: PASS
F Relation integrity: PASS
G Library durability: PASS

Non-blocking missingness:
Open burdens:
Next burden:

Meaning of decision:
Accepted into the Research Library as an organizationally conformant Tier-2 record.
No scientific, mathematical, philosophical, legal, institutional, or canonical endorsement is implied.
```

---

# 23. Repair receipt

Every work not yet acceptable because of incomplete but repairable structure SHALL receive:

```text
STRUCTURA REDITUS RESEARCH LIBRARY
REPAIR RECEIPT

Decision: RETURNED_FOR_REPAIR

Submission:
Provisional ObjectID:
AuthorID(s):
Version:

Failed or blocked gates:
[declare]

For each gap:

Missing structure:
Missingness class:
Affected field or burden:
Why it blocks admission:
Required repair:
Permitted evidence/source:
Does repair change the object? yes/no
Is a new ObjectID required? yes/no
Is a seam declaration required? yes/no

Fields already accepted:
[declare]

Fields not yet accepted:
[declare]

Resubmission condition:
[declare exact minimum required]

Current library state:
NOT ADMITTED AS COMPLETE

This receipt is not a judgment on the truth or value of the work.
It records only why the current submission does not yet satisfy library admission requirements.
```

---

# 24. Rejection receipt

Every rejected work SHALL receive:

```text
STRUCTURA REDITUS RESEARCH LIBRARY
REJECTION RECEIPT

Decision: REJECTED

Submission:
Object / provisional ObjectID:
AuthorID(s):
Version:

Failed admission gate(s):
[declare]

Established violation:
[declare]

Violation class:
CONTRACT_VIOLATING | AUTHORITY_BOUNDARY | SOURCE_BOUNDARY | IDENTITY | OTHER

Why admission is not permitted:
[declare]

Can the same object be repaired?
YES / NO

If YES:
Required repair:
New seam required:
New version required:
Resubmission allowed after:

If NO:
A materially new object is required because:
[declare]

Preserved record:
The rejected submission and receipt remain archived for audit unless legal, privacy, or safety obligations require otherwise.

This rejection concerns library admission only. It does not by itself establish that the underlying research claim is false.
```

---

# 25. Review sequence

Every submission SHALL be reviewed in this order:

```text
1. Identity
2. Object and version
3. Tier placement
4. Primary Tier-2 class
5. Source and provenance
6. Domain and object of study
7. Structural focus
8. Main question
9. Evidence mode
10. Maturity
11. Scope and exclusions
12. Authority boundary
13. Missingness
14. Relations
15. Next burden
16. Durability
17. Admission decision
18. Receipt
```

No admission decision SHALL be made before the required structure has been inspected.

---

# 26. Acceptance logic

Let:

```text
G = {G_A, G_B, G_C, G_D, G_E, G_F, G_G}
```

be the active admission gates.

Then:

```text
ACCEPTED
iff
all active gates PASS
and no evaluability-blocking missingness remains.
```

```text
RETURNED_FOR_REPAIR
iff
admission cannot be derived because required structure is missing
and the missing structure is repairable without falsifying provenance.
```

```text
REJECTED
iff
at least one evaluable admission gate FAILS
and the failure violates the active admission contract.
```

`RETURNED_FOR_REPAIR` SHALL NOT be collapsed into `REJECTED`.

`REJECTED` SHALL NOT be used merely because a work is controversial, unconventional, external, critical of GCD, or incompatible with another Tier-2 object.

Disagreement is not an admission failure.

---

# 27. Neutrality and non-competition rule

The library SHALL be an even Tier-2 comparison surface.

It SHALL NOT privilege a work because:

- the author created Structura Reditus;
- the author is academically credentialed;
- the author is highly cited;
- the author is institutionally affiliated;
- the work agrees with GCD;
- the work is popular;
- the work was published earlier;
- the work appears in a prestigious venue.

The library MAY display these facts as provenance metadata where verifiable.

The library SHALL organize by declared structural relation, not by prestige.

---

# 28. Independent-author rule

Each author profile SHALL remain independent.

The library MAY generate:

- author pages;
- domain views;
- focus views;
- question views;
- evidence views;
- relation networks;
- historical contribution maps;
- cross-domain comparison families.

An author profile SHALL be a projection of registered work, not a manually assigned reputation score.

---

# 29. Version and change control

The library SHALL version:

```text
schema
taxonomies
author registry
object registry
source registry
relation registry
public site
release manifest
```

Suggested version identity:

```text
SR-LIBRARY.v0.1.0
SR-LIBRARY.v0.2.0
SR-LIBRARY.v1.0.0
```

Each release SHALL freeze:

- schema version;
- taxonomy version;
- counts by registry type;
- manifest of IDs;
- file hashes where available;
- date and timezone;
- active open seams;
- migration notes.

No past release SHALL be silently rewritten.

---

# 30. Library file structure

Recommended repository structure:

```text
structura-reditus-research-library/
|
|-- README.md
|-- LIBRARY_SPECIFICATION.md
|-- CHANGELOG.md
|-- CONTRIBUTING.md
|
|-- schema/
|   |-- author.schema.json
|   |-- object.schema.json
|   |-- source.schema.json
|   `-- relation.schema.json
|
|-- taxonomy/
|   |-- domains.yaml
|   |-- focuses.yaml
|   |-- tier2_classes.yaml
|   |-- evidence_modes.yaml
|   |-- provenance_types.yaml
|   |-- maturity_states.yaml
|   |-- relation_types.yaml
|   `-- publication_states.yaml
|
|-- registry/
|   |-- authors/
|   |-- objects/
|   |-- sources/
|   `-- relations/
|
|-- receipts/
|   |-- accepted/
|   |-- repair/
|   `-- rejected/
|
|-- releases/
|   `-- manifests/
|
|-- validators/
|   |-- validate_schema
|   |-- validate_ids
|   |-- validate_taxonomy
|   |-- validate_relations
|   `-- validate_release
|
`-- site/
    `-- generated-public-library/
```

---

# 31. Validator requirements

Before admission, automated validators SHOULD check:

```text
schema validity
unique IDs
valid AuthorID references
valid SourceID references
valid RelationID references
controlled taxonomy terms
required fields
date format
version format
duplicate title/version collisions
broken relations
missing primary class
missing primary domain
missing structural focus
missing main question
missing evidence mode
missing authority boundary
missing next burden
```

Automated validation SHALL NOT decide:

- truth;
- novelty;
- scientific importance;
- evidentiary sufficiency for the domain-native claim;
- whether a theory is correct;
- whether an interpretation is philosophically persuasive.

Those remain local research burdens.

---

# 32. Human review requirements

Human review SHALL verify:

- authorship and provenance;
- source-boundary honesty;
- correct Tier-2 placement;
- reasonable primary classification;
- claim/evidence distinction;
- absence of silent authority promotion;
- external-source attribution;
- missingness declaration;
- relation wording;
- next-burden clarity;
- repairability.

Where reviewers disagree on a non-blocking classification, the disagreement MAY be preserved as an unresolved classification seam rather than forced.

---

# 33. Public-facing library behavior

The public site SHOULD permit browsing by:

```text
Author
Domain
Structural focus
Main question
Object of study
Tier-2 class
Evidence mode
Provenance
Maturity
Relation
Date
Source
```

Each public object page SHOULD show:

```text
title
authors
AuthorIDs
ObjectID
version
Tier-2 class
domain
focus
main question
evidence mode
provenance
maturity
source links
relations
authority boundary
missingness
next burden
publication state
admission receipt
```

Each author page SHOULD show:

```text
AuthorID
name
ORCID
affiliation
credential metadata
verification state
authored objects
represented external-source objects
domain distribution
focus distribution
Tier-2 class distribution
evidence-mode distribution
provenance distribution
maturity distribution
historical timeline
related comparison families
```

---

# 34. Release rule

A library release is eligible only when:

1. registry schemas validate;
2. all accepted records pass the active schema;
3. all AuthorIDs and ObjectIDs are unique;
4. all controlled taxonomy references resolve;
5. all relations resolve or are explicitly marked pending;
6. all accepted records possess receipts;
7. all repair and rejection receipts are archived;
8. the release manifest is generated;
9. version and date are frozen;
10. open seams are declared.

Release of the library SHALL NOT imply that every work in it is true, validated, conformant under UMCP, or endorsed by Structura Reditus.

---

# 35. First implementation sequence

The first implementation SHOULD proceed in this order:

```text
1. Freeze SR-RESEARCH-LIBRARY-SPEC.v0.1 as a Tier-0 candidate.
2. Freeze the initial controlled taxonomies.
3. Register AUTH-0001.
4. Assign ObjectIDs to Clement Paulus Tier-2 works.
5. Create SourceIDs for external works already used.
6. Create RelationIDs only where relations are explicit.
7. Run the admission gates against every candidate object.
8. Issue ACCEPTED, RETURNED_FOR_REPAIR, or REJECTED receipts.
9. Repair taxonomy defects exposed by real objects.
10. Freeze a first registry manifest.
11. Generate the public author, domain, focus, and object views.
12. Open external submission only after the internal corpus passes the same rules.
```

The founding author SHALL NOT receive relaxed admission criteria.

`AUTH-0001` SHALL be evaluated under the same library admission gates as every later author.

---

# 36. Foundational library laws

## Law 1 - Identity before aggregation

No author profile or contribution history may be computed before authors and objects have stable identities.

## Law 2 - Provenance before comparison

No external object may be compared before its source identity and source-native claims are preserved.

## Law 3 - Classification before retrieval

No object may populate a search family before its primary domain, focus, question, evidence, provenance, and Tier-2 role are declared.

## Law 4 - Relation before transfer

Cross-domain reuse requires a typed relation and a new local burden; structural similarity alone does not authorize direct adoption.

## Law 5 - Missingness before rejection

Incomplete structure must be typed before deciding whether the object is repairable, non-evaluable for admission, or contract-violating.

## Law 6 - Admission is not endorsement

Library acceptance proves only that the record satisfies the library's organizational contract.

## Law 7 - Author identity is not authority

AuthorID stabilizes provenance. It does not assign epistemic rank.

## Law 8 - History is append-preserving

Later revisions may supersede earlier states but may not silently erase them.

## Law 9 - Tier-2 remains Tier-2

Library usefulness, recurrence, citation, popularity, cross-domain relevance, or longevity do not promote an object to stronger authority.

## Law 10 - The object comes first

The library exists to make research objects legible and recoverable, not to make the library itself the object of research.

---

# 37. Compact admission checklist

A reviewer SHALL be able to answer YES to every active item before ACCEPTED:

```text
[ ] Author identity is resolvable.
[ ] Object identity is unique.
[ ] Version state is declared.
[ ] Tier-2 authority is correct.
[ ] Primary Tier-2 class is declared.
[ ] Functional locus is declared where relevant.
[ ] Primary domain is declared.
[ ] Object of study is explicit.
[ ] Primary structural focus is declared.
[ ] Main question is explicit and non-leading.
[ ] Evidence mode matches the actual object.
[ ] Provenance is declared.
[ ] External authorship is preserved.
[ ] Source boundary is explicit.
[ ] Authority boundary is explicit.
[ ] Scope and exclusions are explicit.
[ ] Preserved meaning is stated.
[ ] Missingness is typed.
[ ] Distortion/substitution risk is stated.
[ ] Maturity does not exceed evidence.
[ ] Relations are typed and supported.
[ ] Next burden is explicit.
[ ] Repair route exists where needed.
[ ] Record is understandable without live author mediation.
[ ] No Tier-1 redefinition occurs.
[ ] No Tier-0 authority is implied without adoption.
[ ] No library metadata is being used as proof.
```

---

# 38. Official admission compression

```text
ACCEPT
when the record is complete, bounded, source-preserving,
correctly Tier-2, structurally classifiable, and durable.

RETURN FOR REPAIR
when the record is incomplete but repairable.

REJECT
when an evaluable admission gate is violated
and the submitted object is incompatible with the library contract.
```

Every non-accepted submission receives a receipt stating:

```text
what is missing or violated
why it matters
what burden it blocks
what must be supplied or changed
whether the same object can return
whether a new version, new ObjectID, or declared seam is required
```

---

# 39. Closing rule

The Structura Reditus Research Library is complete at any release only in the bounded sense appropriate to a registry:

> every admitted object is identifiable, classifiable, source-preserving, relationally legible, versioned, and retrievable under the active library contract.

Completion does not mean exhaustion.

New authors, domains, questions, relations, evidence modes, and research objects may continue to enter through declared extension and admission paths.

The library grows by adding legible work, not by weakening its boundaries.


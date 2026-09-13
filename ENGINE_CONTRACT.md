# Engine Contract

**ID:** `SR-LIBRARY-ENGINE-CONTRACT.v0.1.0`
**Implementation:** the `validators/` package (`validate`, `admit`, `release`, `build_site`)
**Governing specification:** [docs/SR-RESEARCH-LIBRARY-SPEC.v0.1.md](docs/SR-RESEARCH-LIBRARY-SPEC.v0.1.md)

## Object

The engine validates and organizes Research Library records. It does not evaluate the truth of the underlying research claim.

## Source of truth

The source of truth is the version-controlled content of:

```text
schema/
taxonomy/
registry/
receipts/
releases/manifests/
releases/open-seams.yaml
```

The generated public site is a projection and may be rebuilt at any time.

## Runtime outcome

For each submitted research object the engine derives one and only one admission state:

```text
ACCEPTED
RETURNED_FOR_REPAIR
REJECTED
```

The engine evaluates structure first and outcome last.

- `ACCEPTED`: every active admission gate passes and no evaluability-blocking missingness remains.
- `RETURNED_FOR_REPAIR`: required structure is missing or unresolved but can be repaired without falsifying provenance.
- `REJECTED`: an evaluable contract gate fails, such as a wrong authority tier or explicit contract-violating missingness.

`RETURNED_FOR_REPAIR` is never collapsed into `REJECTED`.

## Seven admission gates

A. Identity  
B. Tier placement  
C. Source and provenance  
D. Classification  
E. Boundary and missingness  
F. Relation integrity  
G. Library durability

## Deterministic boundary

Automated code MAY determine:

- schema validity;
- identifier syntax and uniqueness;
- reference resolution;
- controlled-taxonomy membership;
- required-field presence;
- structural gate state;
- receipt generation;
- registry statistics;
- release manifests and hashes.
- provisional structural adjacency among registered Tier-2 objects from declared registry fields for retrieval and review.

Automated code SHALL NOT determine:

- scientific truth;
- novelty;
- importance;
- prestige;
- philosophical persuasiveness;
- domain-native evidentiary sufficiency;
- whether GCD is true;
- whether an external author agrees with Structura Reditus.
- convert similarity or generated adjacency into scientific equivalence, shared mechanism, causation, support,
  contradiction, reproduction, extension, authority transfer, or a durable REL-* relation without separately
  declared evidence and review.

Those burdens remain outside this engine unless a distinct governing contract explicitly supplies them.

## Historical integrity

No release or frozen record is silently rewritten. A material change to object, version, source boundary, authority role, or publication role must be represented as a new version, new ObjectID, or declared seam as appropriate.

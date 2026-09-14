# Tier-2 Census and Repair Report — 2026-09

**Kind:** readback of registry state. The registry (`registry/`, `receipts/`,
`releases/`) is the source of truth; this report restates it and is not a
second database. Decision rule applied: [LIBRARY_SPECIFICATION.md §6.1](../LIBRARY_SPECIFICATION.md).

> Inclusion in the Research Library means organizational conformance only. It
> does not grant canon status, Tier-0 adoption, Tier-1 authority, proof,
> scientific endorsement, weld, or release status.

## A. Pre-pass state (main at 446755f + bridge layer 6d6db61)

| Quantity | Value |
|---|---|
| Accepted Tier-2 objects | 16 (`SR-OBJ-000001..015`, `000018`); 19 accepted receipts (three 1.0.1 revisions) |
| Returned for repair | 3 (`SR-OBJ-000016`, `000017`, `000019`; RCPT-000016/017/019) |
| Reserved ObjectIDs | `SR-OBJ-000016`, `SR-OBJ-000017`, `SR-OBJ-000019` |
| Sources / relations / governing | 46 / 3 / 19 |
| Next free identifiers (recalculated from the live tree) | `SR-OBJ-000020`, `SRC-000047`, `SR-GOV-000020`, `REL-000004`, `RCPT-000023` |
| Known candidate backlog | SEAM-0014 (DOI verification queue), SEAM-0020 (Saturn, SOURCE_NEEDED), SEAM-0021 (census candidates: DMT v2.0, Diamond Clock, RAR, Memristive, Seam-Chain) |

Evidence consulted in this pass: Zenodo REST API metadata (records, concept
resolution, all-versions searches by creator and title), Crossref metadata
for the two external anchors, and the deposited PDFs read as evidence from
their Zenodo records (never committed; the library does not mirror PDFs).
No local handoff bundle or census package was present in the working tree.

## B. Repair outcomes

### SR-OBJ-000016 — The Collapse Formalism: A Reader's Guide to the UMCP/RCFT/ULRC Stack

- Prior blocker: source identity (DOI 10.5281/zenodo.16990995 resolves to Collapse Calculus) and source-stated next burden (RCPT-000016; SEAM-0011).
- Evidence consulted: Zenodo all-versions search for creator "Paulus, Clement" with Formalism / Reader's Guide terms; file listings of both Collapse Calculus version records (16990996, 17007222). No record or file titled The Collapse Formalism exists.
- Repair performed: none possible without invention. Collapse Calculus was not treated as The Collapse Formalism; no DOI was invented.
- Resulting receipt: none (an unchanged blocked submission is not re-receipted).
- Final state: **RETURNED_FOR_REPAIR, identity reserved**; SEAM-0011 updated with the re-search evidence and remains open. Still missing: an archive record, DOI, or owner-supplied manuscript that resolves to the titled work.

### SR-OBJ-000017 — Collapse Calculus: Weld-Continuous Dynamics and Audit Guarantees

- Prior blocker: REPAIRABLE missingness "source-stated next burden for candidate material" (RCPT-000017; SEAM-0013).
- Evidence consulted: deposited PDF at 10.5281/zenodo.16990996 (abstract; Table I policy surface v1.0.2: "Any change requires a weld: a logged pre/post test on the same anchor with tolerance on |Δκ|"; Tier 5 manifest snapshots, weld validation, hashed audit rows; κ preserved under piecewise-secant updates).
- Repair performed: next burden written from those verification targets; claim layers populated from the PDF; historical/current UNRESOLVED_SEAM kept; version 1.0.1.
- Resulting receipt: **RCPT-000023 ACCEPTED**; RCPT-000017 preserved.
- Final state: registered under the same reserved identity; maturity `historical`; nothing historical promoted.

### SR-OBJ-000019 — A Geometry of Admissible Seams: Contract-Bound Invariants and Auditable Transitions

- Prior blocker: REPAIRABLE missingness "source-stated next burden for candidate material" (RCPT-000019; SEAM-0013).
- Evidence consulted: deposited PDF `Geometry of Admissible Seams.pdf` in the shared archive 10.5281/zenodo.17980036 (December 18th, 2025; Appendix D portability criteria: disclosed embedding, reproducibility, seam viability, closure stability under reuse, consistent admissibility behavior, quantified failure boundary; reporting minimum of manifests, closure registries, audit rows).
- Repair performed: next burden written from the portability criteria; claim layers populated; shared-archive SOURCE_BOUNDARY and historical UNRESOLVED_SEAM kept; version 1.0.1. SRC-000024 and SRC-000023 stay distinct SourceIDs.
- Resulting receipt: **RCPT-000024 ACCEPTED**; RCPT-000019 preserved.
- Final state: registered under the same reserved identity; maturity `historical`.

## C. New works registered

| ObjectID | SourceID(s) | Title | Class (primary) | Locus | Domain | Maturity | Receipt |
|---|---|---|---|---|---|---|---|
| SR-OBJ-000020 | SRC-000047 | GCD / UMCP: The First Seam-Chain Casepack | diagnostic (+handoff) | umcp | structura-reditus-core | frozen-local-object | RCPT-000025 |
| SR-OBJ-000021 | SRC-000049, SRC-000048 (ext.) | Nested Return in a Composite Diamond Clock | external-ingress | umcp | physics | source-bounded | RCPT-000026 |
| SR-OBJ-000022 | SRC-000050 | Recursive Accelerating Return | candidate (+diagnostic) | rcft | systems-theory | prospectively-testable | RCPT-000027 |
| SR-OBJ-000023 | SRC-000052, SRC-000051 (ext.) | Identifiable Return in Memristive Associative Memory | external-ingress | umcp | computer-science | retrospectively-evaluated | RCPT-000028 |
| SR-OBJ-000024 | SRC-000053 | Language Across Articulation | language-contact | ulrc | linguistics | source-bounded | RCPT-000029 |
| SR-OBJ-000025 | SRC-000046 (existing) | Empirical Regime Auditing Under the GCD/UMCP Kernel (v2.0) | diagnostic | umcp | structura-reditus-core | frozen-local-object | RCPT-000030 |
| SR-OBJ-000026 | SRC-000054 | Confinement as Integrity Collapse | diagnostic | umcp | physics | historical | RCPT-000031 |
| SR-OBJ-000027 | SRC-000055 | Contract-First Epistemology (full course) | pedagogical (+handoff) | cross-system | education | frozen-local-object | RCPT-000032 |
| SR-OBJ-000028 | SRC-000056 | Contract-First Epistemology: Semester I | pedagogical (+handoff) | cross-system | education | frozen-local-object | RCPT-000033 |
| SR-OBJ-000029 | SRC-000057 | Contract-First Epistemology: Semester II | pedagogical (+handoff) | cross-system | education | frozen-local-object | RCPT-000034 |
| SR-OBJ-000030 | SRC-000058 | Contract-First Epistemology: Full Course Syllabus and Audit Receipt | pedagogical (+handoff) | cross-system | education | frozen-local-object | RCPT-000035 |
| SR-OBJ-000031 (post-pass ingress, 2026-09-14) | SRC-000060, SRC-000051 (ext.) | Prospective Identifiable Return in Associative Memory | diagnostic (+external-ingress, +domain-translation) | umcp | computer-science | prospectively-tested | RCPT-000037 |

Source boundaries and next burdens are on each object record
(`registry/objects/`). Points of record:

- **Seam-Chain Casepack** — DOI 10.5281/zenodo.19870445 verified (the census had it unresolved). Next burden is the paper's own "What This Enables Next" list; the paper "enables these burdens but does not absorb them". REL-000004 (`extends` SR-OBJ-000009) is stated by the source's ladder.
- **Diamond Clock** — two source identities: SRC-000048 (Lourette et al., DOI 10.1103/z2sl-6gcc, eleven authors preserved) and SRC-000049 (local analysis, DOI 10.5281/zenodo.22155902). The external DOI is not assigned to the local paper. No canonical UMCP weld is claimed (AUTHORITY_BOUNDARY missingness).
- **RAR** — 10.5281/zenodo.22035775 (concept) now resolves; latest version 22121149; four earlier version deposits typed. No empirical validation claimed; classification ≠ causal proof.
- **Memristive** — SRC-000051 (He et al., DOI 10.1038/s41467-026-69958-0, nine authors preserved) is external; SRC-000052 is the local manuscript (GCD-AM-IR.2026-09-08 v1.2). At the census pass it had **no DOI** and no public deposit found; publication state `registered-only` (PUBLICATION_BOUNDARY missingness), not inherited from the external study. **Publication update (2026-09-13, after the pass):** the owner reported the public Zenodo deposit of Version 1.2 (frozen 9 September 2026); verified by API as record 10.5281/zenodo.22695434 (concept 22695433, v1.2, 2026-09-09, Preprint, files `identifiable_return.pdf` and the v1.2 frozen research package). SRC-000052 now carries the DOI lineage; SR-OBJ-000023 resubmitted as 1.0.1 with publication state `archived` (**RCPT-000036 ACCEPTED**; RCPT-000028 and the 1.0.0 state preserved). Metadata-only: text, evidence boundary, frozen run, claims, authority, and burdens unchanged; the DOI is the locator for the frozen v1.2, not a new scientific version.
- **Language Across Articulation** — the maintenance instruction said the edition names no DOI; the deposited publication edition names 10.5281/zenodo.22695438 itself. Recorded as stated. Publication state `archived` (Zenodo deposit; peer review / journal acceptance recorded as not claimed).
- **Empirical Regime Auditing v2.0** — existing SRC-000046 reused; no duplicate source.
- **Confinement** — deposited title "A Contract-Frozen Structural Signature ..." used (the instruction's "A Measurable Structural Signature ..." variant is noted on the source). Historical source and object; source-stated non-claims (not a QCD proof, not a Yang–Mills mass-gap solution) recorded; two version records under the concept recorded as missingness.
- **Pedagogical line** — four member works of one shared archive (10.5281/zenodo.20074210), each with its own SourceID and object (SEAM-0008 policy). The Syllabus and Audit Receipt passed the distinct-object test on inspection (own receipt identity CFE.SYLLABUS-RECEIPT.v1.0, scope, out-of-scope, mandate, non-goal). Every record separates structural conformance of the architecture from classroom efficacy (NON_BLOCKING, NON_EVALUABLE). REL-000005 (Semester II `extends` Semester I) is stated by Semester II's own front matter. `course_layout.pdf` is not registered separately.

## D. Deferred or not admitted

| Work | Exact blocker | Missingness class | Repair route |
|---|---|---|---|
| SR-OBJ-000016 The Collapse Formalism | No archive record, DOI, or manuscript resolves to the titled work | REPAIRABLE (RCPT-000016) | Supply the resolving identifier or owner-supplied manuscript; resubmit the same ObjectID |
| Saturn Southern Decagon | Source now public and registered as **SRC-000059** (10.5281/zenodo.22550978, v2.0.1); no owner-supplied Tier-2 classification | — (source only; SEAM-0020) | Owner supplies classification; ordinary admission |
| DMT Version 2.0 | Not a distinct intellectual object; version lineage of SR-OBJ-000011 | — | None; SRC-000019 typed with the v1.0 record as `earlier_version` |
| SEAM-0014 DOI queue, other census candidates | Sources not acquired / owner confirmation pending | — | Acquire source; deduplicate; allocate |

## E. Integrity statement

- No DOI, source claim, tier promotion, relation, or closure was invented. Relations were created only where the source states the relationship (2 relations).
- No released manifest (`SR-LIBRARY.v1.0.0` and earlier) or released governing record was edited; `check_governing` against `governing_immutable_hashes` passes.
- Historical objects (000017, 000019, 000026) keep `maturity: historical`, historical authority boundaries, and UNRESOLVED_SEAM missingness; nothing historical maps onto current contracts.
- Generated bridge candidates (`site/data/bridge_candidates.json`) were rebuilt after ingress; they are retrieval suggestions and created no REL-* records.
- Post-pass identifiers: 29 objects, 59 sources, 5 relations, 19 governing, 35 receipts (32 accepted, 3 repair). Next free: `SR-OBJ-000031`, `SRC-000060`, `SR-GOV-000020`, `REL-000006`, `RCPT-000036`.
- After the Memristive publication update: 36 receipts (33 accepted, 3 repair); next free receipt `RCPT-000037`. Object, source, relation, and governing counts unchanged.
- **Post-pass ingress (2026-09-14) — Prospective Identifiable Return in Associative Memory.** New distinct Tier-2 object `SR-OBJ-000031` (§6.1 Test A: new contract PIR-COMP-2026-09-14-v1.0, new run PIR-COMP-R1, fresh development and untouched confirmation evidence, new concept DOI), source `SRC-000060` (corpus-native; Zenodo 10.5281/zenodo.22739943, concept 22739942, Final Publication Edition v1.0, 14 September 2026, verified by API 2026-09-14; deposited PDF and bundle read), relation `REL-000006` (`SR-OBJ-000031` extends `SR-OBJ-000023`, stated by the source), receipt `RCPT-000037` ACCEPTED (all seven gates PASS). `SR-OBJ-000023` / `SRC-000052` are unchanged and not superseded; `SRC-000051` is reused as the external anchor. Result profile recorded as stated: identity, correction, and discrimination credit earned; reliability partial (9/10 targets; MU-01 159/200 is an observed negative result); p = 0.50 negative control 71/2,000, no leakage trigger; procedural stance CONFORMANT. Not hardware validation; canonical UMCP return/weld not activated (SEAM-0023). Counts: 30 objects, 60 sources, 6 relations, 19 governing, 37 receipts (34 accepted, 3 repair). Next free: `SR-OBJ-000032`, `SRC-000061`, `SR-GOV-000020`, `REL-000007`, `RCPT-000038`.

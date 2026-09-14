# Researcher Portal — Implementation, Invariants, and Adopted Policy

**Status:** implemented on branch `portal/implementation`; deployment to a public host is
an owner-provisioned step (see [PORTAL_OPERATIONS.md](PORTAL_OPERATIONS.md) and
[PORTAL_ACCEPTANCE.md](PORTAL_ACCEPTANCE.md)).
**Baseline reviewed:** `810f4222c7cca357a12184b8cb485617aecb8869` (30 objects, 60 sources,
19 governing references, 1 author, 6 relations, 37 receipts: 34 accepted, 3 repair). Frozen hashes:
[docs/portal-evidence/baseline-810f4222.json](portal-evidence/baseline-810f4222.json), enforced by
`tests/test_baseline_preservation.py`.

## 1. What was built

A public Django 5.2 LTS application under `portal/` that reuses the unchanged `validators/` engine:

| Path | Responsibility |
|---|---|
| `portal/config/` | Settings (`base`, `dev`, `prod`, `test`), URL root, Celery app, WSGI/ASGI |
| `portal/core/` | Append-only `Event`, `Job` outbox (leases, bounded backoff, reconciliation), `/healthz`, shared context |
| `portal/accounts/` | `Account` (private UUID), `AuthorBinding`, `IdentityClaim`, `ReviewAssignment`; django-allauth signup/verification/login/reset; automatic author registration; verified-claim workflow; session revocation; account closure |
| `portal/submissions/` | `Submission`, immutable `SubmissionRevision`, `Upload`, `FieldEvidence`, `ReviewCase`, `Question`/`Response`; workflow state machine; deterministic extraction; SSRF-safe URL acquisition; guided editor; autosave with optimistic tokens; confirm → freeze → evaluate; repair revisions; handoff export; review routes |
| `portal/registry_bridge/` | Pinned isolated checkouts (`git archive`), per-checkout engine import, subprocess `evaluate_worker.py`, identifier allocation (row lock + shared allocator), path policy, GitHub App client (installation tokens, Git Data API, checks, merge), git-backed test double, publication sequence with crash recovery, webhooks, reconciliation |
| `portal/catalog/` | Committed-registry projection (`RegistryProjection`, `ProjectionSnapshot`), public pages, search over the shared index, legacy static-path redirects |
| `portal/templates/`, `portal/static/` | Shared design system (white surfaces, `#337799` actions, visible focus, rem sizing) and two small JS modules (upload progress + client hash, autosave) |
| `portal/tests/` | 39 workflow, access, integration, concurrency, and failure-recovery tests against a scratch clone and a git-backed GitHub double |

Engine additions (repository root, all additive):

| Path | Purpose |
|---|---|
| `validators/allocation.py`, `validators/reserve.py` | Repository-wide allocator and CLI reservation client; reservation ledger under `registry/reservations/` |
| `validators/execution.py` | Canonical submission hash, execution manifests, verification |
| `validators/receipts.py` | Atomic staged bundle writes (`.json`, `.md`, `.submission.json`, execution manifest); refuse-overwrite; idempotent recovery |
| `validators/admit.py` | `evaluate_and_write()` shared by CLI and portal; `--write` now preserves snapshots for all three decisions; `--source-file` hashes; `--registry-base` |
| `validators/search.py` | Shared search index and query semantics used by `site/search.html` and the portal |
| `validators/sitegen.py` | Receipt selection by version + chronology; all attempts listed; search page |
| `validators/checks.py` | `reservation-ledger` / `reservation-schema` checks |
| `schema/execution.schema.json`, `schema/reservation.schema.json` | SR-EXECUTION.v0.1.0, SR-RESERVATION.v0.1.0 (legacy schemas untouched; `schema/VERSION` remains SR-SCHEMA.v0.4.0 because no record schema changed) |
| `tests/fixtures/census_2026_09_snapshot.json` | Immutable census facts; live tests permit evidence-backed growth |

## 2. Store responsibilities

| Store | Authoritative for | Never |
|---|---|---|
| Git repository | authors, admitted objects, sources, relations, receipts + snapshots + execution manifests, reservation ledger, schemas, taxonomies, releases, generated site | credentials, private drafts, uploaded binaries |
| PostgreSQL | accounts, verified bindings, roles, drafts, immutable revisions, events, jobs/outbox, evaluation attempts, publications, allocations, projections | an editable copy of committed registry facts |
| Object storage | original uploads under immutable keys, archive members, export bundles | content that changes behind the same key (`file_overwrite=False`, versioning enabled) |
| Projections | derived views of one identified commit (`ProjectionSnapshot.committed_sha`) | research authority |

Git and PostgreSQL never share a transaction. The outbox (`core.Job`) dispatches after commit;
`Publication` is a state machine over observable Git state; **Registered** is set only in
`registry_bridge.publication._verify` after the exact expected file contents are read back from the
default branch.

## 3. Workflow, admission, publication — three separate things

`Submission.workflow_state` (operational) · `SubmissionRevision.admission_decision` (engine-only) ·
`Publication.status`/`merge_sha` (Git-only). States and meanings are in
`portal/submissions/state.py`; every transition is guarded (`TRANSITIONS`) and appended to `core.Event`
with actor, revision, previous/new state, operation key, and reason.

## 3a. Automatic preparation (the default contribution experience)

Every completed upload runs `submissions.services.prepare` as one outbox job with six recorded steps
(`Submission.processing_notes[-1]["steps"]`, shown live on the status page and via `status.json`):

| Step | What it does | Where |
|---|---|---|
| preserve | files already stored under immutable keys with server-side SHA-256; originals never modified | `register_upload` |
| identify | DOI / arXiv / Zenodo / URL / "Version N" statements with line locators; publication hints (preprint, archived, published) | `preparation.identify_sources`, `merge_identifications` (cross-file **version ambiguity**) |
| duplicates | DOI match → reuse the existing `SRC-*`; title similarity ≥ 0.82 (or long-prefix containment) against committed objects/sources; identical file hashes against execution manifests | `preparation.check_duplicates` over the committed projection |
| extract | deterministic parsers (pypdf, python-docx, Markdown/text/LaTeX, JSON/YAML records, CSV/TSV, bounded ZIP) with page/paragraph/line locators | `extraction.extract` |
| classify | keyword → taxonomy suggestions for evidence mode, Tier-2 class, domain (+secondary), structural focus, functional locus, publication state; ties are reported, never resolved arbitrarily; every suggestion is recorded as `library-classification`, **uncertain**, with the matched terms | `preparation.suggest_classifications` |
| assemble | candidate record; automatic `SRC-NEW-1` proposal built only from what the files state (gaps → source missingness; source type flagged for confirmation); readiness assessment | `extraction.assemble_candidate`, `services._auto_source`, `preparation.assess` |

Failure of any step marks it `failed`, moves the submission to *Processing unavailable*, keeps the upload, and
retries with backoff; the researcher can always continue manually.

**Readiness and questions.** `preparation.assess` classifies every required field as *ready* (present and
reliably extracted or confirmed), *needs confirmation* (present but from an uncertain extraction or a
suggestion), or *missing*, and emits only the questions still open. Each question carries `why` (which
gate/rule needs it), `blocks` (whether it prevents admission), and `resolves` (what answer or evidence
closes it). Two policy questions are added when triggered: **which version governs** (two version
statements across files) and **revision or distinct study** (possible duplicate object). Both must be
answered on the submit page (`_version_resolution`, `_duplicate_resolution`); choosing *revision of
SR-OBJ-X* sets the intended object so the engine archives the previous state instead of minting a duplicate.

**Confirming without retyping.** Saving the draft from the editor (not autosave) records a
`researcher-statement` evidence row ("confirmed in the editor") for every uncertain value the researcher
kept; the original uncertain extraction row is preserved beside it, so uncertainty remains visible in the
evidence history and the field stops being asked about.

**Repair reuse.** *Start repair* copies the frozen revision's evidence rows into the new draft
(`reused_from_revision`), maps the receipt's `missing_structure` to field paths
(`preparation.repair_focus`), and flags exactly those fields in the editor; all seven gates still run on
the newly confirmed revision.

## 4. Admission engine reuse

`registry_bridge/evaluation.py` runs `registry_bridge/evaluate_worker.py` as a **separate process**
inside a fresh `git archive` checkout of the pinned base commit, with that checkout's `validators`
package on `sys.path`. The worker:

1. writes proposed source/author/relation records and reservation ledger entries into the candidate registry (refusing to overwrite committed records with different content);
2. runs `checks.validate_registry()` on the complete candidate — dependency failures return the draft to the researcher with the exact issues and **no receipt**; a broken base stops with a maintainer action;
3. calls `admit.evaluate_and_write()` — the same function the CLI uses — which calls `gates.evaluate_object()` unchanged, writes the bundle, and registers only `ACCEPTED`;
4. marks ledger entries `published` when their record now exists, re-validates, regenerates `site/`;
5. returns the changed files, which `policy.filter_publishable()` restricts to `registry/{authors,objects,sources,relations,reservations}/`, `receipts/{accepted,repair,rejected,executions}/`, and `site/` (`.json`/`.md`/`.html` only).

Precedence is untouched: any FAIL → REJECTED; else any BLOCKED → RETURNED_FOR_REPAIR; else ACCEPTED.
The portal's preflight (`submissions.services.preflight`) is advisory and never allocates or writes.

Human review is triggered only by documented conditions (`registry_bridge.evaluation.review_triggers`):
open identity claim; AuthorIDs not bound to the submitting account; proposed relation without stated
evidence; declared source-version ambiguity. Reviewers resolve inputs or return the draft; there is no
"accept anyway" control, and a resolved case re-enters the same gates as a distinct attempt.

## 5. Identifiers

`validators.allocation.next_free()` reconciles committed records, `registry/objects/history/`,
receipt IDs and the identities receipts name, `.submission.json` snapshots, and the ledger. The portal
adds a `NamespaceLock` row lock and counts its own uncommitted/withdrawn allocations
(`registry_bridge/allocation.py`). Receipt numbers are reserved before evaluation and **withdrawn, never
reissued** when an attempt is abandoned because the base moved. Namespace exhaustion raises
`NamespaceExhausted` 100 values before the schema limit.

CLI contributors reserve with `python -m validators.reserve SR-OBJ --purpose "…"` and commit the
ledger file with their work; `admit --register` marks the reservation published.

## 6. Search semantics (shared)

Documented in `validators/search.py` and emitted in `site/data/search_index.json["semantics"]`: all
unquoted terms must match (AND, case/accent-folded); `"quoted"` is a phrase; identifiers and DOIs match
exactly; filters AND across axes / OR within, matching primary or secondary values; ranking is the count
of distinct matched fields then identifier order. Baseline misses resolved: *physically constrained* →
SR-OBJ-000023 (`main_question`); *Clement* → all authored works; `REL-000006` → both endpoints.

Generated connections remain the existing `bridges` detector, shown at most five per record (sorted by
signal count, then strength, then identifier; "Show all" available), labelled as retrieval suggestions
whose "strength" is a detector label, never a probability. No ranking change creates a REL-*.

## 7. Adopted policy clarifications (prospective, versioned)

These clarify operation; they do not alter any released record or manifest.

**7.1 Receipt bundles (RECEIPTS.v0.2 clarification).** From `RCPT-000038` onward every formal decision —
accepted included — preserves `RCPT-NNNNNN.submission.json` beside the receipt and
`receipts/executions/RCPT-NNNNNN.execution.json` (SR-EXECUTION.v0.1.0). Historical receipts
`RCPT-000001…000037` are unchanged; their manifests cannot be truthfully reconstructed and are not
fabricated. A corrected receipt is a new receipt with `supersedes_attempt`, never an edit.

**7.2 Identifier reservations (IDENTIFIERS.v0.2 clarification).** Values are reserved through the
ledger before use on both routes; withdrawn values are never recycled; direct PRs proposing unreserved
IDs are brought into the ledger before merge.

**7.3 Portal source policy (prospective).** External papers stay on their platforms; the library never
mirrors them. When a researcher opts to publish author-owned files through the portal
(`SubmissionRevision.publish_files`), the execution manifest records the file hashes with
`public: true`; serving those files from a stable versioned URL requires the object-storage public
routing described in PORTAL_OPERATIONS.md and is **not enabled by default**. Private files are never in
Git; only hashes are. Historical source records are unchanged.

**7.4 Account and withdrawal policy.** Closing an account deactivates login and access to drafts. It
does not erase published records, receipts, or history. Withdrawal of a registered record is a visible
`publication_state`/status event with preserved history — never a rewrite of Git history. Public
author records contain only the display name, optional ORCID, status, registration time, and a
fixed note; no email ever enters Git.

**7.5 Branch protection.** The effective default-branch rule must require a PR, the `validate` check
(the emitted name), and an up-to-date base; deletion/force-push protection stays; no bypass for the
portal App or the founder. See the updated [MAIN_PROTECTION_RULESET.md](MAIN_PROTECTION_RULESET.md).

## 8. Invariants preserved (with the enforcing code)

| Invariant | Enforcement |
|---|---|
| Three distinct registry surfaces | catalog pages keyed by kind; `governing` never editable by submissions (`policy.FORBIDDEN_PREFIXES`) |
| Source identity | proposed sources carry original `source_authors`; `_ambiguous_version` opens a review case |
| Exactly three decisions | engine unchanged; `DECISION_TO_STATE` maps only those three |
| Founder neutrality | `review_triggers` never inspects identity except for unbound AuthorIDs; `test_e04_e05` |
| Missingness preserved | editor requires classed missingness lines; extraction adds questions, never values |
| Negative findings are results | `test_e04_e05` |
| History | `SubmissionRevision.save()` raises on mutation; `archive_object_version` unchanged; snapshot fixture test |
| Profiles | `validators.profiles` unchanged; zero-work profile shows "No registered research objects yet." |
| Relations vs suggestions | separate template sections; suggestion rows link to *propose a relation*, never create one |
| Reproducibility | execution manifest binds hash, engine revision, schema/taxonomy versions, base commit |
| Baseline byte-identity | `tests/test_baseline_preservation.py` (225 files) |

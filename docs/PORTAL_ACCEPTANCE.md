# Researcher Portal — Acceptance Ledger

**Executed version:** branch `portal/implementation` (see `git log`), engine at reviewed baseline
`810f4222c7cca357a12184b8cb485617aecb8869` plus additive changes; Python 3.12.3; Django 5.2.17;
django-allauth 65.19.3. **Date:** 2026-09-14.

**Baseline evidence (before any edit):** `python -m validators.validate` → *OK (no issues found)*;
`python -m pytest` → **74 passed**; `python -m validators.build_site` → no diff. Frozen hashes of 225
historical artifacts: [portal-evidence/baseline-810f4222.json](portal-evidence/baseline-810f4222.json).

**Final automated result:** engine suite **94 passed** (`python -m pytest` at repo root), portal suite
**39 passed** (`make -C portal test`), validator OK, site regeneration deterministic.

**Environments used:**
* *Unit/integration* — pytest with an isolated scratch clone of the repository and the git-backed
  GitHub double (`registry_bridge.fake_github`), which performs real branch/commit/PR/check/merge
  operations with git plumbing on that clone.
* *Browser* — headless Chromium (Playwright 1.62) against a live dev server (`runserver`, eager Celery,
  file-captured email, git-backed GitHub double) on an isolated clone `/tmp/accept-repo`; screenshots and
  the machine ledger are in [portal-evidence/browser/](portal-evidence/browser/).
* *Staging/production* — **not provisioned in this environment.** No hosting, domain, SMTP service,
  managed PostgreSQL/Redis/S3, or GitHub App installation exists yet. Rows that require them are
  **NOT RUN** and listed with the exact owner action in §Dependencies.

Legend: PASS / FAIL / NOT RUN. NOT RUN is not a pass.

## A — Accounts

| ID | Scenario | Result | Evidence | Limitation |
|---|---|---|---|---|
| A01 | New researcher signs up and verifies email | **PASS** | `test_a01_signup_verify_registers_author_and_lands_in_workspace`; browser ledger `A01.*` = AUTH-0002, `registered`; screenshots 01–03 | Email delivery was local capture (file backend), not a real mailbox |
| A02 | Same user returns from a new session | **PASS** | `test_a02_returning_session_keeps_identity_without_duplicate_registration`; browser `A02.same_author_id` = AUTH-0002, submission listed; screenshot 11 | — |
| A03 | Password recovery and session revocation | **PASS** | `test_a03_password_reset_retains_identity_and_revokes_sessions` (reset link from captured mail, identity retained, revoked session gets 302) | Real reset-mail delivery NOT RUN |
| A04 | User submits another author's name/ID | **PASS** | `test_a04_submitting_another_authors_name_or_id_grants_nothing` (display name + ORCID text of AUTH-0001 → claim state, no binding; denied claim → fresh identity) | — |
| A05 | Two users share a display name | **PASS** | `test_a05_same_display_name_yields_distinct_identities` | — |
| A06 | Two simultaneous signups and retried jobs | **PASS** | `test_a06_concurrent_signups_and_retried_jobs_get_unique_ids` (6 accounts, duplicate deliveries, 6 unique AUTH values committed once each); engine `test_concurrent_reservations_never_collide` (8 threads × 12) | Process-level concurrency across hosts NOT RUN (needs PostgreSQL; SQLite in tests) |
| A07 | New author has zero works | **PASS** | `test_a07_zero_work_profile_is_valid_and_empty`; author page renders “No registered research objects yet.” | — |
| A08 | User A requests user B's draft or private upload | **PASS** | `test_a08_private_draft_and_upload_are_denied_to_other_users` (404 on detail/edit/file/handoff/autosave; no private bytes) | — |

## U — Uploads

| ID | Scenario | Result | Evidence | Limitation |
|---|---|---|---|---|
| U01 | Upload, refresh, sign out, return | **PASS** | `test_u01_upload_persists_bytes_and_server_hash`; browser `U01.*` (screenshot 04) | Filesystem storage in tests; S3 path exercised only by configuration |
| U02 | Interrupted/retried upload | **PASS** | `test_u02_retried_upload_of_completed_file_is_not_duplicated` (hash-identical retry returns the same upload; client-hash mismatch refused, nothing recorded) | Network interruption simulated by hash mismatch, not by a dropped socket |
| U03 | Unsupported/oversize/malformed archive | **PASS** | `test_u03_oversize_and_malformed_archives_are_intake_errors_not_rejections` (per-file limit, member-count bomb, path traversal → intake problems, no receipt) | — |
| U04 | PDF/DOCX/Markdown/LaTeX/record/ZIP inputs | **PASS** | `test_u04_supported_formats_extract_or_route_to_manual` (LaTeX `\title`/`\author` with line locators, DOCX title, unsupported → manual route with questions); U01 (Markdown); browser (JSON record); U03 (ZIP) | PDF path exercised by `pypdf` unit parser only (encrypted/scanned reported, OCR not run) |
| U05 | Document tries to instruct the processor | **PASS** | `test_u05_document_instructions_do_not_change_control_flow` (role, authors, state unchanged; text captured as text) | — |
| U06 | Supplied URL targets private infrastructure | **PASS** | `test_u06_private_url_is_refused_and_gap_preserved` (loopback, link-local metadata, localhost, ftp, embedded credentials refused; gap preserved) | — |

## P — Preparation

| ID | Scenario | Result | Evidence | Limitation |
|---|---|---|---|---|
| P01 | Extracted fields reviewed | **PASS** | `test_p01_field_evidence_shows_origin_and_locator`; browser `P01.evidence_rows` = 25, screenshot 05 | — |
| P02 | Two browser tabs edit a draft | **PASS** | `test_p02_stale_draft_is_detected_not_overwritten`; autosave returns 409 with the newer version | Browser-level dual-tab NOT RUN (server semantics verified) |
| P03 | Confirmed revision is edited/repaired | **PASS** | `test_p03_confirmed_revision_is_immutable_and_repair_links_new_revision` (save() on frozen revision raises; r2 links r1; manifest `supersedes_attempt`) | — |

## E — Admission

| ID | Scenario | Result | Evidence | Limitation |
|---|---|---|---|---|
| E01 | Complete structurally conformant record | **PASS** | `test_e01_complete_record_is_accepted_registered_and_verified`; browser `E01.final_state` = Registered, RCPT-000038, SR-OBJ-000032 (screenshots 08–10); merged clone validates OK | Record was the library's synthetic self-test fixture |
| E02 | Repairable missing required structure | **PASS** | `test_e02_repairable_gap_returns_for_repair_with_snapshot` (Gate E BLOCKED; `receipts/repair/*.submission.json` committed; nothing registered) | — |
| E03 | Evaluable wrong-tier/contract violation | **PASS** | `test_e03_contract_violation_is_rejected_with_route` (Gate B FAIL; rejected snapshot committed; editor cannot even express a non-tier-2 claim) | — |
| E04 | Founder and external author, same inputs | **PASS** | `test_e04_e05_founder_and_external_author_identical_and_negative_results_not_penalized` | — |
| E05 | Negative result or challenge | **PASS** | same test: nine-of-ten failure claim + challenging question → ACCEPTED | — |
| E06 | UI changes the displayed decision | **PASS** | `test_e06_client_supplied_decision_is_ignored` (unknown fields 422; POSTed `decision=ACCEPTED` ignored; engine returns RETURNED_FOR_REPAIR) | — |
| E07 | CLI and portal evaluate identical pinned inputs | **PASS** | engine `test_cli_and_direct_evaluation_are_deterministic`; both routes call `admit.evaluate_and_write` → `gates.evaluate_object` | — |
| E08 | Reuse same receipt ID with different content | **PASS** | engine `test_bundle_refuses_overwrite_and_recovers_identical_repeat`; portal `test_e08_receipt_id_reuse_with_different_content_is_refused` | — |
| E09 | Restore a receipt and its inputs | **PASS** | engine `test_manifest_verifies_against_snapshot_and_detects_tampering`; merged clone: `verify_manifest_against_snapshot(RCPT-000038)` → consistent | — |

## G — Registration

| ID | Scenario | Result | Evidence | Limitation |
|---|---|---|---|---|
| G01 | Accepted submission reaches Git | **PASS** (double) / **NOT RUN** (GitHub) | E01 test + browser run: branch → commit → PR #2 → `validate` success → squash merge → readback of every record file → Registered | Real GitHub App write requires owner provisioning |
| G02 | Failed required check or unresolved conflict | **PASS** | `test_g02_failed_check_blocks_merge_and_keeps_work` (BLOCKED with PR/head/check named; state stays *Accepted — registration pending*) | — |
| G03 | GitHub unavailable after ACCEPTED | **PASS** | `test_g03_github_unavailable_after_accept_keeps_pending_then_recovers` (injected outages → FAILED job with backoff; reconcile recovers → Registered) | — |
| G04 | Worker crashes after merge before acknowledgment | **PASS** | `test_g04_worker_crash_after_merge_recovers_same_commit` (MERGED-not-verified → verify finds same commit; no second merge) | — |
| G05 | Duplicate webhook/job delivery | **PASS** | `test_g05_duplicate_job_delivery_creates_nothing_extra`; `WebhookDelivery` unique constraint | Signed-webhook HTTP path exercised by code review only; live delivery NOT RUN |
| G06 | Concurrent web and Codespaces contribution | **PASS** | `test_g06_base_moved_by_another_writer_rebuilds_without_collision` (other writer advances main mid-publication → attempt abandoned, receipt number withdrawn, distinct re-evaluation on new base → Registered; other writer's file preserved) | — |
| G07 | Crafted submission changes workflows/engine paths | **PASS** | `test_g07_crafted_paths_are_refused_by_policy`; CI step in `.github/workflows/validate.yml` for `portal/*` branches | CI step itself NOT RUN here (no Actions runner) |
| G08 | Old repair followed by accepted revision | **PASS** | `test_g08_current_receipt_is_the_acceptance_for_registered_version_and_history_shows_all`; `sitegen.select_current_receipt` | — |
| G09 | Legitimate seventh declared relation | **PASS** | `test_g09_g10_live_engine_tests_permit_growth` runs `tests/test_census_2026_09.py` + baseline test inside the grown checkout; snapshot fixture keeps the six-relation census immutable | — |
| G10 | Legitimate repair of previously blocked object | **PASS** | same test; `test_collapse_formalism_blocked_state_is_preserved_or_repaired_with_evidence` encodes the evidence-backed transition | — |

## S — Search and connections

| ID | Scenario | Result | Evidence | Limitation |
|---|---|---|---|---|
| S01 | Search “physically constrained” | **PASS** | engine `test_s01_physically_constrained_finds_object_23_via_question`; portal `test_s01…`; live server: 1 hit via `main_question` | — |
| S02 | Search “Clement” or REL-000006 | **PASS** | engine + portal `test_s02…`; live server: REL-000006 → SR-OBJ-000023, SR-OBJ-000031 | — |
| S03 | Filter secondary domain/evidence/maturity | **PASS** | `test_s03_filters_*` (engine + portal): matched fields, applied chips, reset, shareable link | — |
| S04 | Generated connection shown/promoted | **PASS** | `test_s04_suggestions_are_labelled_capped_and_create_no_relation`; ≤5 shown + “Show all”; no REL-* created | Fixed-sample usefulness adjudication of suggested pairs **NOT RUN** (recorded as follow-up; thresholds unchanged) |
| S05 | Profile after revision/repair | **PASS** | `test_s05_profile_counts_current_objects_only` (repair + two registered revisions → 1 object) | — |

## H — Handoff

| ID | Scenario | Result | Evidence | Limitation |
|---|---|---|---|---|
| H01 | Owner exports a frozen handoff | **PASS** | `test_h01_h02_handoff_exports_are_complete_and_scoped` (all 12 members, SHA256SUMS verified, publication status) | — |
| H02 | Public-safe handoff requested | **PASS** | same test + browser download `handoff-r1-public.zip` (8632 bytes) in evidence dir: private files excluded and listed in `files/UNAVAILABLE.json`; no email/password strings | — |

## O — Operations

| ID | Scenario | Result | Evidence | Limitation |
|---|---|---|---|---|
| O01 | Worker/broker restart | **PASS** (logic) | G03/G04 + `core.tasks.reconcile` lease expiry re-dispatch | Real Redis/Celery process restart NOT RUN (eager mode in tests) |
| O02 | Backup restored into staging | **NOT RUN** | procedure documented in PORTAL_OPERATIONS.md §6 | Requires provisioned PostgreSQL + object storage |
| O03 | Mobile, keyboard, and 200% zoom | **PASS** | browser ledger: first Tab focuses an input, no horizontal overflow at 200% (screenshot 06), mobile upload input visible (07) | Screen-reader run NOT RUN |
| O04 | Production integration smoke test | **NOT RUN** | — | Requires email, storage, auth, GitHub App, branch rules on a real host |
| O05 | Baseline preservation check | **PASS** | `tests/test_baseline_preservation.py` (225 files byte-identical; counts never shrink); also passes inside the grown acceptance checkout | — |

## Dependencies blocking the NOT RUN rows (owner actions)

1. **Hosting** for web + worker containers (`portal/Dockerfile`), managed PostgreSQL, Redis, S3-compatible bucket (private, versioned), HTTPS termination, domain → set the *Website*, *PostgreSQL*, *Background jobs*, *Files* groups in `portal/.env.example`.
2. **Email** — SMTP/API provider with a verified sender domain → `EMAIL_*`, `DEFAULT_FROM_EMAIL`.
3. **GitHub App** — create, grant Contents/PR write + Checks/Statuses read, install on a **staging repository first**, then production → `GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID`, private key, `GITHUB_WEBHOOK_SECRET`; webhook URL `/integrations/github/webhook`.
4. **Branch protection** — apply [MAIN_PROTECTION_RULESET.md](MAIN_PROTECTION_RULESET.md) (require PR + `validate` + up-to-date; no bypass); remove the untargeted ruleset that names `Validate Research Library`.
5. **Administrator bootstrap** — after the owner signs up and verifies: `python manage.py bootstrap_admin --email <owner> --link-author AUTH-0001 --evidence "<how control was verified>"`.
6. Then run: `python manage.py check_config` (must exit 0 under `config.settings.prod`), the staging smoke test (sign up, upload, submit a **synthetic, clearly labelled** record to the staging repository, verify PR/check/merge), the restore drill (§6), and fill rows G01 (GitHub), O01, O02, O04 here.

Until those steps are complete, the live public signup/upload/registration path is **not** claimed to work.

# Researcher Portal — Operations

Setup, deployment, support, backup, restoration, and credential rotation for the public portal.
Nothing in this document is a claim that a resource already exists; every external input is named so
the owner can provision it and the executor can verify it with `python manage.py check_config`.

## 1. Local start (one command)

```
docker compose -f portal/compose.yaml up --build
```

Starts PostgreSQL 16, Redis 7, MinIO (S3-compatible, bucket `portal-private` with versioning), Mailpit
(captured email at http://localhost:8025 — **not** real delivery), a one-shot `migrate` service, the web
service (http://localhost:8000) and the worker with the reconciliation beat. All values in `compose.yaml`
are documented local placeholders. The GitHub adapter is the git-backed double
(`registry_bridge.fake_github.FakeGitHubClient`), so publications land in the local clone's `main` and
never reach GitHub.

Without Docker (Python 3.12 required):

```
make -C portal venv            # hashed lock install
cd portal && . .venv/bin/activate
cp .env.example .env           # then edit; never commit .env
python manage.py migrate
python manage.py reindex_registry
python manage.py runserver 0.0.0.0:8000
celery -A config worker --beat --loglevel=INFO      # second terminal
```

Tests: `make -C portal test` (portal) and `make -C portal engine-tests` (repository engine).

## 2. Deployment inputs

Validated at startup by `python manage.py check_config` (exit 1 names each missing input).

| Group | Variables |
|---|---|
| Website | `PORTAL_PUBLIC_BASE_URL` (https), `PORTAL_ALLOWED_HOSTS`, `PORTAL_CSRF_TRUSTED_ORIGINS`, `PORTAL_BEHIND_TLS_PROXY`, `PORTAL_HSTS_SECONDS`, `PORTAL_SUPPORT_CONTACT` |
| Django | `DJANGO_SECRET_KEY` (secret manager), `DJANGO_SETTINGS_MODULE=config.settings.prod`, `PORTAL_LOG_LEVEL`, `PORTAL_SESSION_COOKIE_AGE` |
| PostgreSQL | `DATABASE_URL`, `DATABASE_CONN_MAX_AGE`; separate migration and runtime roles recommended; backup policy §6 |
| Background jobs | `CELERY_BROKER_URL`, `PORTAL_WORKER_CONCURRENCY`, `PORTAL_JOB_LEASE_SECONDS`, `PORTAL_JOB_MAX_ATTEMPTS`, `PORTAL_JOB_TIME_LIMIT_SECONDS`, `PORTAL_RECONCILE_INTERVAL_SECONDS` |
| Files | `PORTAL_STORAGE_BACKEND=s3`, `S3_ENDPOINT_URL`, `S3_REGION`, `S3_BUCKET` (private, versioned, encrypted at rest), `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_SIGNED_URL_SECONDS`, upload/archive/URL limits |
| Email | `EMAIL_BACKEND=…smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` (verified sender/domain) |
| GitHub | `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME`, `PORTAL_REGISTRY_DEFAULT_BRANCH`, `GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID`, `GITHUB_APP_PRIVATE_KEY` or `GITHUB_APP_PRIVATE_KEY_PATH`, `GITHUB_WEBHOOK_SECRET`, `GITHUB_REQUIRED_CHECK=validate`, `GITHUB_MERGE_METHOD=squash`, `PORTAL_GITHUB_ADAPTER=registry_bridge.github_app.GitHubAppClient` |
| Account ownership | `python manage.py bootstrap_admin --email <verified owner> [--link-author AUTH-0001 --evidence "…"]` |
| Extraction | pypdf / python-docx versions from the lock; `PORTAL_EXTRACTION_TIME_BUDGET_SECONDS`; optional `PORTAL_EXTRACTION_MODEL_SERVICE_URL` + `PORTAL_EXTRACTION_MODEL_VERSION` (unset = deterministic parsers only, disclosed in preparation notes) |
| Operations | `/healthz` (web, database, outbox age, dead jobs, storage, registry head, pending publications), structured logs (operation/revision references only) |

## 3. GitHub App provisioning (owner action)

1. Create a GitHub App owned by the repository owner. Permissions: **Contents: read & write**,
   **Pull requests: read & write**, **Checks: read**, **Commit statuses: read**, **Metadata: read**.
   No administration, no workflow-file write. Subscribe to `push`, `pull_request`, `check_run`,
   `check_suite`. Webhook URL `https://<host>/integrations/github/webhook`, secret → `GITHUB_WEBHOOK_SECRET`.
2. Generate a private key; store the PEM in the secret manager (`GITHUB_APP_PRIVATE_KEY`) or mount it
   read-only (`GITHUB_APP_PRIVATE_KEY_PATH`). Rotate by generating a new key, deploying, then revoking the old one.
3. Install the App on **the staging repository first**, then production. Record `GITHUB_APP_ID`
   and `GITHUB_APP_INSTALLATION_ID`.
4. Configure default-branch protection per [MAIN_PROTECTION_RULESET.md](MAIN_PROTECTION_RULESET.md):
   require a PR, the `validate` check, and an up-to-date base; no bypass. Verify with
   `gh api repos/<owner>/<repo>/rules/branches/main`.
5. `python manage.py check_config` must exit 0 under `config.settings.prod`.

Installation tokens are short-lived (≤1 h), refreshed on 401, and never logged or sent to the browser.

## 4. Production topology

HTTPS terminator → `gunicorn` web (image from `portal/Dockerfile`) · isolated worker
(`celery -A config worker --beat`) on the same image · PostgreSQL · Redis · S3-compatible bucket ·
GitHub App. Run `python manage.py migrate` as a **one-shot job before** rolling web/worker (never on
process start). Staging uses its own database, bucket, secrets, and an authorized staging repository;
a staging deployment must never point `GITHUB_REPO_*` at production.

Migrations are additive. Before each deploy: back up PostgreSQL (§6), inspect
`python manage.py migrate --plan`, deploy in an order compatible with old and new processes.
Rollback = redeploy compatible code or apply a forward correction; never roll back published research
by rewriting Git history.

## 5. Recovery behaviour

| Failure | Behaviour |
|---|---|
| Email unavailable | allauth surfaces the error; verification can be re-sent from `/accounts/email/`; no account is created twice |
| Extraction/parse failure | submission → *Processing unavailable* with the safe error; job retried with bounded backoff; manual completion always possible |
| Storage interruption | upload not marked complete; retry never duplicates a completed file (hash match) |
| Expired installation token | refreshed on 401 |
| GitHub rate limit / 5xx | `RetryableError`; `Publication.retries` increments; job backoff 15 s → 1 h, max `PORTAL_JOB_MAX_ATTEMPTS`, then `DEAD` with the exact error in the review queue |
| Base moved / non-fast-forward | publication `ABANDONED`, its receipt number withdrawn, a distinct re-evaluation attempt queued on the new base; earlier outcome preserved |
| Required check failed | `BLOCKED` with PR/head/check named; submission stays *Accepted — registration pending*; retry from `/review/` after the cause is fixed |
| Worker restart mid-job | lease expiry → job re-dispatched by `core.tasks.reconcile`; publication resumes from observable Git state (existing branch/PR/merge), never a second PR |
| Lost webhook | beat-scheduled reconciliation re-dispatches in-flight publications every `PORTAL_RECONCILE_INTERVAL_SECONDS` |
| Duplicate webhook | `WebhookDelivery.delivery_id` unique |

## 6. Backup and restoration

A Git clone is **not** a complete backup: accounts, bindings, drafts, uploads, and pending
publications live only in PostgreSQL and object storage.

* PostgreSQL: nightly `pg_dump -Fc` plus WAL/PITR where the provider supports it; retain 30 days.
* Object storage: bucket versioning enabled (`compose.yaml` does this for MinIO); retain versions ≥ 90 days; cross-region replication recommended.
* Secrets: secret manager with audit log.

Restore drill (staging): restore the dump; point `S3_*` at a restored/replicated bucket; run
`python manage.py check_config`, `migrate --plan`, `reindex_registry`; open `/review/` and confirm
pending publications and dead jobs are listed; `core.tasks.reconcile()` then reconciles publications
against Git **before** any new write is allowed; download one handoff bundle and verify `SHA256SUMS`.
Record the drill outcome in PORTAL_ACCEPTANCE.md (O02).

## 7. Retention and withdrawal

Confirmed revisions, evaluation attempts, and receipts are retained indefinitely. Drafts belong to
their owner; draft deletion and account closure require ownership and are recorded as events.
Withdrawal of a registered record is a maintainer action producing a new record version with a
visible status; Git history is never rewritten. Public fields never contain email addresses.

## 8. Support

Maintainers see pending registrations, blockers, identity claims, and stopped jobs at `/review/`.
Logs carry `operation_key`/revision references and `last_safe_error`, never manuscript text or secrets.

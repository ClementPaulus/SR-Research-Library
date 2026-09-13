# SR-LIBRARY-MAIN-PROTECTION.v1

Recommended GitHub ruleset for `main`:

- Target: default branch / `main` only.
- Exclusions: none.
- Bypass: none by default. If an administrator recovery bypass is later adopted, prefer pull-request-only bypass where supported.
- Restrict deletions and block force pushes (non-fast-forward updates).
- **Require a pull request before merging** (at least the author's own review is acceptable for a single-maintainer library; dismiss stale approvals on new pushes).
- **Require status checks to pass before merging**, with the workflow job `validate` from `.github/workflows/validate.yml` listed as a required check (it runs `python -m validators.validate`, `pytest`, and a deterministic `site/` regeneration diff). Require branches to be up to date before merging.
- Do not grant bypass to Copilot, ordinary contributors, library authors, or automated submission tooling.

Working branches remain unrestricted enough to permit feature, contributor, and automation work before pull-request validation.

## Applying it

GitHub UI: Settings → Rules → Rulesets → edit `SR-LIBRARY-MAIN-PROTECTION.v1` → enable *Require a pull request before merging* and *Require status checks to pass* (add `validate`; enable *Require branches to be up to date*).

Equivalent `gh` call (replace `RULESET_ID` with the existing ruleset id from `gh api repos/ClementPaulus/SR-Research-Library/rulesets`):

```
gh api -X PUT repos/ClementPaulus/SR-Research-Library/rulesets/RULESET_ID --input - <<'EOF'
{
  "name": "SR-LIBRARY-MAIN-PROTECTION.v1",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "pull_request", "parameters": { "required_approving_review_count": 0,
      "dismiss_stale_reviews_on_push": true, "require_code_owner_review": false,
      "require_last_push_approval": false, "required_review_thread_resolution": false } },
    { "type": "required_status_checks", "parameters": { "strict_required_status_checks_policy": true,
      "required_status_checks": [ { "context": "validate" } ] } }
  ]
}
EOF
```

Apply this before bulk corpus ingestion so every import lands through a pull request with green checks.

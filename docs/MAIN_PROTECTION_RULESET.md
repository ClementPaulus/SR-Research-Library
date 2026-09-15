# SR-LIBRARY-MAIN-PROTECTION.v1

**Observed at baseline `810f4222`:** one active default-branch ruleset restricting deletion and
non-fast-forward pushes, and a second ruleset with **no branch targets** that requires a check named
`Validate Research Library`. The workflow's emitted check is the *job* name, `validate`, so the second
ruleset is ineffective as written. Consolidate into one effective rule as below; remove the redundant
ruleset only after the replacement is confirmed with
`gh api repos/ClementPaulus/SR-Research-Library/rules/branches/main`.

Recommended GitHub ruleset for `main`:

- Target: default branch / `main` only.
- Exclusions: none.
- Bypass: none. Do not grant bypass to Copilot, ordinary contributors, library authors, the portal's
  GitHub App, or the founder. A single-maintainer installation may use zero required approvals for
  routine publication; source/identity review triggers are enforced by the portal application, not by
  GitHub review.
- Restrict deletions and block force pushes (non-fast-forward updates).
- **Require a pull request before merging** (dismiss stale approvals on new pushes).
- **Require status checks to pass before merging**, with the workflow job **`validate`** from
  `.github/workflows/validate.yml` listed as a required check (it runs `python -m validators.validate`,
  `pytest`, a deterministic `site/` regeneration diff, and — for `portal/*` branches — the runtime
  path-policy diff). Require branches to be up to date before merging (`strict`).
- If linear history is required, use squash or rebase merges; the portal uses `GITHUB_MERGE_METHOD=squash`.

Working branches remain unrestricted enough to permit feature, contributor, and automation work before
pull-request validation. Portal publication branches are named `portal/<kind>/<operation-key-prefix>`.

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

## Verifying the effective rule and check name

```
gh api repos/ClementPaulus/SR-Research-Library/rules/branches/main          # effective rules on main
gh api repos/ClementPaulus/SR-Research-Library/rulesets                      # all rulesets (find untargeted ones)
gh api repos/ClementPaulus/SR-Research-Library/commits/main/check-runs --jq '.check_runs[].name'   # emitted names: expect "validate" (and "portal")
```

The portal reads the required check name from `GITHUB_REQUIRED_CHECK` (default `validate`) and
refuses to merge until that check has concluded `success` on the current PR head.

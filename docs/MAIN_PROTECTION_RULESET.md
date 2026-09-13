# SR-LIBRARY-MAIN-PROTECTION.v1

Recommended GitHub ruleset for the first deployment:

- Target: default branch / `main` only.
- Exclusions: none.
- Bypass: none by default. If an administrator recovery bypass is later adopted, prefer pull-request-only bypass where supported.
- Require pull request before merge.
- Require the repository validation workflow to pass.
- Do not grant bypass to Copilot, ordinary contributors, library authors, or automated submission tooling.

Working branches remain unrestricted enough to permit feature, contributor, and automation work before pull-request validation.

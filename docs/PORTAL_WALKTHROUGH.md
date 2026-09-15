# Researcher Portal — Walkthrough of the Demonstrated Journeys

Four journeys were executed by a headless Chromium browser against a live development server on an
isolated clone of this repository (git-backed GitHub double, file-captured email, eager worker). The
manuscripts are synthetic and describe only the library's own intake machinery. Evidence:
[portal-evidence/journeys/](portal-evidence/journeys/) (screenshots `01`–`19`, `journeys-ledger.json`,
the uploaded PDFs, one public-safe handoff). Reproduce with `portal/tests/run_journeys.sh`.

After the run the isolated clone's `main` held eight merged pull requests (four author registrations,
one repair receipt, four accepted registrations), `python -m validators.validate` reported no issues, and
the census and baseline-preservation tests passed inside that grown checkout.

## J1 — New researcher, PDF manuscript, registered without manual steps

1. **Sign up once** (display name, email, password, terms) → verification link → log in → workspace shows
   `AUTH-0002 · registered`. No identifier was typed; no maintainer acted. *(01)*
2. **Upload** `j1-manuscript-v2.pdf`. Status page: *Uploaded → Preparing → Needs your review*; the six
   preparation steps all `done`; duplicate check: "no matching DOI, similar title, or identical file". *(02)*
3. **Review.** Readiness: **3 ready · 7 to confirm · 14 missing · 21 blocking questions**. Title prefilled
   from PDF metadata (page/locator shown, *uncertain*); suggestions kept visible as *library
   classification*: evidence mode → `simulation`, Tier-2 class → `diagnostic`, publication state →
   `preprint`, each with the matched keywords. Seven evidence rows carry locators; seven are marked
   uncertain. An automatic source proposal `SRC-NEW-1` was built from the file's own statements (version
   "2", no DOI → recorded as source missingness). *(03)*
4. **Answer only what is missing** (object of study, main question, boundaries, claim layers, next burden…)
   and press *Save draft*. Readiness: **24 ready · 0 to confirm · 0 missing · 0 blocking**. The kept title
   now carries a *confirmed in the editor* row beside the original uncertain extraction. *(04)*
5. **Submit.** The confirm page asks the one policy question still open (source type: corpus-native) and
   requires the claims-by-layer acknowledgement. *(05)*
6. **Registered.** `RCPT-000038`, `SR-OBJ-000032`, profile link `AUTH-0002`, search hit, public record
   page showing the new `SRC-*` and receipt, profile counting **1** object, public-safe handoff
   downloaded (8.6 KB). *(06, 07)*

## J2 — Ambiguous submission: two versions and a near-duplicate title

1. Upload `j2-manuscript-v1.pdf` and `j2-manuscript-v2.pdf` (title is a long prefix-extension of J1's).
2. Editor shows **Version ambiguity** ("Version statements 1, 2 appear across the uploaded files…") and
   **Possible duplicates found** (`SR-OBJ-000032`, title similarity). Both appear as blocking questions
   with *why it matters* / *what resolves it*. *(08, 09)*
3. Confirm page requires *Which version governs?* and the *revision / distinct study* decision. *(10)*
   Submitting without them (client-side `required` removed) is **refused by the server**: "state which
   version governs before submitting". *(11)*
4. Researcher states "Version 2 … governs; v1 is an earlier version" and chooses *distinct study*. The
   statement is recorded as a researcher-statement evidence row and applied to the proposed source; no
   review case is needed for a resolved routine ambiguity. **Registered** as `SR-OBJ-000033`. *(12)*
   (Ambiguity the researcher declares unresolvable in the source form still opens an `ambiguous_source`
   review case — see `test_review_trigger_for_other_authors_attribution_and_no_accept_anyway` for the
   attribution case.)

## J3 — Repair and resubmission

1. Upload `j3-manuscript.pdf`; deliberately leave *scope* and *next burden* empty. Confirm page warns
   "2 blocking questions remain" but lets the researcher proceed. *(13)*
2. Engine decision **RETURNED_FOR_REPAIR** (`RCPT-000040`): status *Needs repair*; receipt lists exactly
   `scope is missing`, `next_burden is missing`. *(14)*
3. *Start repair* opens a new draft: **22 ready · 2 missing**, the two fields flagged *by receipt*, every
   other field showing *reused from revision r1*. Only the exact repair is typed. *(15)*
4. Resubmit → all seven gates run again → **ACCEPTED** (`RCPT-000041`) → **Registered** `SR-OBJ-000034`.
   History shows r1 and r2 with both receipts; the public record page lists both attempts, the current
   one being the acceptance for the registered version. *(16, 17)*

## J4 — Interruption after acceptance

1. An outage of the Git host is injected before submission. The engine still decides: **ACCEPTED**
   (`RCPT-000042`), status **Accepted — awaiting registration**, publication `queued`, and **no
   "Registered" is shown**. *(18)*
2. The outage ends; `manage.py reconcile --due` re-dispatches the publication job, which resumes from
   the observable Git state → merged → read back → **Registered** `SR-OBJ-000035`. Exactly one receipt
   exists for the revision; recovery never re-decided. *(19)*

## What the journeys show about assistance

* Repeated data entry is removed where extraction is reliable (title, abstract, version, publication
  hint, classifications) — J1 typed 14 of 24 fields; J3's repair typed 2 of 24.
* Uncertainty stays visible: every suggestion and metadata extraction is marked *uncertain* and keeps its
  origin row even after confirmation.
* Checks are not weakened: the seven gates decide every confirmed revision (J3's first revision was
  returned, not waved through); policy questions (version, duplicate, source type, claim layers) are
  enforced server-side; "Registered" appears only after verification on the default branch.

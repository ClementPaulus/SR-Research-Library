# Contributing to the Structura Reditus Research Library

This document gives the exact steps for working with the library. Nothing
here requires live explanation from the repository creator. The full
contract is in [LIBRARY_SPECIFICATION.md](LIBRARY_SPECIFICATION.md).

Ground rules that apply to every step:

- Do not fabricate metadata. When information is missing, preserve the gap in
  the `missingness` field and mark the record for repair. Do not guess. Do
  not silently reconcile inconsistent source data.
- Synthetic examples must be explicitly marked as synthetic (use
  `"synthetic": true` and provenance `synthetic-test-object`).
- Publication status, credentials, citation counts, and agreement with GCD
  carry no admission authority.
- Every author, including AUTH-0001, is held to the same admission gates.

## 1. Requesting or registering an AuthorID

The researcher portal assigns an AuthorID automatically after email
verification (see [docs/PORTAL_CONTRIBUTING.md](docs/PORTAL_CONTRIBUTING.md)).
For the direct route:

1. Reserve the identifier through the shared ledger instead of counting files:
   `python -m validators.reserve AUTH --purpose "author registration"` writes
   `registry/reservations/AUTH-NNNN.json`; commit it with the record. Never
   claim an existing AuthorID by matching a name, email, or ORCID — that needs
   maintainer-verified evidence.
2. Create `registry/authors/AUTH-NNNN.json` conforming to
   `schema/author.schema.json` with at least:
   - `author_id` — e.g. `AUTH-0002`
   - `display_name` — the author's public name
   - `status` — normally `active`
   - `registered` — the registration timestamp as ISO 8601 with an explicit
     time zone, e.g. `2026-09-12T21:48:30-05:00` or `2026-09-13T02:48:30Z`;
     date-only values are rejected because their time basis is ambiguous
   - `orcid` — only if the author actually has one; never invented
   - `credentials` — optional; each entry needs a `statement` and a
     `verification_state` (`unverified`, `self-declared`,
     `externally-verified`). Credentials are provenance metadata only.
3. Run `python -m validators.validate` and confirm no issues, then mark the
   reservation published:
   `python -m validators.reserve --publish AUTH-NNNN --record registry/authors/AUTH-NNNN.json`.
4. Regenerate the public projection (`python -m validators.build_site`); the
   author page and search index are part of the committed site.
5. Open a pull request adding the author record, the reservation entry, and the
   regenerated `site/`.

The AuthorID is stable for life; contribution history changes around it.

## 2. Preparing a research-object record

1. Reserve the identifier: `python -m validators.reserve SR-OBJ --purpose "<short purpose>"`
   (repeat for `SRC` and `REL`). Reserved values are never reused for different work.
2. Create a JSON file conforming to `schema/object.schema.json`. Every field
   listed as required in the schema must be present, including:
   - exactly one `tier2_class.primary` from `taxonomy/tier2_classes.yaml`
     (secondary classes optional);
   - `authority.tier` set to `tier-2` (the library registers Tier-2 records
     only);
   - controlled values for `domain.primary`, `structural_focus.primary`,
     `evidence_mode.primary`, `provenance`, `maturity`, `functional_locus`,
     and `publication_state` from their taxonomy files — free text never
     replaces controlled values;
   - `main_question` (one main question; others go in `secondary_questions`);
   - `claim_layers` entries with a declared `layer` so source observation
     stays distinct from local interpretation;
   - explicit `source_boundary`, `authority_boundary`, `scope`,
     `exclusions`, `preserved_meaning`, `missingness`,
     `distortion_or_substitution_risk`, `next_burden`, `repair_route`,
     `notes`;
   - `version` (`MAJOR.MINOR.PATCH`) and `date` (ISO 8601 timestamp with an
     explicit time zone, `YYYY-MM-DDThh:mm:ssZ` or `±HH:MM`).
3. Declare unknown or unavailable information in `missingness` with a
   missingness class; never fill gaps with guesses.
4. When revising an already-registered object, first preserve the current
   state to `registry/objects/history/` (see §8), then update the record with
   a bumped `version`.

## 3. Registering a source

1. Take the next free identifier in the `SRC-NNNNNN` namespace.
2. Create `registry/sources/SRC-NNNNNN.json` conforming to
   `schema/source.schema.json`:
   - `source_type: external` for work outside Structura Reditus,
     `corpus-native` for current corpus works, `historical` for
     prefreeze/lineage works, `dataset` for datasets;
   - `source_authors` — the original authors, exactly as attributable; never
     replaced by a library AuthorID;
   - `source_native_claims` — only claims the source itself makes, in its
     own terms; local interpretation belongs on your object's
     `claim_layers`, never here;
   - `identifier` — only supplied identifiers (DOI, URL, ISBN, archive
     reference); never guessed. For a DOI, set `identifier.url` to
     `https://doi.org/<doi>`;
   - `links` — labeled outbound resources (`canonical`, `archive`,
     `full_text`, `publisher`, `code`, `data`, `supplement`,
     `project_page`). Mark at most one `preferred: true` (normally the DOI
     resolver, label "Canonical DOI"). Add an archive landing page only when
     it is known or resolvable. Never guess full-text, code, data, or
     supplement URLs, and never commit PDFs — the paper stays on its
     platform;
   - `missingness` — every unavailable metadata item, preserved explicitly,
     including any title or DOI discrepancy observed in archive metadata.
3. Shared-archive DOIs: when one DOI anchors several member works, give each
   work its own `SRC-*`, record the shared condition in `notes` and as a
   `shared_archive` entry in `related_dois`, and never collapse them into one
   object or count them as separate deposits.
   Record lineage in the typed fields — `version`, `status`, `concept_doi`,
   `version_doi`, `related_dois` (`earlier_version`, `later_version`,
   `alternate_record`, `first_edition`, `external_metadata`, `software`),
   `supersedes` / `superseded_by` — rather than in `notes`. Source identity
   ≠ archive concept ≠ deposited version; a new version DOI alone never
   creates a new source or object. Only a genuinely unresolved identity
   question becomes a seam in `releases/open-seams.yaml` — never silently
   pick one DOI.
4. Never attribute a Structura Reditus or GCD interpretation to an external
   author unless the source actually makes that interpretation.

## 3a. Registering a governing reference

Governing references (`SR-GOV-*`) preserve canon-facing, constitutional,
authority-axis, functional-source, kernel-reference, protocol, specification,
publication-protocol, ingress, and language-contact works. They are not
research objects and never receive an `SR-OBJ-*` merely for visibility.

1. Register the source first (§3); the governing record's `source_id` must
   resolve.
2. Take the next free `SR-GOV-NNNNNN` and create the record under
   `registry/governing/<view>/` conforming to `schema/governing.schema.json`,
   where `<view>` is `tier-1/`, `tier-0/`, or `mixed/` according to which of
   `authority_scope.tier_1` / `tier_0` are non-empty (root if both are empty).
3. Describe the **exact admitted burden** from the source itself in
   `authority_scope`, `scope`, and `non_goal`. Never classify a whole
   document as Tier-1 or Tier-0 because it contains material at that level.
4. Use `status: candidate` for repair or adoption candidates and
   `status: unresolved` where sources disagree on role, version, DOI, or
   adoption status; record the disagreement in `missingness` and in
   `releases/open-seams.yaml`. Do not promote a candidate without an
   adoption record.
5. Record `doi` only when the source establishes it. Set `version` exactly as
   the source states it. `active_from` is a full ISO 8601 timestamp with time
   zone.
6. After release, never edit the record's meaning in place. To change active
   authority: add a new `SR-GOV-*` with `supersedes: <old>`, then set the
   old record's `superseded_by` and `status: superseded`. Keep the old file.
   `python -m validators.validate` enforces this.
7. On Tier-2 objects, list constraining references in `governing_refs`. This
   never transfers authority; `authority.tier` stays `tier-2`.

## 4. Declaring relations

1. Take the next free identifier in the `REL-NNNNNN` namespace.
2. Create `registry/relations/REL-NNNNNN.json` conforming to
   `schema/relation.schema.json` with a `relation_type` from
   `taxonomy/relation_types.yaml`, `from_id`/`to_id` referencing registered
   objects or sources, and a `declared` timestamp (ISO 8601 with an explicit
   time zone).
3. List the RelationID in the `relations` array of the object that declares
   it.
4. If a relation cannot yet be classified, use `unresolved_relation` rather
   than inventing a type. `challenges` and `contrasts_with` are ordinary
   relations — disagreement is not an admission failure.

## 5. Running validators locally

```
pip install -r requirements-dev.txt
python -m validators.validate    # all registry checks; exits non-zero on issues
python -m pytest tests/          # full test suite
```

The same checks run in CI (`.github/workflows/validate.yml`) on every pull
request and push to `main`; `main` should be protected as described in
[docs/MAIN_PROTECTION_RULESET.md](docs/MAIN_PROTECTION_RULESET.md).

## 6. Submitting work

1. Add your new files under `registry/` (author, sources, relations, object)
   together with their `registry/reservations/` entries.
2. Run the validators (§5) until clean.
3. Evaluate admission locally:
   `python -m validators.admit path/to/SR-OBJ-NNNNNN.json --write`
   stores the complete receipt bundle under `receipts/`: the `.json` and `.md`
   receipt, the exact submitted-record snapshot (`RCPT-NNNNNN.submission.json`)
   for every decision, and the companion execution manifest
   (`receipts/executions/RCPT-NNNNNN.execution.json`). Add
   `--source-file PATH` to record manuscript/data hashes (the files themselves
   never enter Git) and `--register` to place an ACCEPTED record into
   `registry/objects/` (any previously registered version is archived to
   `registry/objects/history/` first; the reservation is marked published).
4. Regenerate the public projection: `python -m validators.build_site`.
5. Open a pull request containing the registry files, reservation entries, the
   receipt bundle, and the regenerated `site/`. The default branch requires the
   `validate` check and an up-to-date base.

## 7. Interpreting admission receipts

- `ACCEPTED` — all seven gates (A–G) passed; only non-blocking missingness
  remains. Admission means organizational conformance only: not truth, not
  endorsement, not Tier-0 adoption, not Tier-1 admission.
- `RETURNED_FOR_REPAIR` — structure is missing or incomplete. The receipt
  lists the blocked gates, exact missing structure, the exact repair
  required, fields already accepted, fields still blocked, and the exact
  resubmission condition. This is not a rejection.
- `REJECTED` — an evaluable gate failed because the record violates the
  library contract (for example, a non-Tier-2 authority claim or an
  uncontrolled taxonomy value). The receipt states the established violation
  and the resubmission conditions. Rejection does not establish that the
  underlying research claim is false.

## 8. Repairing and resubmitting

1. Read the `exact_repair_required` list on the repair receipt.
2. Supply exactly the missing structure — from actual records, never
   invented. If information genuinely does not exist, declare it in
   `missingness` with the appropriate class.
3. If the repair changes the object's identity (the receipt says a new
   ObjectID is required), register a new object and relate it to the old one
   (`supersedes` / `derived_from`); otherwise keep the same ObjectID.
4. When revising a registered object, preserve the previous state first:
   ```
   python -c "import json; from validators import loader; \
   loader.archive_object_version(json.load(open('registry/objects/SR-OBJ-NNNNNN.json')))"
   ```
   then bump `version` and edit the record. Historical states are never
   rewritten.
5. Re-run the validators and admission evaluation; resubmit. All seven gates
   are re-evaluated in full, with no penalty for the earlier return.

## 9. Proposing taxonomy changes

1. Record the proposal in `taxonomy/extensions.yaml` with the next `EXT-NNNN`
   id: term, taxonomy, definition, why existing terms are insufficient,
   nearest existing terms, examples, ambiguity risk, backward-compatibility
   effect, and `decision: proposed`.
2. Open a pull request that edits the relevant `taxonomy/*.yaml` file:
   - **Adding a term**: append `id`, `label`, and an optional `description`,
     and set the extension record to `decision: accepted` with
     `version_introduced`.
   - **Deprecating a term**: keep the term in place and add a
     `description` note marking it deprecated and naming its replacement.
     Terms are never silently removed or redefined, because historical
     records reference them.
3. Bump `taxonomy/VERSION` (e.g. `SR-TAXONOMY.v0.2.0` → `SR-TAXONOMY.v0.3.0`).
4. Run `python -m pytest tests/` — existing registry records must still
   validate, and every `accepted` extension must be present in its taxonomy.
5. Taxonomy changes are recorded in release manifests; they are part of the
   library's preserved history.

## 10. Recording open seams

When a contract decision cannot yet be closed, add a `SEAM-NNNN` entry to
`releases/open-seams.yaml` (area, description, `status: open`). When it is
closed, set `status: closed` in place; seams are never deleted. Seams are
copied into the next release manifest.

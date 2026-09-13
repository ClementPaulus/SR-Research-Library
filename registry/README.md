# Registry

The registry is the source of truth for the Structura Reditus Research
Library. Every tool (validators, admission gates, receipts, profiles, release
manifests, site generation) reads from here; nothing maintains a competing
database.

| Directory | Contents | Identifier namespace | Schema |
|---|---|---|---|
| `authors/` | stable author entities | `AUTH-NNNN` | `schema/author.schema.json` |
| `governing/` | governing references with exact admitted burden; `tier-1/`, `tier-0/`, `mixed/` are organizational views chosen by `authority_scope` (records with no Tier-1/Tier-0 burden sit at the root) | `SR-GOV-NNNNNN` | `schema/governing.schema.json` |
| `objects/` | Tier-2 research objects (current state) — exclusively Tier-2 | `SR-OBJ-NNNNNN` | `schema/object.schema.json` |
| `objects/history/` | preserved previous object versions (`SR-OBJ-NNNNNN.vX.Y.Z.json`) | — | `schema/object.schema.json` |
| `sources/` | source / archive records: DOI, archive, labeled outbound `links` | `SRC-NNNNNN` | `schema/source.schema.json` |
| `relations/` | typed, directional relations | `REL-NNNNNN` | `schema/relation.schema.json` |

Records may be written as `.json` or `.yaml`; one record per file, named by
its identifier. Identifiers are allocated sequentially and are never reused.
They encode no prestige, rank, truth, or importance.

The three identities are independent: a work may have an `SRC-*` and an
`SR-GOV-*` record and no `SR-OBJ-*` (governing works), or an `SRC-*` and an
`SR-OBJ-*` and no `SR-GOV-*` (domain research). A source is never relabeled
as Tier-2 research to make it searchable; it is searchable as a source.

## Sources and external links

The library is a thin registry and external scholarly index. A source record
stores identity, metadata, source-native claims, and labeled outbound `links`
(`canonical`, `archive`, `full_text`, `publisher`, `code`, `data`,
`supplement`, `project_page`). The paper itself stays on its DOI/archive
platform; PDFs are never stored or mirrored here.

- At most one link per source is `preferred`; for DOI-bearing works this is
  normally the DOI resolver (`https://doi.org/<doi>`, label "Canonical DOI").
- Add an archive landing page only when it is known or resolvable; never
  guess full-text, code, data, or supplement URLs.
- A DOI may anchor several member works (shared-archive DOI). Each member
  keeps its own `SRC-*`; record the shared condition in `notes` and as a
  `shared_archive` entry in `related_dois`.
- Alternate, earlier, or disputed DOIs are typed entries in `related_dois`
  (see *Source lineage* below); only genuinely unresolved identity questions
  go to `releases/open-seams.yaml`. Nothing is silently reconciled.
- Link failure never deletes a source. DOI identity survives a broken link.

### Source lineage (source identity ≠ archive concept ≠ deposited version)

Every source may carry typed lineage instead of pushing DOI history into
`notes`/`missingness`:

| Field | Meaning |
|---|---|
| `version` | version/edition exactly as the source states it, or `null` |
| `status` | `active` (current state of the named work), `superseded` (see `superseded_by`), `historical` (prefreeze/lineage witness) |
| `concept_doi` | archive concept DOI (resolves to the latest deposited version) |
| `version_doi` | DOI of the specific deposited version this record refers to |
| `related_dois[]` | other observed DOIs, each typed: `earlier_version`, `later_version`, `alternate_record`, `shared_archive`, `first_edition`, `external_metadata`, `software`, `other` |
| `supersedes[]` / `superseded_by` | append-preserving supersession between source records |

`identifier.doi` (the anchoring DOI) must equal `concept_doi` or
`version_doi` when either is set; concept and version DOIs are never
collapsed; a superseded source stays in the registry with `status:
superseded` and `superseded_by` set. `check_source_lineage` enforces this.

### Reserved identifiers

An ObjectID named on a RETURNED_FOR_REPAIR or REJECTED receipt stays
reserved for that submission (its receipt and archived submission are
historical identity). It is registered only by re-admitting the same work;
it is never reassigned. `SR-OBJ-000017` and `SR-OBJ-000019` returned under
their reserved identities in the 2026-09 census pass (RCPT-000023,
RCPT-000024; the earlier repair receipts are preserved). Currently reserved
and still blocked: `SR-OBJ-000016` (SEAM-0011). The next free identifiers are
therefore `SR-OBJ-000031`, `SRC-000060`, `SR-GOV-000020`, `REL-000006`,
`RCPT-000036`. Recalculate from the live tree before allocating; see
[docs/TIER2_CENSUS_2026-09.md](../docs/TIER2_CENSUS_2026-09.md) for the
census readback and [LIBRARY_SPECIFICATION.md §6.1](../LIBRARY_SPECIFICATION.md)
for the Tier-2 admission decision rule.

## Governing references

A governing record (`governing/`) carries the source's exact admitted
burden in `authority_scope.tier_1` / `tier_0`. Never classify a whole
document as Tier-1 or Tier-0 because it contains material at that level;
describe the burden the source admits. `status` is one of `active`,
`superseded`, `historical`, `candidate`, `unresolved` — use `candidate` for
repair/adoption candidates and `unresolved` where the sources disagree on
role, version, DOI, or adoption status. DOIs are recorded only when the
source establishes them.

Once a governing record appears in a release manifest it is immutable: only
`status` and `superseded_by` may change. To change active authority, add a
new `SR-GOV-*` with `supersedes` pointing at the old record, set the old
record's `superseded_by` and `status: superseded`, and keep the old file.
`python -m validators.validate` enforces this against
`governing_immutable_hashes` in the release manifests.

Tier-2 objects may list `governing_refs`. This means "these references
constrain the record"; it never transfers their authority —
`authority.tier` stays `tier-2`.

## Adding a work

1. Register any new author (`authors/`), source (`sources/`), and relation
   (`relations/`) records the work depends on.
2. Prepare the object record (see [CONTRIBUTING.md](../CONTRIBUTING.md) §2).
3. Evaluate admission and, if ACCEPTED, register it in one step:

   ```
   python -m validators.admit path/to/SR-OBJ-NNNNNN.json --write --register
   ```

   `--write` stores the receipt under `receipts/`; `--register` copies an
   ACCEPTED record into `objects/` (archiving any previous version to
   `objects/history/` first). Records that are RETURNED_FOR_REPAIR or
   REJECTED are never registered; their submissions are archived for audit
   beside their receipts as `receipts/repair/RCPT-NNNNNN.submission.json`.
4. Run `python -m validators.validate`, then regenerate the public projection
   with `python -m validators.build_site`.

Do not edit the generated views in `site/` as source data; regenerate them
from the registry.

Bridge candidates in `site/data/bridge_candidates.json` are generated retrieval
and review projections. They are not `REL-*` records and never become part of
the registry source of truth automatically.

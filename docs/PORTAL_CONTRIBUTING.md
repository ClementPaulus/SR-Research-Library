# Contributing through the Portal or the Repository

Two routes, one contract: the same schemas, taxonomies, admission engine, identifier reservations,
receipts, and preservation rules. Ordinary contributors never need a GitHub account, Codespaces, a
terminal, identifier allocation, or JSON editing.

## Researcher guide (portal)

1. **Sign up once.** *Create your profile* → display name, email, password, accept the published terms.
   Verify the email link. Your public AuthorID is assigned automatically through the library's shared
   reservation ledger; you can start a draft while it publishes. Opened the link in a different browser?
   *Log in* there — never create a second account.
2. **Return to your workspace.** `/workspace/` shows *My submissions*, *Requested actions*, *Registered
   works*, and your profile. Changing your display name never changes your AuthorID.
3. **Upload research.** PDF, DOCX, Markdown, text, LaTeX, JSON/YAML records, CSV/TSV, or a ZIP handoff
   (50 MiB per file, 200 MiB per submission), or supply a DOI/archive reference/URL instead.
   *“Your files are saved. We’re preparing a draft for your review.”* The status page shows the six
   preparation steps as they run: preserve files → identify source and version information → check for
   possible duplicates → extract metadata → propose library classifications → prepare the editable
   submission. If a step fails, your upload is kept and the step is retried.
4. **Review the prepared draft.** The readiness panel says what is *ready*, what *needs confirmation*, and
   what is *missing*. Each field shows where its value came from — extracted from a file (with page/line),
   a library-classification suggestion (keyword-based, always marked uncertain), or stated by you. Only the
   questions still open are asked, each with *why it matters*, whether it *blocks submission*, and *what
   resolves it*. Keeping an extracted or suggested value and pressing **Save draft** records it as confirmed
   — you never retype what the system already found. Gaps go in *Missingness* with a class; nothing is
   guessed for you. Autosave protects against lost edits; two tabs never overwrite each other.
5. **Submit.** *“Submit this revision to the public research library.”* If two manuscript versions were
   found you state which governs; if a possible duplicate object was found you decide *revision of it* or
   *distinct study*; if the proposed source's type is uncertain you confirm it; and you confirm the layer of
   each claim (source observations belong to the source; interpretations are yours). The exact public scope
   is shown beside the button. The revision is frozen and evaluated by the seven gates in isolation.
6. **Read the receipt.** ACCEPTED → *Registration is in progress* → **Registered** with links to the
   public record, receipt, and commit. RETURNED_FOR_REPAIR → *“This submission needs additional
   information. Your files and earlier version are preserved.”* → *Start repair* creates a linked new
   revision. REJECTED → the receipt names the contract violation and the resubmission route.
7. **Ask.** Questions attach to the current revision and keep a resolved/unresolved thread. Source-only
   suggestions and relation proposals are never counted as your authored research.
8. **Export.** Any frozen revision downloads as a versioned handoff ZIP (owner or public-safe).

Boundary: *Library admission confirms that the record meets the organizational requirements. It does
not certify the scientific claims.*

## Direct repository route (Codespaces / clone / PR)

1. **Identity.** Existing contributors keep their AuthorID. New direct contributors open the
   *Author registration (direct route)* issue form, or reserve locally:
   `python -m validators.reserve AUTH --purpose "author registration"` and commit
   `registry/reservations/AUTH-NNNN.json` with `registry/authors/AUTH-NNNN.json`.
   Claiming an existing identity requires maintainer-verified evidence; matching a name is never enough.
2. **Search for duplicate work** (`/research`, `site/search.html`, or `site/data/search_index.json`):
   check existing objects, sources, lineage, shared archives, and repair receipts.
3. **Reserve identifiers** for every new record:
   `python -m validators.reserve SR-OBJ --purpose "…" --operation-key <uuid>` (repeat for SRC/REL).
   The same operation key returns the same value on retry.
4. **Prepare sources and the record** per [CONTRIBUTING.md](../CONTRIBUTING.md) §2–§4, using the
   reserved IDs. Source authors stay exactly as stated; external claims stay source-native.
5. **Evaluate and preserve.**
   `python -m validators.admit path/to/SR-OBJ-NNNNNN.json --write [--source-file manuscript.pdf]`
   writes the receipt, the exact submission snapshot, and the execution manifest under `receipts/`.
   Add `--register` only for an ACCEPTED record; it also marks the reservation `published`.
6. **Validate and regenerate.** `python -m validators.validate` then `python -m validators.build_site`
   (the author-only instruction now includes regenerated projections too).
7. **Open a PR** containing registry files, reservation ledger entries, the receipt bundle, and
   regenerated `site/`. CI runs `validate`; the default branch requires it plus an up-to-date base.
   PRs proposing unreserved identifiers are brought into the ledger before merge.

Repair: read `exact_repair_required` on the repair receipt, supply exactly that structure from actual
records, re-run step 5 (a new receipt; the old one stays). Revising a registered object: bump `version`
— `admit --register` archives the previous state to `registry/objects/history/` automatically.

## Reviewers and maintainers

`/review/` lists open review cases (identity claims, ambiguous source versions, attribution, relations
without evidence, taxonomy/governing changes, publication exceptions), blocked publications with their
exact blocker, and stopped jobs. A reviewer resolves inputs or returns the draft with the requested
evidence; the engine alone decides, on a distinct attempt. Controversy, disagreement, negative results,
and the founder's identity are never review triggers.

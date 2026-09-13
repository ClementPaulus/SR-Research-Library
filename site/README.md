# Public library projection

Everything in this directory is generated from `registry/` and `receipts/`
(the sources of truth) by:

```
python -m validators.build_site
```

Do not edit these files by hand; regenerate them after any registry change.
CI fails if the committed site differs from a fresh regeneration.

## Three entry surfaces

The navigation keeps three registries visibly distinct:

- **Governing References** (`governing/`) — `SR-GOV-*` records with title,
  source ID, version, status, exact admitted burden, authority scope,
  canonical DOI/archive link, supersession history, missingness, and linked
  Tier-2 objects. Filter chips: Tier-1-bearing, Tier-0-bearing, mixed, each
  governing role, and each status.
- **Tier-2 Research** (`objects/`) — `SR-OBJ-*` records with classification,
  boundaries, claim layers, missingness, sources (with labeled external
  links), governing references, relations, preserved versions, and the
  admission receipt.
- **Sources & Archives** (`sources/`, `sources/historical.html`) — `SRC-*`
  records with DOI/archive identity, labeled outbound links, source-native
  claims, and missingness. A source page states whether a Tier-2 object
  exists for it; source-only governing works are never shown with a Tier-2
  classification.

Plus `authors/`, `receipts/`, `relations/`, `timeline/`, `questions/`, and per-axis views
`domains/`, `focus/`, `classes/`, `evidence/`, `maturity/`.

- `data/*.json` — registry, governing, receipt, profile, and taxonomy
  projections (`profiles.json` holds only reconstructible quantities; no
  author score). `bridge_candidates.json` is a rebuildable retrieval projection,
  not registry source data.

## Connectivity levels

The Library keeps three connectivity levels distinct:

1. **Retrieval adjacency** — generated from shared registered structure.
2. **Candidate relation** — a generated, explainable connection suggested for review.
3. **Declared relation** — a durable, human-reviewed `REL-*` record.

`retrieval adjacency != candidate relation != declared relation`.
Generated bridge candidates are projections and are not part of the immutable
research registry. They do not establish scientific equivalence, shared
mechanism, causation, support, contradiction, reproduction, extension, or
authority transfer.

## Retrieval axes

The projection supports browsing and filtering by author, domain, subdomain
(secondary domain), object of study, structural focus, main question, Tier-2
class, evidence mode, provenance, maturity, relation, source, and date.

## Route families (generation contract)

- `/governing/<SR-GOV>`
- `/authors/<AuthorID>`
- `/objects/<ObjectID>`
- `/sources/<SourceID>`
- `/receipts/<ReceiptID>`
- `/relations/`
- `/domains/<slug>`, `/focus/<slug>`, `/classes/<slug>`, `/evidence/<slug>`, `/maturity/<slug>`
- `/timeline/`
- `/questions/<slug>` — one page per normalized main question. Slug policy (SEAM-0007, closed): lower-case, Unicode normalized to ASCII, runs of non-alphanumerics → `-`, trimmed, truncated to 80 characters at a word boundary; questions that normalize identically share a page. The slug is a navigation key; the canonical question text lives on the object record.

Cross-domain retrieval follows
`FIND -> COMPARE -> EXTRACT TRANSFERABLE STRUCTURE -> REINSTANTIATE LOCALLY -> VALIDATE LOCALLY`.
Thresholds, adapters, closure gates, evidence standards, causal claims,
ontological claims, and source authority are never transferred automatically.

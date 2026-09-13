# Public library projection

Everything in this directory is generated from `registry/` (the source of
truth) by:

```
python -m validators.build_site
```

Do not edit these files by hand; regenerate them after any registry change.

- `index.html` — browsable, filterable view of research objects, authors,
  and sources.
- `data/authors.json`, `data/objects.json`, `data/sources.json`,
  `data/relations.json` — registry projections.
- `data/profiles.json` — author profiles computed from registered object
  metadata only (reconstructible quantities; no author score).
- `data/taxonomies.json` — the controlled taxonomies in force.

## Retrieval axes

The projection supports browsing and filtering by author, domain, subdomain
(secondary domain), object of study, structural focus, main question, Tier-2
class, evidence mode, provenance, maturity, relation, source, and date.

## Route families (generation contract)

Per-entity and per-axis pages are an open seam (see
`releases/open-seams.yaml`). When built, they follow these route families:

- `/authors/<AuthorID>`
- `/objects/<ObjectID>`
- `/sources/<SourceID>`
- `/relations/<RelationID>`
- `/domains/<slug>`
- `/focus/<slug>`
- `/questions/<slug>`
- `/evidence/<slug>`
- `/maturity/<slug>`
- `/timeline/`

Cross-domain retrieval follows
`FIND -> COMPARE -> EXTRACT TRANSFERABLE STRUCTURE -> REINSTANTIATE LOCALLY -> VALIDATE LOCALLY`.
Thresholds, adapters, closure gates, evidence standards, causal claims,
ontological claims, and source authority are never transferred automatically.

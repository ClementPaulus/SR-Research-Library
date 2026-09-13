# Registry

The registry is the source of truth for the Structura Reditus Research
Library. Every tool (validators, admission gates, receipts, profiles, release
manifests, site generation) reads from here; nothing maintains a competing
database.

| Directory | Contents | Identifier namespace | Schema |
|---|---|---|---|
| `authors/` | stable author entities | `AUTH-NNNN` | `schema/author.schema.json` |
| `objects/` | Tier-2 research objects (current state) | `SR-OBJ-NNNNNN` | `schema/object.schema.json` |
| `objects/history/` | preserved previous object versions (`SR-OBJ-NNNNNN.vX.Y.Z.json`) | — | `schema/object.schema.json` |
| `sources/` | external and internal source records | `SRC-NNNNNN` | `schema/source.schema.json` |
| `relations/` | typed, directional relations | `REL-NNNNNN` | `schema/relation.schema.json` |

Records may be written as `.json` or `.yaml`; one record per file, named by
its identifier. Identifiers are allocated sequentially and are never reused.
They encode no prestige, rank, truth, or importance.

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
   REJECTED are never registered.
4. Run `python -m validators.validate`, then regenerate the public projection
   with `python -m validators.build_site`.

Do not edit the generated views in `site/` as source data; regenerate them
from the registry.

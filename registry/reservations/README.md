# Identifier reservation ledger (SR-RESERVATION.v0.1.0)

`registry/reservations/<value>.json` is the additive identifier ledger governed by
`schema/reservation.schema.json`. It is infrastructure, not a fourth registry surface: entries carry no
research content, are excluded from `loader.load_registry`, and are validated by `check_reservations`
(`python -m validators.validate`). States are `reserved`, `published` (record committed), or
`withdrawn` (never reused).

Do not recalculate "the next free number" by hand from the live tree. Reserve through the shared
allocator, which reconciles committed records, `objects/history/`, receipts and the identities they
name, `.submission.json` snapshots, and this ledger:

```
python -m validators.reserve SR-OBJ --purpose "new research object family" [--operation-key <uuid>]
python -m validators.reserve --publish SR-OBJ-000032 --record registry/objects/SR-OBJ-000032.json
python -m validators.reserve --next SRC
```

The portal reserves automatically and publishes ledger entries through the same protected pull-request
path as records. See [docs/IDENTIFIERS.md](../../docs/IDENTIFIERS.md).

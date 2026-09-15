# Admission Receipts

Every object evaluation produces one of three receipts:

- `ACCEPTED`: organizational contract satisfied.
- `RETURNED_FOR_REPAIR`: blocking structure is incomplete but repairable.
- `REJECTED`: an evaluable active contract gate fails.

Receipts state the gate, missingness or violation class, reason, and repair route. A receipt is not a truth verdict on the underlying research.

Receipts live under `receipts/accepted/`, `receipts/repair/`, and `receipts/rejected/` as `RCPT-NNNNNN.json` (machine-readable) and `RCPT-NNNNNN.md` (human-readable). The exact submitted record is archived beside its receipt as `RCPT-NNNNNN.submission.json` for **every** decision (accepted included, from `RCPT-000038` onward; historical accepted receipts `RCPT-000001..000037` predate this and are unchanged). A non-accepted submission is never placed in `registry/objects/`. A revised object that is re-admitted receives a new receipt; earlier receipts are kept.

## Execution manifests (SR-EXECUTION.v0.1.0)

Each receipt from `RCPT-000038` onward has a companion `receipts/executions/RCPT-NNNNNN.execution.json`
(`schema/execution.schema.json`) binding the decision to its inputs: the canonical SHA-256 of the evaluated
record, the preserved snapshot path, original source-file hashes (never the binaries), the engine revision,
schema and taxonomy versions, the registry base commit, the evaluation time, per-gate results, the route
(`cli` or `portal`), the public operation key, any resolved review condition, and the earlier attempt it
follows. The manifest never contains the SHA of the commit that carries it; publication is bookkept
separately. `validators.execution.verify_manifest_against_snapshot` checks a manifest against its snapshot
and receipt. `loader.load_receipts` never loads snapshots or manifests as receipts.

## Immutability

Bundles are written atomically through a staging directory (`validators.receipts.write_receipt_bundle`).
An existing receipt ID is never overwritten with different content (`ReceiptConflict`); repeating the same
operation recovers the stored bundle. A corrected receipt is a new receipt whose manifest names the earlier
one in `supersedes_attempt`. Receipt numbers are reserved through the identifier ledger; a number whose
attempt is abandoned is withdrawn and never reissued. Draft previews allocate no receipt.

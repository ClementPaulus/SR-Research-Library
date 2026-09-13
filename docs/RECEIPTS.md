# Admission Receipts

Every object evaluation produces one of three receipts:

- `ACCEPTED`: organizational contract satisfied.
- `RETURNED_FOR_REPAIR`: blocking structure is incomplete but repairable.
- `REJECTED`: an evaluable active contract gate fails.

Receipts state the gate, missingness or violation class, reason, and repair route. A receipt is not a truth verdict on the underlying research.

Receipts live under `receipts/accepted/`, `receipts/repair/`, and `receipts/rejected/` as `RCPT-NNNNNN.json` (machine-readable) and `RCPT-NNNNNN.md` (human-readable). A non-accepted submission is archived for audit beside its receipt as `RCPT-NNNNNN.submission.json`; it is never placed in `registry/objects/`. A revised object that is re-admitted receives a new receipt; earlier receipts are kept.

# Examples (all synthetic)

Everything in this directory is **synthetic** and explicitly marked as such.
No scholarly facts are asserted. These files exist only to demonstrate the
submission format and the three admission outcomes; nothing here is
registered in `registry/` (the source of truth), and the receipt IDs used
here (RCPT-000001–RCPT-000003) belong to this example set, not to the live
`receipts/` sequence.

- `submissions/example-accepted.json` — a structurally complete synthetic
  submission → `receipts/accepted/RCPT-000001.{json,md}` (ACCEPTED).
- `submissions/example-returned-for-repair.json` — the same submission with
  its `main_question` missing → `receipts/repair/RCPT-000002.{json,md}`
  (RETURNED_FOR_REPAIR).
- `submissions/example-rejected.json` — the same submission claiming
  non-Tier-2 authority → `receipts/rejected/RCPT-000003.{json,md}`
  (REJECTED).

Regenerate a receipt for any submission with:

```
python -m validators.admit examples/submissions/example-accepted.json
```

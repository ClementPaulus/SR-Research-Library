# Contributing to the Structura Reditus Research Library

## Principles

- Preserve Tier boundaries exactly.
- Admission is organizational conformance, not truth endorsement.
- Use controlled taxonomies for primary classification fields.
- Preserve provenance and external authorship.
- Never silently overwrite historical states.

## Taxonomy extension process

Any taxonomy extension proposal must include:

- Term proposed
- Taxonomy
- Definition
- Reason existing terms are insufficient
- Nearest existing terms
- Examples
- Ambiguity risk
- Backward-compatibility effect
- Decision
- Version introduced

Use `taxonomy/extensions.yaml` to record proposals and outcomes.

## Validation workflow

Run before submitting changes:

```bash
python3 validators/run_validators.py
python3 -m unittest discover -s tests -v
```

## Submission and admission

Follow the review order defined in `LIBRARY_SPECIFICATION.md`.

Do not fabricate unavailable research-object metadata. When required fields are unavailable, declare missingness and use `RETURNED_FOR_REPAIR`.

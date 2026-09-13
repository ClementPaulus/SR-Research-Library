"""Receipt generation for the Structura Reditus Research Library.

Every admission decision generates a human-readable (Markdown) and a
machine-readable (JSON) receipt. Receipts state explicitly what the decision
does and does not mean:

  * Library admission means organizational conformance only. It does not imply
    scientific truth, endorsement, Tier-0 adoption, or Tier-1 admission.
  * Rejection concerns library admission only. It does not by itself establish
    that the underlying research claim is false.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import loader
from .gates import GateEvaluation

ACCEPTED_DISCLAIMER = (
    "Library admission means organizational conformance only. It does not imply "
    "scientific truth, endorsement, Tier-0 adoption, or Tier-1 admission."
)

REPAIR_DISCLAIMER = (
    "RETURNED_FOR_REPAIR is not a rejection. Required structure is missing or "
    "incomplete, the gap blocks admission, and the same object can return through "
    "the declared repair. Library admission means organizational conformance only "
    "and does not imply scientific truth, endorsement, Tier-0 adoption, or Tier-1 "
    "admission."
)

REJECTED_DISCLAIMER = (
    "This rejection concerns library admission only: the submitted record violates "
    "the active library contract. It does not by itself establish that the "
    "underlying research claim is false. Library admission means organizational "
    "conformance only and does not imply scientific truth, endorsement, Tier-0 "
    "adoption, or Tier-1 admission."
)

DECISION_DIRS = {
    "ACCEPTED": "accepted",
    "RETURNED_FOR_REPAIR": "repair",
    "REJECTED": "rejected",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def next_receipt_id(receipts_dir: Path = None) -> str:
    receipts_dir = receipts_dir or loader.RECEIPTS_DIR
    pattern = re.compile(r"RCPT-([0-9]{6})")
    highest = 0
    for subdir in DECISION_DIRS.values():
        directory = receipts_dir / subdir
        if not directory.is_dir():
            continue
        for path in directory.iterdir():
            match = pattern.search(path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return f"RCPT-{highest + 1:06d}"


def _gates_payload(evaluation: GateEvaluation) -> dict:
    return {
        key: {
            "name": gate.name,
            "result": gate.result,
            "detail": "; ".join(gate.details) if gate.details else "",
        }
        for key, gate in evaluation.gates.items()
    }


def build_receipt(record: dict, evaluation: GateEvaluation, receipt_id: str = None,
                  generated: str = None) -> dict:
    """Build the machine-readable receipt for an admission decision."""
    receipt_id = receipt_id or next_receipt_id()
    generated = generated or _now_iso()
    decision = evaluation.decision
    submission_identity = record.get("object_id") or record.get("title") or "<unidentified submission>"

    receipt = {
        "receipt_id": receipt_id,
        "decision": decision,
        "submission_identity": submission_identity,
        "generated": generated,
        "gates": _gates_payload(evaluation),
    }

    if decision == "ACCEPTED":
        receipt.update({
            "disclaimer": ACCEPTED_DISCLAIMER,
            "object_id": record.get("object_id"),
            "title": record.get("title"),
            "author_ids": record.get("authors", []),
            "version": record.get("version"),
            "date": record.get("date"),
            "authority": (record.get("authority") or {}).get("tier"),
            "tier2_class_primary": (record.get("tier2_class") or {}).get("primary"),
            "functional_locus": record.get("functional_locus"),
            "domain_primary": (record.get("domain") or {}).get("primary"),
            "structural_focus_primary": (record.get("structural_focus") or {}).get("primary"),
            "main_question": record.get("main_question"),
            "evidence_mode_primary": (record.get("evidence_mode") or {}).get("primary"),
            "provenance": record.get("provenance"),
            "maturity": record.get("maturity"),
            "source_ids": record.get("source_ids", []),
            "relation_ids": record.get("relations", []),
            "publication_state": record.get("publication_state"),
            "non_blocking_missingness": list(evaluation.missingness_notes),
            "open_burdens": [record.get("next_burden")] if record.get("next_burden") else [],
            "next_burden": record.get("next_burden"),
        })
    elif decision == "RETURNED_FOR_REPAIR":
        blocked = evaluation.blocked_gates + evaluation.failed_gates
        missing_structure = [d for g in blocked for d in g.details]
        receipt.update({
            "disclaimer": REPAIR_DISCLAIMER,
            "provisional_object_id": record.get("object_id"),
            "author_ids": record.get("authors", []),
            "version": record.get("version"),
            "failed_or_blocked_gates": [f"Gate {g.gate}: {g.name}" for g in blocked],
            "missing_structure": missing_structure,
            "missingness_class": "REPAIRABLE",
            "affected_burden": record.get("next_burden"),
            "why_blocked": (
                "Required structure is missing or incomplete and the gap blocks "
                "admission evaluability; the same object can reasonably return "
                "through the declared repair."
            ),
            "exact_repair_required": [f"Supply or correct: {d}" for d in missing_structure],
            "permitted_source_or_evidence": (
                "Any source or evidence mode permitted by the controlled taxonomies; "
                "missing metadata must be supplied from actual records, never invented."
            ),
            "repair_changes_object": False,
            "new_object_id_required": False,
            "seam_declaration_required": any(
                (m.get("class") == "UNRESOLVED_SEAM")
                for m in (record.get("missingness") or [])
                if isinstance(m, dict)
            ),
            "fields_already_accepted": _accepted_fields(record, evaluation),
            "fields_still_blocked": missing_structure,
            "resubmission_condition": (
                "Resubmit the same object with every listed missing structure supplied; "
                "all seven gates are then re-evaluated in full."
            ),
        })
    else:  # REJECTED
        failed = evaluation.failed_gates
        violations = [d for g in failed for d in g.details]
        receipt.update({
            "disclaimer": REJECTED_DISCLAIMER,
            "failed_gates": [f"Gate {g.gate}: {g.name}" for g in failed],
            "established_violation": "; ".join(violations),
            "violation_class": "CONTRACT_VIOLATING",
            "why_not_permitted": (
                "An evaluable admission gate failed because the submitted object "
                "violates the active library contract."
            ),
            "repairable_same_object": False,
            "new_object_version_or_seam_required": (
                "A corrected record must be submitted as a new version (or, if the "
                "violation changes the object's identity, as a new object with a "
                "declared seam)."
            ),
            "resubmission_conditions": (
                "Remove every listed contract violation; resubmission is then "
                "evaluated by the same seven gates with no penalty for the prior "
                "rejection."
            ),
        })
    return receipt


def _accepted_fields(record: dict, evaluation: GateEvaluation) -> list:
    accepted = []
    field_gate = {
        "object_id": "A", "title": "A", "authors": "A",
        "authority": "B",
        "provenance": "C", "source_ids": "C", "source_boundary": "C",
        "tier2_class": "D", "domain": "D", "structural_focus": "D",
        "evidence_mode": "D", "maturity": "D", "functional_locus": "D",
        "publication_state": "D", "main_question": "D",
        "authority_boundary": "E", "scope": "E", "missingness": "E",
        "relations": "F",
        "version": "G", "date": "G", "next_burden": "G", "repair_route": "G",
    }
    for field_name, gate_key in field_gate.items():
        value = record.get(field_name)
        present = value is not None and (not isinstance(value, str) or value.strip())
        if present and evaluation.gates[gate_key].result == "PASS":
            accepted.append(field_name)
    return accepted


def render_receipt_markdown(receipt: dict) -> str:
    """Render the human-readable receipt."""
    lines = [
        f"# Admission Receipt {receipt['receipt_id']}",
        "",
        f"Decision: {receipt['decision']}",
        f"Submission identity: {receipt['submission_identity']}",
        f"Generated: {receipt['generated']}",
        "",
    ]
    decision = receipt["decision"]
    if decision == "ACCEPTED":
        lines += [
            f"ObjectID: {receipt.get('object_id')}",
            f"Title: {receipt.get('title')}",
            f"AuthorID(s): {', '.join(receipt.get('author_ids', []))}",
            f"Version: {receipt.get('version')}",
            f"Date: {receipt.get('date')}",
            f"Authority: {receipt.get('authority')}",
            f"Primary Tier-2 class: {receipt.get('tier2_class_primary')}",
            f"Functional locus: {receipt.get('functional_locus')}",
            f"Primary domain: {receipt.get('domain_primary')}",
            f"Structural focus: {receipt.get('structural_focus_primary')}",
            f"Main question: {receipt.get('main_question')}",
            f"Evidence mode: {receipt.get('evidence_mode_primary')}",
            f"Provenance: {receipt.get('provenance')}",
            f"Maturity: {receipt.get('maturity')}",
            f"SourceIDs: {', '.join(receipt.get('source_ids', [])) or '(none)'}",
            f"RelationIDs: {', '.join(receipt.get('relation_ids', [])) or '(none)'}",
            f"Publication state: {receipt.get('publication_state')}",
            "",
        ]
        for key in "ABCDEFG":
            lines.append(f"Gate {key}: {receipt['gates'][key]['result']}")
        lines += [
            "",
            "Non-blocking missingness: "
            + ("; ".join(receipt.get("non_blocking_missingness", [])) or "(none declared)"),
            "Open burdens: " + ("; ".join(receipt.get("open_burdens", [])) or "(none declared)"),
            f"Next burden: {receipt.get('next_burden')}",
        ]
    elif decision == "RETURNED_FOR_REPAIR":
        lines += [
            f"Provisional ObjectID: {receipt.get('provisional_object_id')}",
            f"AuthorID(s): {', '.join(receipt.get('author_ids', []))}",
            f"Version: {receipt.get('version')}",
            "",
            "Failed or blocked gates:",
        ]
        lines += [f"  - {g}" for g in receipt.get("failed_or_blocked_gates", [])]
        lines += ["", "Missing structure:"]
        lines += [f"  - {m}" for m in receipt.get("missing_structure", [])]
        lines += [
            "",
            f"Missingness class: {receipt.get('missingness_class')}",
            f"Affected burden: {receipt.get('affected_burden')}",
            f"Why it blocks admission: {receipt.get('why_blocked')}",
            "",
            "Exact repair required:",
        ]
        lines += [f"  - {r}" for r in receipt.get("exact_repair_required", [])]
        lines += [
            "",
            f"Permitted source/evidence: {receipt.get('permitted_source_or_evidence')}",
            f"Repair changes the object: {receipt.get('repair_changes_object')}",
            f"New ObjectID required: {receipt.get('new_object_id_required')}",
            f"Seam declaration required: {receipt.get('seam_declaration_required')}",
            "",
            "Fields already accepted: "
            + (", ".join(receipt.get("fields_already_accepted", [])) or "(none)"),
            "",
            "Fields still blocked:",
        ]
        lines += [f"  - {m}" for m in receipt.get("fields_still_blocked", [])]
        lines += ["", f"Exact resubmission condition: {receipt.get('resubmission_condition')}"]
    else:  # REJECTED
        lines += ["Failed gates:"]
        lines += [f"  - {g}" for g in receipt.get("failed_gates", [])]
        lines += [
            "",
            f"Established violation: {receipt.get('established_violation')}",
            f"Violation class: {receipt.get('violation_class')}",
            f"Why admission is not permitted: {receipt.get('why_not_permitted')}",
            f"Same object repairable: {receipt.get('repairable_same_object')}",
            f"New object/version/seam required: {receipt.get('new_object_version_or_seam_required')}",
            f"Resubmission conditions: {receipt.get('resubmission_conditions')}",
        ]
    lines += ["", "---", "", receipt["disclaimer"], ""]
    return "\n".join(lines)


def write_receipt(receipt: dict, receipts_dir: Path = None) -> tuple:
    """Write machine-readable (.json) and human-readable (.md) receipt files."""
    receipts_dir = receipts_dir or loader.RECEIPTS_DIR
    directory = receipts_dir / DECISION_DIRS[receipt["decision"]]
    directory.mkdir(parents=True, exist_ok=True)
    stem = receipt["receipt_id"]
    json_path = directory / f"{stem}.json"
    md_path = directory / f"{stem}.md"
    json_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_receipt_markdown(receipt), encoding="utf-8")
    return json_path, md_path

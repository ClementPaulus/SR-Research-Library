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
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import loader
from .gates import GateEvaluation


class ReceiptConflict(RuntimeError):
    """An existing receipt ID would be overwritten with different content."""

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


def next_receipt_id(receipts_dir: Path = None, registry_dir: Path = None) -> str:
    """Next free RCPT value, reconciled against receipts, snapshots, and the reservation ledger."""
    from . import allocation  # local import: allocation depends on loader only

    receipts_dir = receipts_dir or loader.RECEIPTS_DIR
    registry_dir = registry_dir or loader.REGISTRY_DIR
    return allocation.next_free("RCPT", registry_dir=registry_dir, receipts_dir=receipts_dir,
                                registry={"authors": {}, "objects": {}, "sources": {}, "relations": {}, "governing": {}},
                                history={})


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


def _dump(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _same_content(path: Path, text: str) -> bool:
    return path.exists() and path.read_text(encoding="utf-8") == text


def write_receipt(receipt: dict, receipts_dir: Path = None) -> tuple:
    """Write the .json and .md receipt files (legacy entry point; prefer write_receipt_bundle).

    Refuses to overwrite an existing receipt ID with different content; repeating
    the same write is a no-op that returns the existing paths.
    """
    receipts_dir = receipts_dir or loader.RECEIPTS_DIR
    directory = receipts_dir / DECISION_DIRS[receipt["decision"]]
    directory.mkdir(parents=True, exist_ok=True)
    stem = receipt["receipt_id"]
    json_path = directory / f"{stem}.json"
    md_path = directory / f"{stem}.md"
    json_text = _dump(receipt)
    if json_path.exists() and not _same_content(json_path, json_text):
        raise ReceiptConflict(f"{json_path.name} already exists with different content; receipts are never rewritten")
    _guard_other_decision_dirs(receipts_dir, stem, receipt["decision"])
    json_path.write_text(json_text, encoding="utf-8")
    md_path.write_text(render_receipt_markdown(receipt), encoding="utf-8")
    return json_path, md_path


def _guard_other_decision_dirs(receipts_dir: Path, stem: str, decision: str) -> None:
    for other_decision, subdir in DECISION_DIRS.items():
        if other_decision != decision and (receipts_dir / subdir / f"{stem}.json").exists():
            raise ReceiptConflict(
                f"{stem} already exists under receipts/{subdir}/ with decision {other_decision}; "
                "a corrected decision is a new receipt with declared linkage, never an overwrite")


def bundle_paths(receipt: dict, receipts_dir: Path = None) -> dict:
    receipts_dir = receipts_dir or loader.RECEIPTS_DIR
    directory = receipts_dir / DECISION_DIRS[receipt["decision"]]
    stem = receipt["receipt_id"]
    return {
        "receipt_json": directory / f"{stem}.json",
        "receipt_md": directory / f"{stem}.md",
        "submission": directory / f"{stem}.submission.json",
        "execution": receipts_dir / "executions" / f"{stem}.execution.json",
    }


def write_receipt_bundle(receipt: dict, record: dict, execution_manifest: dict = None,
                         receipts_dir: Path = None) -> dict:
    """Atomically write receipt JSON, Markdown, the submission snapshot, and the execution manifest.

    All members are staged in a temporary directory and moved into place only
    when every member is ready, so a bundle is never partially published.
    Repeating the same operation recovers the stored bundle; a different
    payload under an existing receipt ID is refused.
    """
    receipts_dir = receipts_dir or loader.RECEIPTS_DIR
    paths = bundle_paths(receipt, receipts_dir)
    stem = receipt["receipt_id"]
    payloads = {
        "receipt_json": _dump(receipt),
        "receipt_md": render_receipt_markdown(receipt),
        "submission": _dump(record),
    }
    if execution_manifest is not None:
        if execution_manifest.get("receipt_id") != stem:
            raise ValueError("execution manifest receipt_id does not match the receipt")
        payloads["execution"] = _dump(execution_manifest)

    _guard_other_decision_dirs(receipts_dir, stem, receipt["decision"])
    existing = {key: paths[key].exists() for key in payloads}
    if any(existing.values()):
        for key, present in existing.items():
            if present and not _same_content(paths[key], payloads[key]):
                raise ReceiptConflict(
                    f"{paths[key].name} already exists with different content; receipts, snapshots and "
                    "execution manifests are never rewritten")
        if all(existing.values()):
            return {key: paths[key] for key in payloads}
        # Partial earlier write with identical content: fall through and complete it.

    staging = Path(tempfile.mkdtemp(prefix=f".{stem}.", dir=receipts_dir))
    try:
        staged = {}
        for key, text in payloads.items():
            staged_path = staging / paths[key].name
            staged_path.write_text(text, encoding="utf-8")
            staged[key] = staged_path
        for key in payloads:
            paths[key].parent.mkdir(parents=True, exist_ok=True)
        for key, staged_path in staged.items():
            if not paths[key].exists():
                os.replace(staged_path, paths[key])
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return {key: paths[key] for key in payloads}


def load_submission_snapshots(receipts_dir: Path = None) -> dict:
    """{receipt_id: preserved submission record} for every decision directory."""
    receipts_dir = receipts_dir or loader.RECEIPTS_DIR
    snapshots = {}
    for subdir in DECISION_DIRS.values():
        directory = receipts_dir / subdir
        if directory.is_dir():
            for path in sorted(directory.glob("RCPT-*.submission.json")):
                snapshots[path.name.split(".")[0]] = json.loads(path.read_text(encoding="utf-8"))
    return snapshots

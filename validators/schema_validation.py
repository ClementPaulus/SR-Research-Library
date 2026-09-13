from __future__ import annotations

from pathlib import Path

from jsonschema import Draft202012Validator

from .common import ROOT, list_yaml_files, load_json, load_yaml

SCHEMA_DIR = ROOT / "schema"

REPO_OBJECT_SCHEMAS = {
    "author.schema.json",
    "object.schema.json",
    "source.schema.json",
    "relation.schema.json",
    "receipt.schema.json",
}

SCHEMA_RECORD_TARGETS = {
    "author.schema.json": [ROOT / "registry" / "authors"],
    "object.schema.json": [ROOT / "registry" / "objects"],
    "source.schema.json": [ROOT / "registry" / "sources"],
    "relation.schema.json": [ROOT / "registry" / "relations"],
    "receipt.schema.json": [ROOT / "receipts" / "accepted", ROOT / "receipts" / "repair", ROOT / "receipts" / "rejected"],
}


def validate_schema_files() -> list[str]:
    errors: list[str] = []
    schema_files = sorted(SCHEMA_DIR.glob("*.schema.json"))

    for path in schema_files:
        try:
            schema_data = load_json(path)
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"Invalid JSON schema file {path.name}: {exc}")
            continue

        try:
            Draft202012Validator.check_schema(schema_data)
        except Exception as exc:
            errors.append(f"{path.name} is not a valid JSON Schema: {exc}")
            continue

        if path.name in REPO_OBJECT_SCHEMAS:
            for required_key in ("$schema", "$id", "type", "required", "properties"):
                if required_key not in schema_data:
                    errors.append(f"{path.name} missing required schema key: {required_key}")
            if schema_data.get("type") != "object":
                errors.append(f"{path.name} root type must be object")
            if not isinstance(schema_data.get("required"), list) or not schema_data.get("required"):
                errors.append(f"{path.name} must declare non-empty required list")

        validator = Draft202012Validator(schema_data)
        for record_dir in SCHEMA_RECORD_TARGETS.get(path.name, []):
            for record in list_yaml_files(record_dir):
                payload = load_yaml(record)
                for err in validator.iter_errors(payload):
                    try:
                        record_name = str(record.relative_to(ROOT))
                    except ValueError:
                        record_name = str(record)
                    errors.append(f"{record_name} violates {path.name}: {err.message}")

    if not schema_files:
        errors.append("No schema files found")

    return errors

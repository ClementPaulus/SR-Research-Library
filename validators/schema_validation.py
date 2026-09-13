from __future__ import annotations

from jsonschema.validators import Draft202012Validator

from .common import ROOT, load_json

SCHEMA_DIR = ROOT / "schema"

REPO_OBJECT_SCHEMAS = {
    "author.schema.json",
    "object.schema.json",
    "source.schema.json",
    "relation.schema.json",
    "receipt.schema.json",
}


def validate_schema_files() -> list[str]:
    errors: list[str] = []
    schema_files = sorted(SCHEMA_DIR.glob("*.schema.json"))

    for path in schema_files:
        try:
            data = load_json(path)
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"Invalid JSON schema file {path.name}: {exc}")
            continue

        try:
            Draft202012Validator.check_schema(data)
        except Exception as exc:
            errors.append(f"{path.name} is not a valid JSON Schema: {exc}")
            continue

        if path.name in REPO_OBJECT_SCHEMAS:
            for required_key in ("$schema", "$id", "type", "required", "properties"):
                if required_key not in data:
                    errors.append(f"{path.name} missing required schema key: {required_key}")
            if data.get("type") != "object":
                errors.append(f"{path.name} root type must be object")
            if not isinstance(data.get("required"), list) or not data.get("required"):
                errors.append(f"{path.name} must declare non-empty required list")

    if not schema_files:
        errors.append("No schema files found")

    return errors

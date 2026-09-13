from __future__ import annotations

from pathlib import Path

from jsonschema.validators import Draft202012Validator

from .common import ROOT, load_json

SCHEMA_DIR = ROOT / "schema"
REQUIRED_SCHEMA_KEYS = {"$schema", "$id", "type", "required", "properties"}


def validate_schema_files() -> list[str]:
    errors: list[str] = []
    schema_files = sorted(SCHEMA_DIR.glob("*.schema.json"))

    for path in schema_files:
        try:
            data = load_json(path)
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"Invalid JSON schema file {path.name}: {exc}")
            continue

        missing = REQUIRED_SCHEMA_KEYS - set(data.keys())
        if missing:
            errors.append(f"{path.name} missing required schema keys: {sorted(missing)}")
        if data.get("type") != "object":
            errors.append(f"{path.name} root type must be object")
        if not isinstance(data.get("required"), list) or not data.get("required"):
            errors.append(f"{path.name} must declare non-empty required list")

        try:
            Draft202012Validator.check_schema(data)
        except Exception as exc:
            errors.append(f"{path.name} is not a valid JSON Schema: {exc}")

    if not schema_files:
        errors.append("No schema files found")

    return errors

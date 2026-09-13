from __future__ import annotations

from .common import ROOT, load_yaml

PRIMARY_FIELDS = {
    "tier2_classes": "tier2_class.primary",
    "domains": "domain.primary",
    "focuses": "structural_focus.primary",
    "evidence_modes": "evidence_mode.primary",
    "provenance_types": "provenance",
    "maturity_states": "maturity",
    "functional_loci": "functional_locus.primary",
    "publication_states": "publication_state",
}

SECONDARY_FIELDS = {
    "tier2_classes": "tier2_class.secondary",
    "domains": "domain.secondary",
    "focuses": "structural_focus.secondary",
    "evidence_modes": "evidence_mode.secondary",
    "functional_loci": "functional_locus.secondary",
}


def _path_get(data: dict, dotted: str):
    current = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def validate_taxonomies() -> list[str]:
    errors: list[str] = []
    taxonomy_terms: dict[str, set[str]] = {}

    for name in PRIMARY_FIELDS:
        taxonomy_data = load_yaml(ROOT / "taxonomy" / f"{name}.yaml")
        terms = taxonomy_data.get("terms", []) if isinstance(taxonomy_data, dict) else []
        taxonomy_terms[name] = set(terms)
        if not terms:
            errors.append(f"taxonomy/{name}.yaml has no terms")

    for obj_path in sorted((ROOT / "registry" / "objects").glob("*.yaml")):
        obj = load_yaml(obj_path)

        for taxonomy_name, field_path in PRIMARY_FIELDS.items():
            value = _path_get(obj, field_path)
            if value is None:
                errors.append(f"{obj_path.name} missing required field: {field_path}")
                continue
            if value not in taxonomy_terms[taxonomy_name]:
                errors.append(f"{obj_path.name} field {field_path} has unsupported value: {value}")

        for taxonomy_name, field_path in SECONDARY_FIELDS.items():
            values = _path_get(obj, field_path)
            if values is None:
                continue
            if not isinstance(values, list):
                errors.append(f"{obj_path.name} field {field_path} must be a list")
                continue
            for value in values:
                if value not in taxonomy_terms[taxonomy_name]:
                    errors.append(f"{obj_path.name} field {field_path} has unsupported value: {value}")

    return errors

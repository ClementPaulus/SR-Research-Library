from __future__ import annotations

from .common import ROOT, list_yaml_files, load_yaml


def validate_relations() -> list[str]:
    errors: list[str] = []

    object_records = [load_yaml(path) for path in list_yaml_files(ROOT / "registry" / "objects")]
    source_records = [load_yaml(path) for path in list_yaml_files(ROOT / "registry" / "sources")]
    relation_records = [load_yaml(path) for path in list_yaml_files(ROOT / "registry" / "relations")]

    object_ids = {record.get("object_id") for record in object_records if isinstance(record, dict) and record.get("object_id")}
    source_ids = {record.get("source_id") for record in source_records if isinstance(record, dict) and record.get("source_id")}
    relation_ids = {
        record.get("relation_id")
        for record in relation_records
        if isinstance(record, dict) and record.get("relation_id")
    }
    valid_targets = object_ids | source_ids

    relation_type_data = load_yaml(ROOT / "taxonomy" / "relation_types.yaml")
    relation_types = set(relation_type_data.get("terms", [])) if isinstance(relation_type_data, dict) else set()

    for path in list_yaml_files(ROOT / "registry" / "objects"):
        obj = load_yaml(path)
        if not isinstance(obj, dict):
            errors.append(f"{path.name}: object record must be a YAML object")
            continue

        relations = obj.get("relations", [])
        if not isinstance(relations, list):
            errors.append(f"{path.name}: relations must be a list")
            relations = []
        for relation_id in relations:
            if relation_id not in relation_ids:
                errors.append(f"{path.name}: unknown relation reference {relation_id}")

        source_refs = obj.get("source_ids", [])
        if not isinstance(source_refs, list):
            errors.append(f"{path.name}: source_ids must be a list")
            source_refs = []
        for source_id in source_refs:
            if source_id not in source_ids:
                errors.append(f"{path.name}: unknown source reference {source_id}")

        required_non_empty = [
            "authority_boundary",
            "next_burden",
            "provenance",
        ]
        for field in required_non_empty:
            if not obj.get(field):
                errors.append(f"{path.name}: missing {field}")

    for path in list_yaml_files(ROOT / "registry" / "relations"):
        rel = load_yaml(path)
        if not isinstance(rel, dict):
            errors.append(f"{path.name}: relation record must be a YAML object")
            continue

        subject = rel.get("subject")
        target = rel.get("object")
        relation_type = rel.get("relation_type")

        if relation_type not in relation_types:
            errors.append(f"{path.name}: unsupported relation_type {relation_type}")
        if subject not in valid_targets:
            errors.append(f"{path.name}: unresolved relation subject {subject}")
        if target not in valid_targets:
            errors.append(f"{path.name}: unresolved relation object {target}")

    return errors

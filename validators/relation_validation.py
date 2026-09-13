from __future__ import annotations

from .common import ROOT, list_yaml_files, load_yaml


def validate_relations() -> list[str]:
    errors: list[str] = []

    object_ids = {
        load_yaml(path).get("object_id")
        for path in list_yaml_files(ROOT / "registry" / "objects")
        if load_yaml(path).get("object_id")
    }
    source_ids = {
        load_yaml(path).get("source_id")
        for path in list_yaml_files(ROOT / "registry" / "sources")
        if load_yaml(path).get("source_id")
    }
    relation_ids = {
        load_yaml(path).get("relation_id")
        for path in list_yaml_files(ROOT / "registry" / "relations")
        if load_yaml(path).get("relation_id")
    }
    valid_targets = object_ids | source_ids

    for path in list_yaml_files(ROOT / "registry" / "objects"):
        obj = load_yaml(path)
        for relation_id in obj.get("relations", []):
            if relation_id not in relation_ids:
                errors.append(f"{path.name}: unknown relation reference {relation_id}")

        for source_id in obj.get("source_ids", []):
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
        subject = rel.get("subject")
        target = rel.get("object")
        if subject not in valid_targets:
            errors.append(f"{path.name}: unresolved relation subject {subject}")
        if target not in valid_targets:
            errors.append(f"{path.name}: unresolved relation object {target}")

    return errors

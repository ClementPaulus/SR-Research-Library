"""Committed-registry projection for the public catalog.

The projection is rebuilt from an identified commit using that commit's own
engine (loader, profiles, bridges, search, sitegen), so the portal shows
exactly what the Git registry contains — never an independently edited copy.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from core.tasks import handler
from registry_bridge.checkout import commit_exists, fetch_default_branch, isolated_checkout, repository_head
from registry_bridge.engine import import_engine
from registry_bridge.models import ProjectionSnapshot, RegistryProjection

log = logging.getLogger("portal.catalog")

REFRESH_PROJECTION = "catalog.refresh_projection"


@dataclass
class Projection:
    sha: str
    objects: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)
    authors: dict = field(default_factory=dict)
    relations: dict = field(default_factory=dict)
    governing: dict = field(default_factory=dict)
    receipts: dict = field(default_factory=dict)
    profiles: dict = field(default_factory=dict)
    search_index: dict = field(default_factory=dict)
    bridge_candidates: dict = field(default_factory=dict)
    object_history: dict = field(default_factory=dict)
    taxonomies: dict = field(default_factory=dict)
    schema_version: str = ""
    taxonomy_version: str = ""
    refreshed_at: object = None

    @property
    def attempts(self) -> dict:
        grouped: dict = {}
        for r in self.receipts.values():
            ident = r.get("object_id") or r.get("provisional_object_id") or r.get("submission_identity")
            if ident:
                grouped.setdefault(ident, []).append(r)
        for ident in grouped:
            grouped[ident].sort(key=lambda r: (r.get("generated") or "", r.get("receipt_id") or ""))
        return grouped

    def current_receipt(self, obj: dict) -> dict | None:
        candidates = self.attempts.get(obj["object_id"], [])
        if not candidates:
            return None
        same = [r for r in candidates if r.get("decision") == "ACCEPTED" and r.get("version") == obj.get("version")]
        if same:
            return same[-1]
        accepted = [r for r in candidates if r.get("decision") == "ACCEPTED"]
        return accepted[-1] if accepted else candidates[-1]

    def bridges_for(self, object_id: str, limit: int = 5) -> tuple:
        rows = []
        for candidate in self.bridge_candidates.get("candidates", []):
            if object_id not in (candidate.get("object_a"), candidate.get("object_b")):
                continue
            if candidate.get("strength") not in ("medium", "high"):
                continue
            other = candidate["object_b"] if candidate["object_a"] == object_id else candidate["object_a"]
            rows.append(dict(candidate, other_id=other, other_title=(self.objects.get(other) or {}).get("title", other),
                             signal_count=len(candidate.get("signals", []))))
        rows.sort(key=lambda c: (-c["signal_count"], 0 if c["strength"] == "high" else 1, c["other_id"]))
        return rows[:limit], len(rows)


_CACHE: dict = {}


def _snapshot_to_projection(snapshot: ProjectionSnapshot) -> Projection:
    rows = RegistryProjection.objects.filter(committed_sha=snapshot.committed_sha)
    projection = Projection(sha=snapshot.committed_sha, receipts=snapshot.receipts, profiles=snapshot.profiles,
                            search_index=snapshot.search_index, bridge_candidates=snapshot.bridge_candidates,
                            object_history=snapshot.object_history, taxonomies=snapshot.taxonomies,
                            schema_version=snapshot.schema_version, taxonomy_version=snapshot.taxonomy_version,
                            refreshed_at=snapshot.refreshed_at)
    for row in rows:
        getattr(projection, {"object": "objects", "source": "sources", "author": "authors", "relation": "relations",
                             "governing": "governing"}[row.kind])[row.record_id] = row.payload
    return projection


def current_projection() -> Projection:
    snapshot = ProjectionSnapshot.objects.filter(is_current=True).order_by("-refreshed_at").first()
    if snapshot is None:
        sha = repository_head()
        snapshot = refresh_projection(sha)
    cached = _CACHE.get(snapshot.committed_sha)
    if cached is None or cached.refreshed_at != snapshot.refreshed_at:
        cached = _snapshot_to_projection(snapshot)
        _CACHE.clear()
        _CACHE[snapshot.committed_sha] = cached
    return cached


def refresh_projection(sha: str = None) -> ProjectionSnapshot:
    """Rebuild every projection row and derived view from the checkout at ``sha``."""
    if sha and not commit_exists(sha):
        fetch_default_branch()
    if not sha or not commit_exists(sha):
        log.warning("projection refresh: commit %s not in local clone; using fetched default branch", (sha or "")[:12])
        sha = fetch_default_branch()
    with isolated_checkout(sha) as checkout:
        engine = import_engine(checkout)
        loader, profiles, bridges, search = engine["loader"], engine["profiles"], engine["bridges"], engine["search"]
        registry = loader.load_registry(checkout / "registry")
        receipts = loader.load_receipts(checkout / "receipts")
        history = loader.load_object_history(checkout / "registry")
        taxonomies = loader.load_taxonomies(checkout / "taxonomy")
        profile_map = profiles.build_all_profiles(registry)
        bridge_projection = bridges.build_bridge_projection(registry)
        index = search.build_search_index(registry, receipts) if search else {"documents": []}
        schema_version = (checkout / "schema" / "VERSION").read_text(encoding="utf-8").strip()
        taxonomy_version = (checkout / "taxonomy" / "VERSION").read_text(encoding="utf-8").strip()
    now = timezone.now()
    with transaction.atomic():
        RegistryProjection.objects.filter(committed_sha=sha).delete()
        rows = []
        for kind, records, id_field in (("author", registry["authors"], "author_id"), ("object", registry["objects"], "object_id"),
                                        ("source", registry["sources"], "source_id"), ("relation", registry["relations"], "relation_id"),
                                        ("governing", registry.get("governing") or {}, "governing_id")):
            for record in records.values():
                payload = json.dumps(record, sort_keys=True, ensure_ascii=False)
                rows.append(RegistryProjection(kind=kind, record_id=record[id_field], committed_sha=sha, payload=record,
                                               payload_hash="sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                                               refreshed_at=now))
        RegistryProjection.objects.bulk_create(rows, batch_size=500)
        ProjectionSnapshot.objects.filter(is_current=True).update(is_current=False)
        snapshot, _ = ProjectionSnapshot.objects.update_or_create(
            committed_sha=sha,
            defaults={"search_index": index, "profiles": profile_map, "bridge_candidates": bridge_projection,
                      "object_history": history, "receipts": receipts, "taxonomies": taxonomies,
                      "schema_version": schema_version, "taxonomy_version": taxonomy_version,
                      "is_current": True, "refreshed_at": now})
    _CACHE.clear()
    return snapshot


@handler(REFRESH_PROJECTION)
def refresh_projection_job(job) -> None:
    refresh_projection(job.payload.get("sha"))

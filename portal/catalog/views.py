"""Public catalog: home, research search, record pages, sources, governing, authors, receipts, contribute."""

from __future__ import annotations

from django.http import Http404
from django.shortcuts import redirect, render

from registry_bridge.engine import import_engine

from .projection import current_projection

_SEARCH_ENGINE = None


def _search_module():
    """The search semantics module from the *live* engine (same code the static site uses)."""
    global _SEARCH_ENGINE
    if _SEARCH_ENGINE is None:
        from django.conf import settings

        _SEARCH_ENGINE = import_engine(settings.PORTAL_REGISTRY_REPO_PATH)["search"]
    return _SEARCH_ENGINE


def home(request):
    projection = current_projection()
    q = request.GET.get("q", "").strip()
    results = None
    if q:
        results = _search_module().search(projection.search_index, q, kinds=("object", "source", "author", "governing"), limit=25)
    counts = {"objects": len(projection.objects), "sources": len(projection.sources), "governing": len(projection.governing),
              "authors": len(projection.authors), "receipts": len(projection.receipts)}
    recent = sorted(projection.objects.values(), key=lambda o: o.get("date", ""), reverse=True)[:6]
    return render(request, "catalog/home.html", {"projection": projection, "counts": counts, "recent": recent, "q": q, "results": results})


FILTER_AXES = ["domain", "class", "focus", "evidence", "maturity", "provenance", "publication_state", "functional_locus", "author", "source"]
AXIS_TAXONOMY = {"domain": "domains", "class": "tier2_classes", "focus": "focuses", "evidence": "evidence_modes",
                 "maturity": "maturity_states", "provenance": "provenance_types", "publication_state": "publication_states",
                 "functional_locus": "functional_loci"}


def research(request):
    projection = current_projection()
    q = request.GET.get("q", "").strip()
    filters = {axis: set(v for v in request.GET.getlist(axis) if v) for axis in FILTER_AXES}
    filters = {k: v for k, v in filters.items() if v}
    result = _search_module().search(projection.search_index, q, filters=filters, kinds=("object",))
    options = {axis: projection.taxonomies.get(taxonomy, []) for axis, taxonomy in AXIS_TAXONOMY.items()}
    options["author"] = [(a["author_id"], a["display_name"]) for a in sorted(projection.authors.values(), key=lambda a: a["author_id"])]
    rows = []
    for hit in result["results"]:
        doc = hit["document"]
        rows.append({"doc": doc, "record": projection.objects.get(doc["id"]), "matched": hit["matched_fields"], "excerpts": hit["excerpts"]})
    return render(request, "catalog/research.html", {
        "projection": projection, "q": q, "filters": filters, "result": result, "rows": rows, "options": options,
        "query_string": request.GET.urlencode(),
    })


def research_detail(request, object_id: str):
    projection = current_projection()
    obj = projection.objects.get(object_id)
    if obj is None:
        raise Http404("No registered research object with that identifier")
    receipt = projection.current_receipt(obj)
    attempts = projection.attempts.get(object_id, [])
    relations = [projection.relations[r] for r in obj.get("relations", []) if r in projection.relations]
    inbound = [r for r in projection.relations.values() if r["to_id"] == object_id and r["relation_id"] not in obj.get("relations", [])]
    sources = [projection.sources[s] for s in obj.get("source_ids", []) if s in projection.sources]
    governing = [projection.governing[g] for g in obj.get("governing_refs", []) or [] if g in projection.governing]
    history = sorted((k, v) for k, v in projection.object_history.items() if v.get("object_id") == object_id)
    suggestions, total_suggestions = projection.bridges_for(object_id, limit=5)
    show_all = request.GET.get("suggestions") == "all"
    if show_all:
        suggestions, total_suggestions = projection.bridges_for(object_id, limit=10_000)
    authors = [projection.authors.get(a, {"author_id": a, "display_name": a}) for a in obj.get("authors", [])]
    return render(request, "catalog/research_detail.html", {
        "projection": projection, "o": obj, "receipt": receipt, "attempts": attempts, "relations": relations, "inbound": inbound,
        "sources": sources, "governing": governing, "history": history, "suggestions": suggestions,
        "total_suggestions": total_suggestions, "show_all": show_all, "authors": authors,
    })


def source_detail(request, source_id: str):
    projection = current_projection()
    src = projection.sources.get(source_id)
    if src is None:
        raise Http404("No source with that identifier")
    objects = [o for o in projection.objects.values() if source_id in o.get("source_ids", [])]
    governing = [g for g in projection.governing.values() if g.get("source_id") == source_id]
    return render(request, "catalog/source_detail.html", {"projection": projection, "s": src, "objects": objects, "governing": governing})


def sources(request):
    projection = current_projection()
    q = request.GET.get("q", "").strip()
    result = _search_module().search(projection.search_index, q, kinds=("source",))
    rows = [projection.sources[h["document"]["id"]] for h in result["results"] if h["document"]["id"] in projection.sources]
    return render(request, "catalog/sources.html", {"projection": projection, "rows": rows, "q": q, "total": result["total"]})


def governing_detail(request, governing_id: str):
    projection = current_projection()
    g = projection.governing.get(governing_id)
    if g is None:
        raise Http404("No governing reference with that identifier")
    source = projection.sources.get(g.get("source_id"))
    constrained = [o for o in projection.objects.values() if governing_id in (o.get("governing_refs") or [])]
    return render(request, "catalog/governing_detail.html", {"projection": projection, "g": g, "source": source, "constrained": constrained})


def governing(request):
    projection = current_projection()
    rows = sorted(projection.governing.values(), key=lambda g: g["governing_id"])
    return render(request, "catalog/governing.html", {"projection": projection, "rows": rows})


def authors(request):
    projection = current_projection()
    rows = []
    for a in sorted(projection.authors.values(), key=lambda a: a["author_id"]):
        rows.append({"author": a, "profile": projection.profiles.get(a["author_id"], {})})
    return render(request, "catalog/authors.html", {"projection": projection, "rows": rows})


def author_detail(request, author_id: str):
    projection = current_projection()
    a = projection.authors.get(author_id)
    if a is None:
        raise Http404("No author with that identifier")
    profile = projection.profiles.get(author_id, {})
    objects = sorted((o for o in projection.objects.values() if author_id in o.get("authors", [])), key=lambda o: o["object_id"])
    distributions = [(label, profile.get(key, {})) for key, label in (
        ("primary_domain_distribution", "Primary domain"), ("tier2_class_distribution", "Tier-2 class"),
        ("structural_focus_distribution", "Structural focus"), ("evidence_mode_distribution", "Evidence mode"),
        ("provenance_distribution", "Provenance"), ("maturity_distribution", "Maturity"))]
    return render(request, "catalog/author_detail.html", {"projection": projection, "a": a, "profile": profile, "objects": objects,
                                                          "distributions": distributions})


def receipt_detail(request, receipt_id: str):
    projection = current_projection()
    r = projection.receipts.get(receipt_id)
    if r is None:
        raise Http404("No public receipt with that identifier")
    ident = r.get("object_id") or r.get("provisional_object_id") or r.get("submission_identity")
    registered = ident in projection.objects
    from django.conf import settings

    engine = import_engine(settings.PORTAL_REGISTRY_REPO_PATH)
    markdown = engine["receipts"].render_receipt_markdown(r)
    from registry_bridge.models import EvaluationAttempt, Publication

    attempt = EvaluationAttempt.objects.filter(receipt_id=receipt_id).order_by("-recorded_at").first()
    publication = Publication.objects.filter(attempt=attempt).order_by("-created_at").first() if attempt else None
    return render(request, "catalog/receipt_detail.html", {"projection": projection, "r": r, "ident": ident, "registered": registered,
                                                           "markdown": markdown, "attempt": attempt, "publication": publication})


def receipts(request):
    projection = current_projection()
    rows = sorted(projection.receipts.values(), key=lambda r: r["receipt_id"])
    return render(request, "catalog/receipts.html", {"projection": projection, "rows": rows})


def contribute(request):
    return render(request, "catalog/contribute.html")


# Legacy static-site path compatibility (site/objects/SR-OBJ-000001.html -> /research/SR-OBJ-000001).
def legacy_redirect(request, folder: str, ident: str):
    mapping = {"objects": "catalog:research_detail", "sources": "catalog:source_detail", "governing": "catalog:governing_detail",
               "authors": "catalog:author_detail", "receipts": "catalog:receipt_detail"}
    if folder not in mapping:
        raise Http404
    return redirect(mapping[folder], ident)

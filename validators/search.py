"""Shared search index and query semantics for the public library surface.

One search document per committed record is generated from the registry and
used by both the static projection (site/data/search_index.json + site/search.html)
and the portal catalog, so the two surfaces never disagree about what a term
matches.

Matching rules (documented in docs/PORTAL_IMPLEMENTATION.md):

* unquoted terms are case-insensitive and *all* must match somewhere in the
  indexed public fields of a record (AND);
* "quoted text" is a phrase and must appear contiguously;
* identifiers (SR-OBJ-*, SRC-*, REL-*, AUTH-*, RCPT-*, SR-GOV-*) and DOIs are
  matched exactly against identifier fields as well as by text;
* filters combine by AND across axes and OR within an axis; an object matches
  an axis value if its primary or any secondary value equals it;
* ranking is retrieval relevance only (number of distinct fields matched, then
  identifier), never author prestige or claimed scientific strength.

Only public, committed fields are indexed. Private workspace search is a
separate scope in the portal and never reads this index.
"""

from __future__ import annotations

import re
import unicodedata

from . import loader

ID_RE = re.compile(r"^(SR-OBJ-[0-9]{6}|SRC-[0-9]{6}|REL-[0-9]{6}|AUTH-[0-9]{4}|RCPT-[0-9]{6}|SR-GOV-[0-9]{6})$", re.I)
DOI_RE = re.compile(r"^10\.[0-9]{4,9}/\S+$", re.I)
TOKEN_RE = re.compile(r'"([^"]+)"|(\S+)')

FILTER_AXES = {
    "domain": ("domain", True),
    "class": ("tier2_class", True),
    "focus": ("structural_focus", True),
    "evidence": ("evidence_mode", True),
    "maturity": ("maturity", False),
    "provenance": ("provenance", False),
    "publication_state": ("publication_state", False),
    "functional_locus": ("functional_locus", False),
    "author": ("author_ids", False),
    "source": ("source_ids", False),
}


def _fold(text) -> str:
    text = "" if text is None else str(text)
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()


def _axis(record: dict, key: str) -> dict:
    value = record.get(key) or {}
    if isinstance(value, dict):
        return {"primary": value.get("primary"), "secondary": list(value.get("secondary") or [])}
    return {"primary": value, "secondary": []}


def object_document(o: dict, authors_by_id: dict, sources_by_id: dict, relations_by_id: dict,
                    receipt: dict = None) -> dict:
    authors = [authors_by_id.get(a, {"author_id": a, "display_name": a}) for a in o.get("authors") or []]
    sources = [sources_by_id.get(s, {"source_id": s, "title": s}) for s in o.get("source_ids") or []]
    declared = list(o.get("relations") or [])
    inbound = sorted(rid for rid, r in relations_by_id.items()
                     if rid not in declared and o["object_id"] in (r.get("from_id"), r.get("to_id")))
    relations = [dict(relations_by_id.get(r, {"relation_id": r}), declared_here=True) for r in declared] + \
                [dict(relations_by_id[r], declared_here=False) for r in inbound]
    return {
        "kind": "object",
        "id": o["object_id"],
        "title": o.get("title"),
        "questions": [q for q in [o.get("main_question")] + list(o.get("secondary_questions") or []) if q],
        "main_question": o.get("main_question"),
        "object_of_study": o.get("object_of_study"),
        "lens": o.get("lens"),
        "tier2_class": _axis(o, "tier2_class"),
        "domain": _axis(o, "domain"),
        "structural_focus": _axis(o, "structural_focus"),
        "evidence_mode": _axis(o, "evidence_mode"),
        "provenance": o.get("provenance"),
        "maturity": o.get("maturity"),
        "functional_locus": o.get("functional_locus"),
        "publication_state": o.get("publication_state"),
        "authors": [{"author_id": a.get("author_id"), "display_name": a.get("display_name"), "orcid": a.get("orcid")} for a in authors],
        "author_ids": [a.get("author_id") for a in authors],
        "sources": [{"source_id": s.get("source_id"), "title": s.get("title"), "doi": (s.get("identifier") or {}).get("doi")} for s in sources],
        "source_ids": [s.get("source_id") for s in sources],
        "relations": [{"relation_id": r.get("relation_id"), "relation_type": r.get("relation_type"),
                       "from_id": r.get("from_id"), "to_id": r.get("to_id"), "declared_here": r.get("declared_here", True)} for r in relations],
        "relation_ids": [r.get("relation_id") for r in relations],
        "governing_refs": list(o.get("governing_refs") or []),
        "version": o.get("version"),
        "date": o.get("date"),
        "next_burden": o.get("next_burden"),
        "missingness": [{"item": m.get("item"), "class": m.get("class")} for m in o.get("missingness") or [] if isinstance(m, dict)],
        "receipt": {"receipt_id": receipt["receipt_id"], "decision": receipt["decision"]} if receipt else None,
    }


def source_document(s: dict) -> dict:
    ident = s.get("identifier") or {}
    return {
        "kind": "source", "id": s["source_id"], "title": s.get("title"),
        "source_type": s.get("source_type"), "source_authors": list(s.get("source_authors") or []),
        "doi": ident.get("doi"), "venue": s.get("venue"), "publication_year": s.get("publication_year"),
        "version": s.get("version"), "status": s.get("status"),
        "source_native_claims": list(s.get("source_native_claims") or []),
    }


def author_document(a: dict) -> dict:
    return {"kind": "author", "id": a["author_id"], "display_name": a.get("display_name"), "orcid": a.get("orcid"),
            "status": a.get("status")}


def governing_document(g: dict) -> dict:
    return {"kind": "governing", "id": g["governing_id"], "title": g.get("title"), "status": g.get("status"),
            "governing_role": g.get("governing_role"), "source_id": g.get("source_id"), "scope": g.get("scope")}


def _searchable_fields(doc: dict) -> dict:
    """{field label: folded text} — the public fields a query may match."""
    fields = {}

    def put(label, value):
        if value is None:
            return
        if isinstance(value, (list, tuple)):
            text = " ".join(str(v) for v in value if v is not None)
        else:
            text = str(value)
        if text.strip():
            fields[label] = _fold(text)

    kind = doc.get("kind")
    put("id", doc.get("id"))
    put("title", doc.get("title"))
    if kind == "object":
        put("main_question", doc.get("main_question"))
        put("secondary_questions", [q for q in doc.get("questions", [])[1:]])
        put("object_of_study", doc.get("object_of_study"))
        put("lens", doc.get("lens"))
        for axis in ("tier2_class", "domain", "structural_focus", "evidence_mode"):
            put(f"{axis}.primary", doc[axis]["primary"])
            put(f"{axis}.secondary", doc[axis]["secondary"])
        for key in ("provenance", "maturity", "functional_locus", "publication_state", "version", "date", "next_burden"):
            put(key, doc.get(key))
        put("authors", [f"{a.get('display_name')} {a.get('author_id')} {a.get('orcid') or ''}" for a in doc.get("authors", [])])
        put("sources", [f"{s.get('source_id')} {s.get('title')} {s.get('doi') or ''}" for s in doc.get("sources", [])])
        put("relations", [f"{r.get('relation_id')} {r.get('relation_type')} {r.get('from_id')} {r.get('to_id')}" for r in doc.get("relations", [])])
        put("governing_refs", doc.get("governing_refs"))
        put("missingness", [f"{m.get('item')} {m.get('class')}" for m in doc.get("missingness", [])])
        if doc.get("receipt"):
            put("receipt", f"{doc['receipt']['receipt_id']} {doc['receipt']['decision']}")
    elif kind == "source":
        for key in ("source_type", "source_authors", "doi", "venue", "publication_year", "version", "status", "source_native_claims"):
            put(key, doc.get(key))
    elif kind == "author":
        put("display_name", doc.get("display_name"))
        put("orcid", doc.get("orcid"))
    elif kind == "governing":
        for key in ("status", "governing_role", "source_id", "scope"):
            put(key, doc.get(key))
    return fields


def _identifier_values(doc: dict) -> set:
    values = {doc.get("id")}
    if doc.get("kind") == "object":
        values.update(doc.get("author_ids", []))
        values.update(doc.get("source_ids", []))
        values.update(doc.get("relation_ids", []))
        values.update(doc.get("governing_refs", []))
        values.update(s.get("doi") for s in doc.get("sources", []))
        if doc.get("receipt"):
            values.add(doc["receipt"]["receipt_id"])
    elif doc.get("kind") == "source":
        values.add(doc.get("doi"))
    elif doc.get("kind") == "governing":
        values.add(doc.get("source_id"))
    return {_fold(v) for v in values if v}


def build_search_index(registry: dict = None, receipts: dict = None, receipt_for: dict = None) -> dict:
    """Build the shared public search index from committed records."""
    if registry is None:
        registry = loader.load_registry()
    if receipts is None:
        receipts = loader.load_receipts()
    authors_by_id = {a["author_id"]: a for a in registry["authors"].values()}
    sources_by_id = {s["source_id"]: s for s in registry["sources"].values()}
    relations_by_id = {r["relation_id"]: r for r in registry["relations"].values()}
    if receipt_for is None:
        from . import sitegen  # local import to avoid a cycle at module load
        attempts = sitegen.attempts_by_identity(receipts)
        receipt_for = {}
        for o in registry["objects"].values():
            chosen = sitegen.select_current_receipt(o, attempts)
            if chosen:
                receipt_for[o["object_id"]] = chosen
    documents = []
    for o in sorted(registry["objects"].values(), key=lambda r: r["object_id"]):
        documents.append(object_document(o, authors_by_id, sources_by_id, relations_by_id, receipt_for.get(o["object_id"])))
    for s in sorted(registry["sources"].values(), key=lambda r: r["source_id"]):
        documents.append(source_document(s))
    for a in sorted(registry["authors"].values(), key=lambda r: r["author_id"]):
        documents.append(author_document(a))
    for g in sorted((registry.get("governing") or {}).values(), key=lambda r: r["governing_id"]):
        documents.append(governing_document(g))
    return {
        "index_version": "SR-SEARCH-INDEX.v0.1.0",
        "schema_version": loader.schema_version(),
        "taxonomy_version": loader.taxonomy_version(),
        "semantics": {
            "terms": "all unquoted terms must match (case-insensitive, accent-folded)",
            "phrase": "\"quoted text\" must appear contiguously",
            "identifiers": "SR-OBJ/SRC/REL/AUTH/RCPT/SR-GOV identifiers and DOIs match exactly",
            "filters": "AND across axes, OR within an axis; primary or secondary values match",
            "ranking": "retrieval relevance only (distinct fields matched, then identifier order)",
        },
        "filter_axes": sorted(FILTER_AXES),
        "documents": documents,
    }


def parse_query(query: str) -> list:
    """Split a query into terms: {"text": folded, "phrase": bool, "identifier": bool}."""
    terms = []
    for phrase, word in TOKEN_RE.findall(query or ""):
        raw = phrase or word
        if not raw.strip():
            continue
        folded = _fold(raw.strip())
        terms.append({"text": folded, "phrase": bool(phrase),
                      "identifier": bool(ID_RE.match(raw.strip()) or DOI_RE.match(raw.strip()))})
    return terms


def _term_matches(term: dict, fields: dict, identifiers: set) -> list:
    """Field labels where the term matches (empty when it does not)."""
    matched = []
    if term["identifier"] and term["text"] in identifiers:
        matched.append("identifier")
    needle = term["text"]
    for label, text in fields.items():
        if term["phrase"]:
            if needle in text:
                matched.append(label)
        else:
            if needle in text:
                matched.append(label)
    return matched


def _passes_filters(doc: dict, filters: dict) -> bool:
    if doc.get("kind") != "object":
        return not filters
    for axis, wanted in (filters or {}).items():
        wanted = {w for w in wanted if w}
        if not wanted:
            continue
        key, has_secondary = FILTER_AXES.get(axis, (axis, False))
        value = doc.get(key)
        if has_secondary and isinstance(value, dict):
            present = {value.get("primary")} | set(value.get("secondary") or [])
        elif isinstance(value, list):
            present = set(value)
        else:
            present = {value}
        if not (present & wanted):
            return False
    return True


def _excerpt(text: str, needle: str, width: int = 90) -> str:
    position = text.find(needle)
    if position < 0:
        return text[:width]
    start = max(0, position - width // 3)
    end = min(len(text), position + len(needle) + width // 2)
    return ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")


def search(index: dict, query: str = "", filters: dict = None, kinds: tuple = ("object",), limit: int = None) -> dict:
    """Run a query over the shared index; deterministic ordering, relevance-only ranking."""
    terms = parse_query(query)
    results = []
    for doc in index["documents"]:
        if kinds and doc.get("kind") not in kinds:
            continue
        if not _passes_filters(doc, filters or {}):
            continue
        fields = _searchable_fields(doc)
        identifiers = _identifier_values(doc)
        matched_fields: dict = {}
        ok = True
        for term in terms:
            labels = _term_matches(term, fields, identifiers)
            if not labels:
                ok = False
                break
            for label in labels:
                matched_fields.setdefault(label, term["text"])
        if not ok:
            continue
        excerpts = {label: _excerpt(fields.get(label, ""), needle) for label, needle in matched_fields.items() if label in fields}
        results.append({"document": doc, "matched_fields": sorted(matched_fields), "excerpts": excerpts,
                        "score": len(matched_fields)})
    results.sort(key=lambda r: (-r["score"], r["document"]["kind"], r["document"]["id"]))
    total = len(results)
    if limit is not None:
        results = results[:limit]
    return {"query": query, "terms": terms, "filters": {k: sorted(v) for k, v in (filters or {}).items() if v},
            "total": total, "results": results}

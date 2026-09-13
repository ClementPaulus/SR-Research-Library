"""Static public library surface generation.

The registry files are the source of truth. The site is generated *from* the
registry and receipts and is never a second independent database: every run
regenerates site/data/*.json and every HTML page.

Three entry surfaces are kept visually and structurally distinct:

  GOVERNING REFERENCES  (SR-GOV-*)  — canon-facing, constitutional, authority-axis,
                                       functional-source, kernel/protocol/specification,
                                       publication-protocol, ingress, language-contact
  TIER-2 RESEARCH       (SR-OBJ-*)  — the living research body with admission receipts
  SOURCES & ARCHIVES    (SRC-*)     — where a work lives: DOI, archive, labeled links

A source is never shown with a Tier-2 classification. A governing reference is
never shown as research. Listing a governing reference on a Tier-2 object
transfers no authority.

Cross-domain retrieval follows FIND -> COMPARE -> EXTRACT TRANSFERABLE STRUCTURE
-> REINSTANTIATE LOCALLY -> VALIDATE LOCALLY. Thresholds, adapters, closure
gates, evidence standards, causal claims, ontological claims, and source
authority are never transferred automatically between domains.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from . import loader, profiles, receipts as receipts_mod

DISCLAIMER = ("Library admission means organizational conformance only and does not imply "
              "scientific truth, endorsement, Tier-0 adoption, or Tier-1 admission.")

AXES = {
    "domains": ("Domains", "domain", "domain", "domains"),
    "focus": ("Structural focus", "structural_focus", "focus", "focuses"),
    "classes": ("Tier-2 classes", "tier2_class", "Tier-2 class", "tier2_classes"),
    "evidence": ("Evidence modes", "evidence_mode", "evidence mode", "evidence_modes"),
    "maturity": ("Maturity", "maturity", "maturity", "maturity_states"),
}

GOVERNING_FILTERS = [
    "Tier-1-bearing", "Tier-0-bearing", "mixed",
    "constitutional", "canon-facing", "authority-axis", "functional-source", "kernel-reference",
    "protocol", "specification", "publication-protocol", "ingress", "language-contact",
    "active", "candidate", "historical", "superseded", "unresolved",
]

OBJECT_HEADERS = ["SR-OBJ", "Title", "Authors", "Domain", "Tier-2 class", "Structural focus", "Evidence mode",
                  "Provenance", "Maturity", "Sources", "Receipt", "Date"]


# --------------------------------------------------------------------------- data

def build_site_data(registry: dict = None, receipts: dict = None) -> dict:
    if registry is None:
        registry = loader.load_registry()
    if receipts is None:
        receipts = loader.load_receipts()
    return {
        "authors": sorted(registry["authors"].values(), key=lambda r: r.get("author_id", "")),
        "objects": sorted(registry["objects"].values(), key=lambda r: r.get("object_id", "")),
        "sources": sorted(registry["sources"].values(), key=lambda r: r.get("source_id", "")),
        "relations": sorted(registry["relations"].values(), key=lambda r: r.get("relation_id", "")),
        "governing": sorted((registry.get("governing") or {}).values(), key=lambda r: r.get("governing_id", "")),
        "receipts": dict(sorted(receipts.items())),
        "profiles": profiles.build_all_profiles(registry),
        "taxonomies": loader.load_taxonomies(),
        "schema_version": loader.schema_version(),
        "taxonomy_version": loader.taxonomy_version(),
    }


# --------------------------------------------------------------------------- html helpers

def _e(value) -> str:
    text = "" if value is None else str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _slug(value) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-") or "none"


def question_slug(question: str, limit: int = 80) -> str:
    """Canonical /questions/<slug> key (SEAM-0007 policy).

    Lower-case, Unicode normalized to ASCII, runs of non-alphanumerics -> '-',
    trimmed, truncated to ``limit`` characters at a word boundary. Questions
    that normalize to the same slug share one page.
    """
    ascii_text = unicodedata.normalize("NFKD", str(question or "")).encode("ascii", "ignore").decode("ascii")
    slug = _slug(ascii_text)
    if len(slug) > limit:
        slug = slug[:limit].rsplit("-", 1)[0] or slug[:limit]
    return slug or "none"


STYLE = """
  body { font-family: system-ui, sans-serif; margin: 0; line-height: 1.5; color: #1a1a1a; }
  header { background: #1f2a37; color: #fff; padding: 0.8rem 1.5rem; }
  header a { color: #fff; text-decoration: none; margin-right: 1.2rem; font-weight: 600; }
  header .brand { font-size: 1.1rem; margin-right: 2rem; }
  main { max-width: 68rem; margin: 1.5rem auto; padding: 0 1.5rem; }
  h1, h2, h3 { font-weight: 600; }
  .kind { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 0.3rem; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.02em; }
  .kind-gov { background: #fde68a; color: #4a3200; }
  .kind-obj { background: #bfdbfe; color: #0b2f6b; }
  .kind-src { background: #d1fae5; color: #064e3b; }
  .kind-rcpt { background: #e5e7eb; color: #111827; }
  .status { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 0.3rem; font-size: 0.8rem; background: #f3f4f6; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; font-size: 0.92rem; }
  th, td { border: 1px solid #d4d4d8; padding: 0.4rem 0.6rem; text-align: left; vertical-align: top; }
  th { background: #f4f4f5; }
  dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.3rem 1rem; }
  dt { font-weight: 600; color: #374151; }
  dd { margin: 0; }
  input.filter { padding: 0.45rem; width: 100%; box-sizing: border-box; margin-bottom: 0.8rem; }
  .chips button { margin: 0 0.3rem 0.3rem 0; padding: 0.2rem 0.6rem; border: 1px solid #9ca3af; border-radius: 1rem; background: #fff; cursor: pointer; font-size: 0.85rem; }
  .chips button.on { background: #1f2a37; color: #fff; border-color: #1f2a37; }
  .note { color: #52525b; font-size: 0.9rem; }
  .boundary { border-left: 4px solid #f59e0b; padding: 0.4rem 0.8rem; background: #fffbeb; margin: 1rem 0; }
  ul.links li { margin-bottom: 0.2rem; }
  .pref { font-weight: 700; }
  pre { background: #f8fafc; padding: 1rem; overflow-x: auto; font-size: 0.85rem; white-space: pre-wrap; }
  footer { max-width: 68rem; margin: 2rem auto; padding: 0 1.5rem 2rem; color: #52525b; font-size: 0.85rem; }
"""

FILTER_SCRIPT = """
<script>
(function () {
  var box = document.getElementById('filter');
  var active = {};
  function apply() {
    var needle = box ? box.value.toLowerCase() : '';
    document.querySelectorAll('table.filterable tbody tr').forEach(function (row) {
      var tags = (row.getAttribute('data-tags') || '').split(' ');
      var okTags = Object.keys(active).every(function (t) { return tags.indexOf(t) !== -1; });
      var okText = row.textContent.toLowerCase().indexOf(needle) !== -1;
      row.style.display = (okTags && okText) ? '' : 'none';
    });
  }
  if (box) box.addEventListener('input', apply);
  document.querySelectorAll('.chips button').forEach(function (b) {
    b.addEventListener('click', function () {
      var t = b.getAttribute('data-tag');
      if (active[t]) { delete active[t]; b.classList.remove('on'); } else { active[t] = true; b.classList.add('on'); }
      apply();
    });
  });
})();
</script>
"""


def _page(title: str, body: str, root: str, versions: dict) -> str:
    nav = (f'<a class="brand" href="{root}index.html">Structura Reditus Research Library</a>'
           f'<a href="{root}governing/index.html">Governing References</a>'
           f'<a href="{root}objects/index.html">Tier-2 Research</a>'
           f'<a href="{root}sources/index.html">Sources &amp; Archives</a>'
           f'<a href="{root}authors/index.html">Authors</a>'
           f'<a href="{root}receipts/index.html">Receipts</a>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(title)} — Structura Reditus Research Library</title>
<style>{STYLE}</style>
</head>
<body>
<header>{nav}</header>
<main>
{body}
</main>
<footer>
<p>{DISCLAIMER} Generated from the registry (the source of truth); this site is never a second database.
Schema {_e(versions['schema_version'])} &middot; Taxonomy {_e(versions['taxonomy_version'])}.</p>
<p>Cross-domain retrieval: FIND &rarr; COMPARE &rarr; EXTRACT TRANSFERABLE STRUCTURE &rarr; REINSTANTIATE LOCALLY &rarr; VALIDATE LOCALLY.
Thresholds, adapters, closure gates, evidence standards, causal claims, ontological claims, and source authority are never transferred automatically.</p>
</footer>
</body>
</html>
"""


def _table(headers: list, rows: list, table_id: str = "", empty: str = "Nothing registered yet.", filterable: bool = False) -> str:
    head = "".join(f"<th>{_e(h)}</th>" for h in headers)
    body = "\n".join(rows) or f'<tr><td colspan="{len(headers)}">{_e(empty)}</td></tr>'
    attrs = (f' id="{table_id}"' if table_id else "") + (' class="filterable"' if filterable else "")
    return f"<table{attrs}><thead><tr>{head}</tr></thead><tbody>\n{body}\n</tbody></table>"


def _row(cells: list, attrs: str = "") -> str:
    return f"<tr{attrs}>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def _link(root: str, kind: str, ident: str, text: str = None) -> str:
    folder = {"gov": "governing", "obj": "objects", "src": "sources", "auth": "authors", "rcpt": "receipts"}[kind]
    return f'<a href="{root}{folder}/{_e(ident)}.html">{_e(text or ident)}</a>'


def _entity_link(root: str, ident: str) -> str:
    return _link(root, "obj" if str(ident).startswith("SR-OBJ") else "src", ident)


def _dl(items: list) -> str:
    return "<dl>" + "".join(f"<dt>{_e(term)}</dt><dd>{value}</dd>" for term, value in items) + "</dl>"


def _list(values, escape=True) -> str:
    values = [v for v in (values or []) if v not in (None, "")]
    if not values:
        return '<span class="note">(none)</span>'
    return "<ul>" + "".join(f"<li>{_e(v) if escape else v}</li>" for v in values) + "</ul>"


def _secondary(block: dict) -> str:
    sec = (block or {}).get("secondary") or []
    return f' <span class="note">{", ".join(_e(x) for x in sec)}</span>' if sec else ""


def _missingness(entries) -> str:
    rows = []
    for m in entries or []:
        if isinstance(m, dict):
            rows.append(_row([_e(m.get("item")), f'<span class="status">{_e(m.get("class"))}</span>', _e(m.get("notes", ""))]))
        else:
            rows.append(_row([_e(m), "", ""]))
    return _table(["Item", "Class", "Notes"], rows, empty="No missingness declared.")


def _external_links(source: dict) -> str:
    items = []
    for link in source.get("links") or []:
        cls = ' class="pref"' if link.get("preferred") else ""
        items.append(f'<li><a{cls} href="{_e(link["url"])}" rel="external noopener">{_e(link["label"])}</a> '
                     f'<span class="note">({_e(link["type"])}{"; preferred" if link.get("preferred") else ""})</span></li>')
    if not items:
        return ('<p class="note">No outbound links recorded. Identity is preserved by the identifiers above; '
                'a missing or broken web link never removes a source.</p>')
    return '<ul class="links">' + "".join(items) + "</ul>"


# --------------------------------------------------------------------------- governing surface

def _gov_tags(g: dict) -> list:
    scope = g.get("authority_scope") or {}
    t1, t0 = bool(scope.get("tier_1")), bool(scope.get("tier_0"))
    tags = (["Tier-1-bearing"] if t1 else []) + (["Tier-0-bearing"] if t0 else []) + (["mixed"] if t1 and t0 else [])
    return tags + list(g.get("governing_role") or []) + [g.get("status", "")]


def _scope_summary(g: dict) -> str:
    scope = g.get("authority_scope") or {}
    parts = [t for t, present in (("Tier-1", scope.get("tier_1")), ("Tier-0", scope.get("tier_0"))) if present]
    return ", ".join(parts) or '<span class="note">no Tier-1/Tier-0 burden</span>'


def _governing_index(data: dict, root: str) -> str:
    chips = "".join(f'<button type="button" data-tag="{_e(t)}">{_e(t)}</button>' for t in GOVERNING_FILTERS)
    rows = [_row([
        _link(root, "gov", g["governing_id"]), _e(g["title"]), _e(g["version"]),
        f'<span class="status">{_e(g["status"])}</span>',
        ", ".join(_e(r) for r in g.get("governing_role", [])), _scope_summary(g), _link(root, "src", g["source_id"]),
    ], f' data-tags="{_e(" ".join(_gov_tags(g)))}"') for g in data["governing"]]
    return f"""
<h1><span class="kind kind-gov">GOVERNING REFERENCES</span></h1>
<p>Canon-facing, constitutional, authority-axis, functional-source, kernel-reference, protocol, specification,
publication-protocol, ingress, and language-contact references with their exact admitted burden.
These records are <strong>not</strong> Tier-2 research objects. Authority belongs to the admitted burden shown on each
record, never to the whole document: a document is never classified wholly Tier-1 or Tier-0 because it contains material at that level.</p>
<div class="chips">{chips}</div>
<input id="filter" class="filter" placeholder="Filter governing references by title, version, role, status, or source&hellip;">
{_table(["SR-GOV", "Title", "Version", "Status", "Roles", "Authority scope", "Source"], rows, "governing", "No governing references registered yet.", filterable=True)}
{FILTER_SCRIPT}
"""


def _governing_page(g: dict, root: str, by_source: dict, objects_by_gov: dict) -> str:
    scope = g.get("authority_scope") or {}
    src = by_source.get(g["source_id"])
    supersession = []
    if g.get("supersedes"):
        supersession.append(f'Supersedes {_link(root, "gov", g["supersedes"])} (preserved)')
    if g.get("superseded_by"):
        supersession.append(f'Superseded by {_link(root, "gov", g["superseded_by"])}')
    canonical = (f'<a href="{_e(g["canonical_link"])}" rel="external noopener">{_e(g["canonical_link"])}</a>'
                 if g.get("canonical_link") else '<span class="note">none established by the source</span>')
    linked = [_link(root, "obj", o["object_id"], f'{o["object_id"]} — {o["title"]}') for o in objects_by_gov.get(g["governing_id"], [])]
    return f"""
<p><span class="kind kind-gov">GOVERNING REFERENCE</span> <span class="status">{_e(g["status"])}</span></p>
<h1>{_e(g["title"])}</h1>
{_dl([
    ("SR-GOV ID", _e(g["governing_id"])),
    ("Source ID", _link(root, "src", g["source_id"], f'{g["source_id"]} — {src["title"]}' if src else g["source_id"])),
    ("Version", _e(g["version"])),
    ("Status", f'<span class="status">{_e(g["status"])}</span>'),
    ("Governing role", ", ".join(_e(r) for r in g.get("governing_role", []))),
    ("Source role", _e(g["source_role"])),
    ("DOI", _e(g["doi"]) if g.get("doi") else '<span class="note">none established by the source</span>'),
    ("Canonical link", canonical),
    ("Active from", _e(g["active_from"])),
    ("Immutable record", _e(g["immutable_record"])),
    ("Supersession history", "; ".join(supersession) or '<span class="note">none</span>'),
])}
<h2>Exact admitted burden</h2>
<div class="boundary"><strong>Scope.</strong> {_e(g["scope"])}<br><strong>Non-goal.</strong> {_e(g["non_goal"])}</div>
<h2>Authority scope</h2>
<h3>Tier-1 burden</h3>{_list(scope.get("tier_1"))}
<h3>Tier-0 burden</h3>{_list(scope.get("tier_0"))}
<p class="note">Listing this reference on a Tier-2 object constrains that object; it never transfers this authority to it.</p>
<h2>Missingness</h2>
{_missingness(g.get("missingness"))}
<h2>Linked Tier-2 objects</h2>
{_list(linked, escape=False)}
<h2>Notes</h2>
<p>{_e(g.get("notes") or "")}</p>
"""


# --------------------------------------------------------------------------- Tier-2 surface

def _object_row(o: dict, root: str, receipt_for: dict, extra_cells: list = None) -> str:
    rcpt = receipt_for.get(o["object_id"])
    tags = " ".join(_slug(v) for v in (
        (o.get("domain") or {}).get("primary"), (o.get("tier2_class") or {}).get("primary"),
        (o.get("structural_focus") or {}).get("primary"), (o.get("evidence_mode") or {}).get("primary"),
        o.get("maturity"), o.get("provenance")))
    cells = [
        _link(root, "obj", o["object_id"]), _e(o["title"]),
        ", ".join(_link(root, "auth", a) for a in o.get("authors", [])),
        _e((o.get("domain") or {}).get("primary")), _e((o.get("tier2_class") or {}).get("primary")),
        _e((o.get("structural_focus") or {}).get("primary")), _e((o.get("evidence_mode") or {}).get("primary")),
        _e(o.get("provenance")), _e(o.get("maturity")),
        ", ".join(_link(root, "src", s) for s in o.get("source_ids", [])),
        _link(root, "rcpt", rcpt["receipt_id"], rcpt["decision"]) if rcpt else '<span class="note">none</span>',
        _e(o.get("date")),
    ] + (extra_cells or [])
    return _row(cells, f' data-tags="{_e(tags)}"')


def _objects_index(data: dict, root: str, receipt_for: dict) -> str:
    rows = [_object_row(o, root, receipt_for) for o in data["objects"]]
    views = " &middot; ".join(f'<a href="{root}{key}/index.html">{_e(label)}</a>' for key, (label, _, _, _) in AXES.items())
    return f"""
<h1><span class="kind kind-obj">TIER-2 RESEARCH</span></h1>
<p>The living research body: domain, diagnostic, translation, candidate, pedagogical, external-ingress, and handoff
research registered as Tier-2 objects, each with its admission receipt. Browse by {views} &middot; <a href="{root}questions/index.html">Main question</a> &middot; <a href="{root}timeline/index.html">Timeline</a>.</p>
<input id="filter" class="filter" placeholder="Filter by author, domain, object of study, structural focus, main question, Tier-2 class, evidence mode, provenance, maturity, relation, source, or date&hellip;">
{_table(OBJECT_HEADERS, rows, "objects", "No research objects registered yet.", filterable=True)}
{FILTER_SCRIPT}
"""


def _object_page(o: dict, root: str, by_source: dict, by_gov: dict, receipt_for: dict, relations_by_id: dict, history: dict) -> str:
    rcpt = receipt_for.get(o["object_id"])
    rel_rows = []
    for rid in o.get("relations", []):
        r = relations_by_id.get(rid)
        if r:
            rel_rows.append(_row([_e(rid), _e(r["relation_type"]), _entity_link(root, r["from_id"]), _entity_link(root, r["to_id"]), _e(r.get("notes", ""))]))
    source_blocks = []
    for sid in o.get("source_ids", []):
        s = by_source.get(sid)
        if s:
            doi = (s.get("identifier") or {}).get("doi")
            source_blocks.append(
                f'<h3>{_link(root, "src", sid, f"{sid} — {s["title"]}")} <span class="kind kind-src">SOURCE</span></h3>'
                f'<p class="note">{_e(s.get("source_type"))} &middot; {_e(s.get("venue") or "")} {_e(s.get("publication_year") or "")}'
                f'{" &middot; DOI " + _e(doi) if doi else ""}</p>' + _external_links(s))
    gov_items = [_link(root, "gov", gid, f"{gid} — {by_gov[gid]['title']}" if gid in by_gov else gid) for gid in o.get("governing_refs", []) or []]
    prior = sorted(k for k in history if k.startswith(o["object_id"] + ".v"))
    return f"""
<p><span class="kind kind-obj">TIER-2 RESEARCH OBJECT</span> <span class="status">authority: {_e((o.get("authority") or {}).get("tier"))}</span></p>
<h1>{_e(o["title"])}</h1>
{_dl([
    ("SR-OBJ ID", _e(o["object_id"])),
    ("Authors", ", ".join(_link(root, "auth", a) for a in o.get("authors", []))),
    ("Version / date", f'{_e(o.get("version"))} &middot; {_e(o.get("date"))}'),
    ("Tier-2 class", _e((o.get("tier2_class") or {}).get("primary")) + _secondary(o.get("tier2_class"))),
    ("Functional locus", _e(o.get("functional_locus"))),
    ("Domain", _e((o.get("domain") or {}).get("primary")) + _secondary(o.get("domain"))),
    ("Structural focus", _e((o.get("structural_focus") or {}).get("primary")) + _secondary(o.get("structural_focus"))),
    ("Evidence mode", _e((o.get("evidence_mode") or {}).get("primary")) + _secondary(o.get("evidence_mode"))),
    ("Provenance", _e(o.get("provenance"))),
    ("Maturity", _e(o.get("maturity"))),
    ("Publication state", _e(o.get("publication_state"))),
    ("Lens", _e(o.get("lens"))),
    ("Object of study", _e(o.get("object_of_study"))),
    ("Admission receipt", _link(root, "rcpt", rcpt["receipt_id"], f'{rcpt["receipt_id"]} — {rcpt["decision"]}') if rcpt else '<span class="note">none</span>'),
])}
<h2>Main question</h2><p><a href="{root}questions/{question_slug(o.get("main_question"))}.html">{_e(o.get("main_question"))}</a></p>
<h2>Boundaries</h2>
<div class="boundary"><strong>Authority boundary.</strong> {_e(o.get("authority_boundary"))}</div>
<div class="boundary"><strong>Source boundary.</strong> {_e(o.get("source_boundary"))}</div>
{_dl([("Scope", _e(o.get("scope"))), ("Exclusions", _list(o.get("exclusions"))), ("Preserved meaning", _e(o.get("preserved_meaning"))),
      ("Distortion / substitution risk", _e(o.get("distortion_or_substitution_risk"))), ("Next burden", _e(o.get("next_burden"))),
      ("Repair route", _e(o.get("repair_route")))])}
<h2>Claim layers</h2>
{_table(["Layer", "Claim"], [_row([f'<span class="status">{_e(c.get("layer"))}</span>', _e(c.get("claim"))]) for c in o.get("claim_layers", [])], empty="No claim layers declared.")}
<h2>Missingness</h2>
{_missingness(o.get("missingness"))}
<h2>Sources</h2>
{"".join(source_blocks) or '<p class="note">No sources declared.</p>'}
<h2>Governing references</h2>
{_list(gov_items, escape=False)}
<p class="note">Governing references constrain this record; they transfer no authority to it. This object remains Tier-2.</p>
<h2>Relations</h2>
{_table(["REL", "Type", "From", "To", "Notes"], rel_rows, empty="No relations declared.")}
<h2>Preserved previous versions</h2>
{_list(prior)}
<h2>Notes</h2><p>{_e(o.get("notes") or "")}</p>
"""


def _axis_pages(data: dict, root: str, receipt_for: dict, out: Path, versions: dict) -> None:
    for key, (label, field_name, singular, taxonomy_name) in AXES.items():
        groups: dict = {}
        for o in data["objects"]:
            value = o.get(field_name)
            primary = value.get("primary") if isinstance(value, dict) else value
            secondaries = value.get("secondary", []) if isinstance(value, dict) else []
            for v, role in [(primary, "primary")] + [(s, "secondary") for s in secondaries]:
                if v:
                    groups.setdefault(v, []).append((o, role))
        terms = data["taxonomies"].get(taxonomy_name, [])
        rows = [_row([f'<a href="{_slug(t)}.html">{_e(t)}</a>',
                      _e(sum(1 for _, r in groups.get(t, []) if r == "primary")),
                      _e(sum(1 for _, r in groups.get(t, []) if r == "secondary"))]) for t in terms]
        (out / key).mkdir(parents=True, exist_ok=True)
        index_body = (f"<h1>{_e(label)}</h1><p class='note'>Controlled terms from the taxonomy with counts of Tier-2 objects "
                      f"using each term as a primary or secondary value.</p>" + _table([singular.capitalize(), "Primary", "Secondary"], rows))
        (out / key / "index.html").write_text(_page(label, index_body, root, versions), encoding="utf-8")
        for t in terms:
            members = groups.get(t, [])
            body = (f'<p><span class="kind kind-obj">TIER-2 RESEARCH</span> by {_e(singular)}</p><h1>{_e(t)}</h1>'
                    + _table(OBJECT_HEADERS + ["Role"], [_object_row(o, root, receipt_for, [_e(r)]) for o, r in members],
                             empty=f"No Tier-2 objects use {t}."))
            (out / key / f"{_slug(t)}.html").write_text(_page(f"{label}: {t}", body, root, versions), encoding="utf-8")


def _question_pages(data: dict, root: str, receipt_for: dict, out: Path, versions: dict) -> None:
    groups: dict = {}
    for o in data["objects"]:
        q = o.get("main_question")
        if q:
            groups.setdefault(question_slug(q), []).append(o)
    (out / "questions").mkdir(parents=True, exist_ok=True)
    rows = [_row([f'<a href="{_e(slug)}.html">{_e(members[0]["main_question"])}</a>',
                  ", ".join(_link(root, "obj", o["object_id"]) for o in members)])
            for slug, members in sorted(groups.items(), key=lambda kv: kv[1][0]["main_question"].lower())]
    intro = ("<h1>Main questions</h1><p class='note'>One page per normalized main question (slug policy: lower-case ASCII, "
             "non-alphanumerics to '-', 80 characters at a word boundary; identical normalizations share a page). "
             "Cross-domain retrieval follows FIND &rarr; COMPARE &rarr; EXTRACT TRANSFERABLE STRUCTURE &rarr; REINSTANTIATE LOCALLY &rarr; VALIDATE LOCALLY.</p>")
    (out / "questions" / "index.html").write_text(_page("Main questions", intro + _table(["Main question", "Objects"], rows, empty="No questions registered yet."), root, versions), encoding="utf-8")
    for slug, members in groups.items():
        body = (f'<p><span class="kind kind-obj">TIER-2 RESEARCH</span> by main question</p><h1>{_e(members[0]["main_question"])}</h1>'
                + ("<p class='note'>Other objects whose main question normalizes to this slug: " + "; ".join(_e(m["main_question"]) for m in members[1:] if m["main_question"] != members[0]["main_question"]) + "</p>" if len({m["main_question"] for m in members}) > 1 else "")
                + _table(OBJECT_HEADERS, [_object_row(o, root, receipt_for) for o in members]))
        (out / "questions" / f"{slug}.html").write_text(_page(members[0]["main_question"], body, root, versions), encoding="utf-8")


# --------------------------------------------------------------------------- sources surface

def _sources_index(data: dict, root: str, objects_by_source: dict, gov_by_source: dict, historical_only: bool = False) -> str:
    rows = []
    for s in data["sources"]:
        if historical_only and s.get("source_type") != "historical":
            continue
        objs, govs = objects_by_source.get(s["source_id"], []), gov_by_source.get(s["source_id"], [])
        doi = (s.get("identifier") or {}).get("doi")
        pref = next((l for l in s.get("links") or [] if l.get("preferred")), None)
        rows.append(_row([
            _link(root, "src", s["source_id"]), _e(s["title"]), _e(s.get("source_type")),
            _e(s.get("publication_year") or ""), _e(s.get("venue") or ""),
            f'<a href="{_e(pref["url"])}" rel="external noopener">{_e(pref["label"])}</a>' if pref else (_e(doi) if doi else '<span class="note">none</span>'),
            ", ".join(_link(root, "gov", g["governing_id"]) for g in govs) or '<span class="note">—</span>',
            ", ".join(_link(root, "obj", o["object_id"]) for o in objs) or '<span class="note">source only</span>',
        ], f' data-tags="{_e(_slug(s.get("source_type")))}"'))
    if historical_only:
        title, intro, extra = ("HISTORICAL / PREFREEZE SOURCES",
                               "Historical and prefreeze lineage works. Their historical language is preserved as source evidence and does not overwrite the mature Structura Reditus architecture.", "")
    else:
        title = "SOURCES &amp; ARCHIVES"
        intro = ("Where each work actually lives: DOI, archive, publisher, data, code, historical and external sources, with labeled outbound links. "
                 "The original work remains on its DOI/archive platform; the library never mirrors it. A source is <strong>not</strong> a Tier-2 research object: "
                 "governing, foundational, canonical, and historical works are fully searchable here without being relabeled as Tier-2 research.")
        extra = f'<p><a href="{root}sources/historical.html">Historical / prefreeze source view</a></p>'
    return f"""
<h1><span class="kind kind-src">{title}</span></h1>
<p>{intro}</p>{extra}
<input id="filter" class="filter" placeholder="Filter sources by title, type, year, venue, DOI&hellip;">
{_table(["SRC", "Title", "Type", "Year", "Venue", "Preferred link / DOI", "Governing", "Tier-2 object"], rows, "sources", "No sources registered yet.", filterable=True)}
{FILTER_SCRIPT}
"""


def _lineage(s: dict, root: str) -> str:
    rows = []
    if s.get("concept_doi"):
        rows.append(_row(["Concept DOI", _e(s["concept_doi"]), "archive concept (resolves to the latest deposited version)"]))
    if s.get("version_doi"):
        rows.append(_row(["Version DOI", _e(s["version_doi"]), "specific deposited version this record refers to"]))
    for r in s.get("related_dois") or []:
        rows.append(_row([_e(r.get("relation")), _e(r.get("doi")), _e(r.get("notes", ""))]))
    for old in s.get("supersedes") or []:
        rows.append(_row(["supersedes", _link(root, "src", old), "earlier source state (preserved)"]))
    if s.get("superseded_by"):
        rows.append(_row(["superseded_by", _link(root, "src", s["superseded_by"]), "current source state"]))
    return _table(["Relation", "Identifier", "Notes"], rows, empty="No lineage recorded beyond the anchoring DOI.")


def _source_page(s: dict, root: str, objects_by_source: dict, gov_by_source: dict) -> str:
    objs, govs = objects_by_source.get(s["source_id"], []), gov_by_source.get(s["source_id"], [])
    ident = s.get("identifier") or {}
    role = ('<div class="boundary"><strong>Registry kind: SOURCE.</strong> This record preserves where the work lives and what it states. '
            + ("It has <strong>no Tier-2 research object</strong> and carries no Tier-2 classification." if not objs else
               f"Tier-2 research object(s) built on it: {', '.join(_link(root, 'obj', o['object_id']) for o in objs)}.")
            + (f" Governing reference(s): {', '.join(_link(root, 'gov', g['governing_id']) for g in govs)}." if govs else "")
            + "</div>")
    return f"""
<p><span class="kind kind-src">SOURCE</span> <span class="status">{_e(s.get("source_type"))}</span> <span class="status">{_e(s.get("status", "active"))}</span></p>
<h1>{_e(s["title"])}</h1>
{role}
{_dl([
    ("SRC ID", _e(s["source_id"])),
    ("Source authors", ", ".join(_e(a) for a in s.get("source_authors", []))),
    ("Version", _e(s.get("version")) if s.get("version") else '<span class="note">none stated</span>'),
    ("Year / venue", f'{_e(s.get("publication_year") or "")} &middot; {_e(s.get("venue") or "")}'),
    ("DOI", _e(ident.get("doi")) if ident.get("doi") else '<span class="note">none recorded</span>'),
    ("Other identifiers", "<br>".join(f"<strong>{_e(k)}:</strong> {_e(v)}" for k, v in ident.items() if k != "doi") or '<span class="note">none</span>'),
])}
<h2>Lineage</h2>
<p class="note">Source identity &ne; archive concept &ne; specific deposited version.</p>
{_lineage(s, root)}
<h2>External links</h2>
{_external_links(s)}
<h2>Source-native claims</h2>
{_list(s.get("source_native_claims"))}
<p class="note">Claims the source itself makes, in its own terms. Library interpretation lives on Tier-2 objects, never here.</p>
<h2>Missingness</h2>
{_list(s.get("missingness"))}
<h2>Notes</h2><p>{_e(s.get("notes") or "")}</p>
"""


# --------------------------------------------------------------------------- authors / receipts

def _author_page(a: dict, data: dict, root: str) -> str:
    profile = data["profiles"].get(a["author_id"], {})
    objs = [o for o in data["objects"] if a["author_id"] in (o.get("authors") or [])]
    dist_rows = [_row([_e(label), ", ".join(f"{_e(k)} {v:.2f}" for k, v in profile.get(key, {}).items()) or '<span class="note">—</span>'])
                 for key, label in (("primary_domain_distribution", "Primary domain"), ("tier2_class_distribution", "Tier-2 class"),
                                    ("structural_focus_distribution", "Structural focus"), ("evidence_mode_distribution", "Evidence mode"),
                                    ("provenance_distribution", "Provenance"), ("maturity_distribution", "Maturity"))]
    return f"""
<p><span class="kind kind-rcpt">AUTHOR</span> <span class="status">{_e(a.get("status"))}</span></p>
<h1>{_e(a["display_name"])}</h1>
{_dl([("AuthorID", _e(a["author_id"])), ("ORCID", _e(a.get("orcid") or "")), ("Registered", _e(a.get("registered"))),
      ("Registered authored objects", _e(profile.get("total_registered_authored_objects", 0)))])}
<p class="note">{_e(profile.get("note", ""))}</p>
<h2>Distributions (reconstructible from the registry)</h2>
{_table(["Axis", "Normalized distribution"], dist_rows)}
<h2>Tier-2 research objects</h2>
{_list([_link(root, "obj", o["object_id"], f'{o["object_id"]} — {o["title"]}') for o in objs], escape=False)}
<h2>Notes</h2><p>{_e(a.get("notes") or "")}</p>
"""


def _receipt_identity(r: dict):
    return r.get("object_id") or r.get("provisional_object_id") or r.get("submission_identity")


def _receipt_page(r: dict, root: str, registered_ids: set) -> str:
    ident = _receipt_identity(r)
    obj = _link(root, "obj", ident) if ident in registered_ids else _e(ident)
    return f"""
<p><span class="kind kind-rcpt">ADMISSION RECEIPT</span> <span class="status">{_e(r["decision"])}</span></p>
<h1>{_e(r["receipt_id"])}</h1>
{_dl([("Decision", _e(r["decision"])), ("Submission", obj), ("Generated", _e(r.get("generated")))])}
<pre>{_e(receipts_mod.render_receipt_markdown(r))}</pre>
"""


# --------------------------------------------------------------------------- driver

def generate_site(site_dir: Path = None, registry: dict = None, receipts: dict = None) -> Path:
    """Regenerate the public library surface from the registry and receipts."""
    site_dir = site_dir or loader.SITE_DIR
    data = build_site_data(registry, receipts)
    versions = {"schema_version": data["schema_version"], "taxonomy_version": data["taxonomy_version"]}
    history = loader.load_object_history() if registry is None else {}

    data_dir = site_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for name in ("authors", "objects", "sources", "relations", "governing", "receipts", "profiles", "taxonomies"):
        (data_dir / f"{name}.json").write_text(json.dumps(data[name], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    by_source = {s["source_id"]: s for s in data["sources"]}
    by_gov = {g["governing_id"]: g for g in data["governing"]}
    relations_by_id = {r["relation_id"]: r for r in data["relations"]}
    registered_ids = {o["object_id"] for o in data["objects"]}
    objects_by_source: dict = {}
    objects_by_gov: dict = {}
    for o in data["objects"]:
        for sid in o.get("source_ids", []):
            objects_by_source.setdefault(sid, []).append(o)
        for gid in o.get("governing_refs", []) or []:
            objects_by_gov.setdefault(gid, []).append(o)
    gov_by_source: dict = {}
    for g in data["governing"]:
        gov_by_source.setdefault(g["source_id"], []).append(g)
    receipt_for: dict = {}  # latest receipt per submission identity (receipt ids are sequential)
    for r in data["receipts"].values():
        ident = _receipt_identity(r)
        if ident:
            receipt_for[ident] = r

    up = "../"
    for folder in ("governing", "objects", "sources", "authors", "receipts", "relations", "timeline"):
        (site_dir / folder).mkdir(parents=True, exist_ok=True)

    counts = {k: len(data[k]) for k in ("governing", "objects", "sources", "relations", "authors")}
    accepted = sum(1 for r in data["receipts"].values() if r["decision"] == "ACCEPTED")
    landing = f"""
<h1>Structura Reditus Research Library</h1>
<p class="note">Tier-0 organizational and retrieval surface for the Structura Reditus corpus. Three registries, kept distinct:</p>
<table>
<tr><th><span class="kind kind-gov">GOVERNING REFERENCES</span></th><td><a href="governing/index.html">{counts['governing']} governing references</a> — canon-facing, constitutional, authority-axis, functional-source, kernel/protocol/specification, publication-protocol, ingress, and language-contact references with their exact admitted burden. Not research objects.</td></tr>
<tr><th><span class="kind kind-obj">TIER-2 RESEARCH</span></th><td><a href="objects/index.html">{counts['objects']} registered Tier-2 research objects</a> ({accepted} accepted receipts; <a href="receipts/index.html">all receipts</a>) — the living research body, browsable by <a href="domains/index.html">domain</a>, <a href="focus/index.html">structural focus</a>, <a href="classes/index.html">Tier-2 class</a>, <a href="evidence/index.html">evidence mode</a>, <a href="maturity/index.html">maturity</a>, <a href="questions/index.html">main question</a>, and <a href="timeline/index.html">timeline</a>.</td></tr>
<tr><th><span class="kind kind-src">SOURCES &amp; ARCHIVES</span></th><td><a href="sources/index.html">{counts['sources']} sources</a> — DOI, archive, publisher, data, code, <a href="sources/historical.html">historical</a> and external sources with labeled outbound links. A source is never shown as Tier-2 research.</td></tr>
<tr><th>Authors</th><td><a href="authors/index.html">{counts['authors']} registered author identities</a> — profiles contain only reconstructible quantities; no author score.</td></tr>
</table>
<p class="note">Everything here is a projection of <code>registry/</code> and <code>receipts/</code>. {DISCLAIMER}</p>
"""
    (site_dir / "index.html").write_text(_page("Home", landing, "", versions), encoding="utf-8")

    (site_dir / "governing" / "index.html").write_text(_page("Governing References", _governing_index(data, up), up, versions), encoding="utf-8")
    for g in data["governing"]:
        (site_dir / "governing" / f"{g['governing_id']}.html").write_text(
            _page(g["title"], _governing_page(g, up, by_source, objects_by_gov), up, versions), encoding="utf-8")

    (site_dir / "objects" / "index.html").write_text(_page("Tier-2 Research", _objects_index(data, up, receipt_for), up, versions), encoding="utf-8")
    for o in data["objects"]:
        (site_dir / "objects" / f"{o['object_id']}.html").write_text(
            _page(o["title"], _object_page(o, up, by_source, by_gov, receipt_for, relations_by_id, history), up, versions), encoding="utf-8")
    _axis_pages(data, up, receipt_for, site_dir, versions)
    _question_pages(data, up, receipt_for, site_dir, versions)
    timeline_rows = [_object_row(o, up, receipt_for) for o in sorted(data["objects"], key=lambda r: r.get("date", ""))]
    (site_dir / "timeline" / "index.html").write_text(
        _page("Timeline", "<h1>Timeline</h1><p class='note'>Tier-2 objects by record date.</p>" + _table(OBJECT_HEADERS, timeline_rows), up, versions), encoding="utf-8")

    (site_dir / "sources" / "index.html").write_text(_page("Sources & Archives", _sources_index(data, up, objects_by_source, gov_by_source), up, versions), encoding="utf-8")
    (site_dir / "sources" / "historical.html").write_text(
        _page("Historical sources", _sources_index(data, up, objects_by_source, gov_by_source, historical_only=True), up, versions), encoding="utf-8")
    for s in data["sources"]:
        (site_dir / "sources" / f"{s['source_id']}.html").write_text(_page(s["title"], _source_page(s, up, objects_by_source, gov_by_source), up, versions), encoding="utf-8")

    author_rows = [_row([_link(up, "auth", a["author_id"]), _e(a["display_name"]), _e(a.get("orcid") or ""), _e(a.get("status")),
                         _e(data["profiles"].get(a["author_id"], {}).get("total_registered_authored_objects", 0))]) for a in data["authors"]]
    (site_dir / "authors" / "index.html").write_text(
        _page("Authors", "<h1>Authors</h1>" + _table(["AuthorID", "Display name", "ORCID", "Status", "Registered objects"], author_rows), up, versions), encoding="utf-8")
    for a in data["authors"]:
        (site_dir / "authors" / f"{a['author_id']}.html").write_text(_page(a["display_name"], _author_page(a, data, up), up, versions), encoding="utf-8")

    rcpt_rows = [_row([_link(up, "rcpt", r["receipt_id"]), _e(r["decision"]), _e(_receipt_identity(r)), _e(r.get("generated"))]) for r in data["receipts"].values()]
    (site_dir / "receipts" / "index.html").write_text(
        _page("Receipts", f"<h1>Admission receipts</h1><p class='note'>{DISCLAIMER}</p>" + _table(["Receipt", "Decision", "Submission", "Generated"], rcpt_rows), up, versions), encoding="utf-8")
    for r in data["receipts"].values():
        (site_dir / "receipts" / f"{r['receipt_id']}.html").write_text(_page(r["receipt_id"], _receipt_page(r, up, registered_ids), up, versions), encoding="utf-8")

    rel_rows = [_row([_e(r["relation_id"]), _e(r["relation_type"]), _entity_link(up, r["from_id"]), _entity_link(up, r["to_id"]), _e(r.get("declared")), _e(r.get("notes", ""))])
                for r in data["relations"]]
    (site_dir / "relations" / "index.html").write_text(
        _page("Relations", "<h1>Relations</h1>" + _table(["REL", "Type", "From", "To", "Declared", "Notes"], rel_rows), up, versions), encoding="utf-8")

    return site_dir / "index.html"

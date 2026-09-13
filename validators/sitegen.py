"""Static public library surface generation.

The registry files are the source of truth. The site is generated *from* the
registry and is never a second independent database: every run regenerates
site/data/*.json and site/index.html entirely from registry state.

The generated surface supports browsing/filtering by author, domain,
subdomain (secondary domain), object of study, structural focus, main
question, Tier-2 class, evidence mode, provenance, maturity, relation,
source, and date.

Cross-domain retrieval follows the conceptual route:
FIND -> COMPARE -> EXTRACT TRANSFERABLE STRUCTURE -> REINSTANTIATE LOCALLY
-> VALIDATE LOCALLY. The site never automatically transfers thresholds,
adapters, closure gates, evidence standards, causal claims, ontological
claims, or source authority between domains.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import loader, profiles


def build_site_data(registry: dict = None) -> dict:
    if registry is None:
        registry = loader.load_registry()
    return {
        "authors": sorted(registry["authors"].values(), key=lambda r: r.get("author_id", "")),
        "objects": sorted(registry["objects"].values(), key=lambda r: r.get("object_id", "")),
        "sources": sorted(registry["sources"].values(), key=lambda r: r.get("source_id", "")),
        "relations": sorted(registry["relations"].values(), key=lambda r: r.get("relation_id", "")),
        "profiles": profiles.build_all_profiles(registry),
        "taxonomies": loader.load_taxonomies(),
        "schema_version": loader.schema_version(),
        "taxonomy_version": loader.taxonomy_version(),
    }


INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Structura Reditus Research Library</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 60rem; line-height: 1.5; }}
  h1, h2 {{ font-weight: 600; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; }}
  th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; vertical-align: top; }}
  th {{ background: #f4f4f4; }}
  input {{ padding: 0.4rem; width: 100%; box-sizing: border-box; margin-bottom: 1rem; }}
  .note {{ color: #555; font-size: 0.9rem; }}
</style>
</head>
<body>
<h1>Structura Reditus Research Library</h1>
<p class="note">Tier-0 organizational and retrieval surface for Tier-2 research records.
Generated from the registry (the source of truth).
Library admission means organizational conformance only and does not imply
scientific truth, endorsement, Tier-0 adoption, or Tier-1 admission. This is an even organizational surface, not a prestige hierarchy.</p>
<p class="note">Schema version: {schema_version} &middot; Taxonomy version: {taxonomy_version}</p>

<h2>Research objects</h2>
<input id="filter" placeholder="Filter by author, domain, object of study, structural focus, main question, Tier-2 class, evidence mode, provenance, maturity, relation, source, or date&hellip;">
<table id="objects">
<thead><tr>
<th>ObjectID</th><th>Title</th><th>Authors</th><th>Domain</th><th>Tier-2 class</th>
<th>Structural focus</th><th>Object of study</th><th>Main question</th><th>Evidence mode</th>
<th>Provenance</th><th>Maturity</th><th>Sources</th><th>Relations</th><th>Date</th>
</tr></thead>
<tbody>
{object_rows}
</tbody>
</table>

<h2>Authors</h2>
<table>
<thead><tr><th>AuthorID</th><th>Display name</th><th>ORCID</th><th>Status</th><th>Registered objects</th></tr></thead>
<tbody>
{author_rows}
</tbody>
</table>

<h2>Sources</h2>
<table>
<thead><tr><th>SourceID</th><th>Type</th><th>Title</th><th>Original authors</th></tr></thead>
<tbody>
{source_rows}
</tbody>
</table>

<h2>Cross-domain retrieval route</h2>
<p>FIND &rarr; COMPARE &rarr; EXTRACT TRANSFERABLE STRUCTURE &rarr; REINSTANTIATE LOCALLY &rarr; VALIDATE LOCALLY.</p>
<p class="note">Thresholds, adapters, closure gates, evidence standards, causal claims,
ontological claims, and source authority are never transferred automatically between domains.</p>

<script>
document.getElementById('filter').addEventListener('input', function () {{
  var needle = this.value.toLowerCase();
  document.querySelectorAll('#objects tbody tr').forEach(function (row) {{
    row.style.display = row.textContent.toLowerCase().indexOf(needle) === -1 ? 'none' : '';
  }});
}});
</script>
</body>
</html>
"""


def _escape(value) -> str:
    text = "" if value is None else str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _object_row(obj: dict) -> str:
    cells = [
        obj.get("object_id"),
        obj.get("title"),
        ", ".join(obj.get("authors", [])),
        (obj.get("domain") or {}).get("primary"),
        (obj.get("tier2_class") or {}).get("primary"),
        (obj.get("structural_focus") or {}).get("primary"),
        obj.get("object_of_study"),
        obj.get("main_question"),
        (obj.get("evidence_mode") or {}).get("primary"),
        obj.get("provenance"),
        obj.get("maturity"),
        ", ".join(obj.get("source_ids", [])),
        ", ".join(obj.get("relations", [])),
        obj.get("date"),
    ]
    return "<tr>" + "".join(f"<td>{_escape(c)}</td>" for c in cells) + "</tr>"


def generate_site(site_dir: Path = None, registry: dict = None) -> Path:
    """Regenerate the public library surface from the registry."""
    site_dir = site_dir or loader.SITE_DIR
    data = build_site_data(registry)

    data_dir = site_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for name in ("authors", "objects", "sources", "relations", "profiles", "taxonomies"):
        (data_dir / f"{name}.json").write_text(
            json.dumps(data[name], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    object_rows = "\n".join(_object_row(o) for o in data["objects"]) or \
        "<tr><td colspan=\"14\">No research objects registered yet.</td></tr>"
    author_rows = "\n".join(
        "<tr>" + "".join(f"<td>{_escape(c)}</td>" for c in (
            a.get("author_id"), a.get("display_name"), a.get("orcid"), a.get("status"),
            data["profiles"].get(a.get("author_id"), {}).get("total_registered_authored_objects", 0),
        )) + "</tr>"
        for a in data["authors"]
    ) or "<tr><td colspan=\"5\">No authors registered yet.</td></tr>"
    source_rows = "\n".join(
        "<tr>" + "".join(f"<td>{_escape(c)}</td>" for c in (
            s.get("source_id"), s.get("source_type"), s.get("title"),
            ", ".join(s.get("source_authors", [])),
        )) + "</tr>"
        for s in data["sources"]
    ) or "<tr><td colspan=\"4\">No sources registered yet.</td></tr>"

    index_path = site_dir / "index.html"
    index_path.write_text(INDEX_TEMPLATE.format(
        schema_version=_escape(data["schema_version"]),
        taxonomy_version=_escape(data["taxonomy_version"]),
        object_rows=object_rows,
        author_rows=author_rows,
        source_rows=source_rows,
    ), encoding="utf-8")
    return index_path

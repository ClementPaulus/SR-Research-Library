"""Automatic preparation beyond raw extraction: source identification, duplicate checks,
classification suggestions, and the remaining-questions assessment.

Everything here is deterministic and explainable. A suggestion always says what it matched
and is recorded as *uncertain* library classification, never as a source fact. Nothing
silently fills a gap: an unresolved item becomes a question that states why it matters,
whether it blocks submission, and what would resolve it.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections import Counter

DOI_RE = re.compile(r"\b(10\.[0-9]{4,9}/[^\s\"'<>)\]]+)", re.I)
ARXIV_RE = re.compile(r"\barXiv:\s*([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", re.I)
ZENODO_RE = re.compile(r"zenodo\.org/(?:records?|record)/([0-9]+)", re.I)
VERSION_RE = re.compile(r"\b(?:version|v\.?|revision|rev\.?)\s*([0-9]+(?:\.[0-9]+){0,2})\b", re.I)
URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+", re.I)
PUBLICATION_HINTS = (
    ("preprint", ("preprint", "arxiv", "not peer reviewed", "not yet peer-reviewed")),
    ("archived", ("zenodo", "figshare", "osf.io", "deposited", "archive record")),
    ("published", ("published in", "journal of", "proceedings of", "doi:", "accepted for publication")),
    ("draft", ("draft", "work in progress", "manuscript in preparation")),
)

FIELD_META = {
    "title": {"why": "The record must be identifiable by the exact title the source states.", "blocks": True,
              "resolves": "The title as it appears in the source (we prefill it from page 1 or file metadata)."},
    "object_of_study": {"why": "Gate G requires a stated object of study; retrieval compares works by it.", "blocks": True,
                        "resolves": "One sentence naming what the work actually examines."},
    "main_question": {"why": "Gate D requires exactly one main question; the questions index is built from it.", "blocks": True,
                      "resolves": "The single question the work addresses (others go under secondary questions)."},
    "lens": {"why": "Gate G requires the lens or framing so local interpretation stays distinct from the source.", "blocks": True,
             "resolves": "A short statement of the framing you bring to the object."},
    "source_boundary": {"why": "Gate C: the record must say what its sources establish and do not establish.", "blocks": True,
                        "resolves": "Two clauses: what the cited sources support, and what they do not."},
    "authority_boundary": {"why": "Gate E: every Tier-2 record states what it does not claim authority over.", "blocks": True,
                           "resolves": "e.g. 'Claims no Tier-0 or Tier-1 authority and no endorsement of external sources.'"},
    "scope": {"why": "Gate E requires an explicit scope.", "blocks": True, "resolves": "What is inside the work's scope."},
    "exclusions": {"why": "Gate G requires exclusions to be declared (an empty list is allowed).", "blocks": False,
                   "resolves": "Anything explicitly out of scope, one per line, or leave empty."},
    "preserved_meaning": {"why": "External-source discipline: which source-native meaning must not be reinterpreted.", "blocks": True,
                          "resolves": "The source's own meaning that the library must preserve verbatim."},
    "distortion_or_substitution_risk": {"why": "Gate G: the record names where classification could distort the claim.", "blocks": True,
                                        "resolves": "Where a reader could mistake library classification for the source's claim."},
    "missingness": {"why": "Gate E: gaps are recorded with a class instead of guessed; blocking classes prevent admission until resolved.",
                    "blocks": False, "resolves": "One line per gap as CLASS | item | notes, or leave empty if nothing is missing."},
    "next_burden": {"why": "Gate G: every record states what remains untested within its scope.", "blocks": True,
                    "resolves": "The next burden the source itself supports — not a universal experiment."},
    "repair_route": {"why": "Gate G: how the record would be repaired if returned.", "blocks": True,
                     "resolves": "e.g. 'Amend this record and resubmit through the same seven gates.'"},
    "claim_layers": {"why": "Gate C: source observations must stay distinct from local interpretation.", "blocks": True,
                     "resolves": "At least one line as  layer | claim  (source-observation, local-interpretation, translation, structural-mapping, candidate-claim)."},
    "tier2_class.primary": {"why": "Gate D: exactly one controlled Tier-2 class.", "blocks": True, "resolves": "Choose from the taxonomy; we suggest a class when the text supports it."},
    "domain.primary": {"why": "Gate D: a controlled primary domain.", "blocks": True, "resolves": "Choose from the taxonomy; suggestions show which terms matched."},
    "structural_focus.primary": {"why": "Gate D: a controlled structural focus.", "blocks": True, "resolves": "Choose from the taxonomy."},
    "evidence_mode.primary": {"why": "Gate D: a controlled evidence mode.", "blocks": True, "resolves": "Choose from the taxonomy (e.g. simulation, formal-proof, conceptual-argument)."},
    "provenance": {"why": "Gate C: a controlled provenance type.", "blocks": True, "resolves": "corpus-native for your own current work; external-source-native for work you did not author; see the taxonomy."},
    "maturity": {"why": "Gate D: a controlled maturity state.", "blocks": True, "resolves": "Choose from the taxonomy."},
    "functional_locus": {"why": "Gate D: a functional locus (or 'none').", "blocks": True, "resolves": "umcp, rcft, ulrc, cross-system, or none."},
    "publication_state": {"why": "Gate D: a controlled publication state; 'unknown' is allowed and preserved as missingness.", "blocks": True,
                          "resolves": "Choose from the taxonomy; we suggest one when the text states it."},
    "version": {"why": "Gate G: MAJOR.MINOR.PATCH record version.", "blocks": True, "resolves": "1.0.0 for a first registration."},
    "source_ids": {"why": "Gate C: sources are registered SRC-* records; a DOI is not mandatory but source identity is.", "blocks": True,
                   "resolves": "Reuse a matched existing source or add one below with its authors and identifier."},
    "_version": {"why": "Two manuscript versions or titles were found; the record must name the governing version.", "blocks": True,
                 "resolves": "Say which file/version governs this submission and record the other as an earlier version on the source."},
    "_duplicate": {"why": "Library rule H: no duplicate intellectual object. A new version of an existing object advances its version instead of minting a duplicate.",
                   "blocks": True, "resolves": "Choose on the submit page: this is a revision of the matched object, or a distinct study with its own question."},
    "_source_type": {"why": "Source type decides how authorship and claims are preserved.", "blocks": False,
                     "resolves": "Confirm corpus-native (your own current work) or external (work you did not author)."},
}

QUESTION_TEXT = {
    "title": "What is the title of this work, exactly as the source states it?",
    "object_of_study": "What is the object of study — the thing this work actually examines?",
    "main_question": "What single main question does this work address?",
    "lens": "Through what lens or framing does the work approach its object?",
    "source_boundary": "What do the sources establish, and what do they not establish?",
    "authority_boundary": "What does this work not claim authority over?",
    "scope": "What is inside the scope of this work?",
    "exclusions": "What is explicitly excluded?",
    "preserved_meaning": "Which source-native meaning must be preserved rather than reinterpreted?",
    "distortion_or_substitution_risk": "Where could the library's classification distort or substitute the source's claim?",
    "missingness": "What information is missing or unresolved, and which missingness class applies?",
    "next_burden": "What remains untested within the scope of this work — the next burden?",
    "repair_route": "If the record is returned for repair, how would it be repaired?",
    "claim_layers": "Which claims are source observations, and which are local interpretation, translation, structural mapping, or candidate claims?",
    "tier2_class.primary": "Which one Tier-2 class best describes the work?",
    "domain.primary": "Which primary domain applies?",
    "structural_focus.primary": "Which primary structural focus applies?",
    "evidence_mode.primary": "Which primary evidence mode applies?",
    "provenance": "What is the provenance type of this record?",
    "maturity": "What maturity state applies?",
    "functional_locus": "Which functional locus applies (or 'none')?",
    "publication_state": "What is the publication state of the source?",
    "version": "Which version of the record is this (MAJOR.MINOR.PATCH)?",
    "source_ids": "Which source record(s) does this work rest on?",
    "_version": "We found more than one manuscript version or title among your files. Which version governs this submission?",
    "_duplicate": "This looks similar to an existing record. Is this a revision of it, or a distinct study with a new question or contract?",
    "_source_type": "Is the proposed source your own current work (corpus-native) or work you did not author (external)?",
}


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii").lower()


# --------------------------------------------------------------------------- source identification

def identify_sources(text: str, filename: str = "") -> dict:
    """Identifiers and version statements present in the text, each with a line locator."""
    found = {"dois": [], "arxiv": [], "zenodo": [], "urls": [], "versions": [], "publication_hints": []}
    seen: dict = {key: set() for key in found}
    for number, line in enumerate((text or "").splitlines(), start=1):
        for key, pattern in (("dois", DOI_RE), ("arxiv", ARXIV_RE), ("zenodo", ZENODO_RE), ("versions", VERSION_RE)):
            for match in pattern.finditer(line):
                value = match.group(1).rstrip(".,;:")
                if key == "dois":
                    value = value.lower()
                if value not in seen[key]:
                    seen[key].add(value)
                    found[key].append({"value": value, "locator": f"{filename}: line {number}".strip(": ")})
        for match in URL_RE.finditer(line):
            value = match.group(0).rstrip(".,;:)")
            if value not in seen["urls"] and "doi.org" not in value:
                seen["urls"].add(value)
                found["urls"].append({"value": value, "locator": f"{filename}: line {number}".strip(": ")})
    folded = _fold(text)
    for state, hints in PUBLICATION_HINTS:
        hits = [h for h in hints if h in folded]
        if hits:
            found["publication_hints"].append({"value": state, "matched": hits})
    return found


def merge_identifications(per_file: list) -> dict:
    """Combine per-file identifications; detect version ambiguity across files."""
    merged = {"dois": [], "arxiv": [], "zenodo": [], "urls": [], "versions": [], "publication_hints": [], "version_ambiguity": None}
    seen: dict = {key: set() for key in merged if key != "version_ambiguity"}
    for filename, ident in per_file:
        for key in ("dois", "arxiv", "zenodo", "urls", "versions"):
            for item in ident.get(key, []):
                if item["value"] not in seen[key]:
                    seen[key].add(item["value"])
                    merged[key].append(dict(item, file=filename))
        for hint in ident.get("publication_hints", []):
            if hint["value"] not in seen["publication_hints"]:
                seen["publication_hints"].add(hint["value"])
                merged["publication_hints"].append(dict(hint, file=filename))
    versions = sorted({v["value"] for v in merged["versions"]})
    if len(versions) > 1:
        merged["version_ambiguity"] = (f"Version statements {', '.join(versions)} appear across the uploaded files "
                                       f"({', '.join(sorted({v['file'] for v in merged['versions']}))}).")
    return merged


# --------------------------------------------------------------------------- duplicate checks

def _norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", _fold(title)).strip()


def _title_similarity(a: str, b: str) -> float:
    """Sequence ratio, lifted when one title is a long prefix/substring of the other (truncated titles)."""
    if not a or not b:
        return 0.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) >= 40 and shorter in longer:
        ratio = max(ratio, 0.9)
    return ratio


def check_duplicates(title: str, dois: list, file_hashes: list, projection, execution_manifests: dict = None,
                     threshold: float = 0.82) -> list:
    """Compare the candidate against committed objects/sources: DOI identity, title similarity, identical files."""
    findings = []
    doi_values = {d.lower() for d in dois}
    for source in projection.sources.values():
        ident = source.get("identifier") or {}
        source_dois = {v.lower() for v in (ident.get("doi"), source.get("concept_doi"), source.get("version_doi")) if v}
        hit = doi_values & source_dois
        if hit:
            objects = [o["object_id"] for o in projection.objects.values() if source["source_id"] in o.get("source_ids", [])]
            findings.append({"kind": "existing_source", "id": source["source_id"], "title": source.get("title"),
                             "basis": f"DOI {sorted(hit)[0]} matches this registered source", "score": 1.0, "objects": objects})
    normalized = _norm_title(title or "")
    if normalized and len(normalized) > 12:
        for obj in projection.objects.values():
            ratio = _title_similarity(normalized, _norm_title(obj.get("title", "")))
            if ratio >= threshold:
                findings.append({"kind": "possible_duplicate_object", "id": obj["object_id"], "title": obj.get("title"),
                                 "basis": f"title similarity {ratio:.2f}", "score": round(ratio, 3), "version": obj.get("version"),
                                 "authors": obj.get("authors", [])})
        for source in projection.sources.values():
            ratio = _title_similarity(normalized, _norm_title(source.get("title", "")))
            if ratio >= threshold and not any(f["id"] == source["source_id"] for f in findings):
                findings.append({"kind": "possible_duplicate_source", "id": source["source_id"], "title": source.get("title"),
                                 "basis": f"title similarity {ratio:.2f}", "score": round(ratio, 3)})
    hashes = set(file_hashes)
    for receipt_id, manifest in (execution_manifests or {}).items():
        for entry in manifest.get("source_files", []):
            if entry.get("sha256") in hashes:
                findings.append({"kind": "identical_file", "id": receipt_id, "title": manifest.get("submission_identity"),
                                 "basis": f"identical file bytes ({entry.get('display_name')}) recorded on receipt {receipt_id}", "score": 1.0})
    findings.sort(key=lambda f: (-f["score"], f["kind"], f["id"]))
    return findings


# --------------------------------------------------------------------------- classification suggestions

KEYWORDS = {
    "evidence_mode": {
        "simulation": ["simulation", "simulated", "monte carlo", "numerical experiment"],
        "formal-proof": ["theorem", "proof", "lemma", "we prove", "proposition"],
        "formal-derivation": ["derivation", "we derive", "derived from first principles"],
        "experimental": ["experiment", "experimental", "measured", "apparatus", "laboratory"],
        "primary-empirical": ["we collected", "participants", "field data", "survey data", "primary data"],
        "secondary-empirical": ["reanalysis", "secondary data", "meta-analysis", "existing dataset"],
        "retrospective-analysis": ["retrospective", "post hoc", "after the fact"],
        "prospective-protocol": ["prospective", "preregistered", "pre-registered", "frozen protocol", "protocol"],
        "computational-reproduction": ["reproduction", "reproduce", "re-implementation", "replication"],
        "source-synthesis": ["synthesis", "literature review", "survey of", "we synthesize"],
        "conceptual-argument": ["we argue", "conceptual", "argument", "philosophical"],
        "historical": ["historical", "archival", "history of"],
        "pedagogical": ["course", "syllabus", "lecture", "students", "teaching", "tutorial"],
        "translation-only": ["translation only", "translates", "glossary"],
        "no-empirical-validation": ["no empirical validation", "not empirically validated", "untested"],
    },
    "tier2_class": {
        "diagnostic": ["diagnos", "failure mode", "audit", "reliability", "test of"],
        "domain-translation": ["translat", "mapping between", "correspondence between", "in terms of"],
        "pedagogical": ["course", "syllabus", "lecture", "students", "teaching", "tutorial", "guide"],
        "candidate": ["candidate", "we propose", "proposal", "conjecture", "hypothesis"],
        "external-ingress": ["external source", "ingress", "closure around", "external article"],
        "language-contact": ["terminology", "vocabulary", "language contact", "glossary", "nomenclature"],
        "handoff": ["handoff", "hand off", "handed to", "prepared for"],
    },
    "domain": {
        "mathematics": ["theorem", "lemma", "algebra", "topology", "manifold", "proof"],
        "physics": ["physics", "quantum", "thermodynamic", "particle", "spin", "hamiltonian"],
        "chemistry": ["chemistry", "molecule", "reaction", "catalyst"],
        "biology": ["biology", "cell", "protein", "genome", "organism"],
        "medicine": ["clinical", "patient", "medicine", "diagnosis", "therapy"],
        "neuroscience": ["neuron", "neural", "cortex", "brain", "synap"],
        "psychology": ["psycholog", "behavior", "cognition", "participants"],
        "cognitive-science": ["cognitive", "memory", "attention", "representation"],
        "linguistics": ["linguistic", "grammar", "syntax", "semantic", "phonolog"],
        "computer-science": ["algorithm", "software", "computation", "neural network", "associative memory", "memristive", "circuit"],
        "engineering": ["engineering", "hardware", "device", "controller", "sensor"],
        "earth-systems": ["climate", "geolog", "atmosphere", "ocean"],
        "ecology": ["ecolog", "ecosystem", "species", "habitat"],
        "economics": ["econom", "market", "price", "firm"],
        "sociology": ["sociolog", "social network", "institution"],
        "social-science": ["social science", "policy", "survey"],
        "history": ["historical", "archival", "century", "chronicle"],
        "philosophy": ["philosoph", "ontolog", "epistem", "metaphysic"],
        "education": ["education", "curriculum", "classroom", "pedagog"],
        "arts": ["artistic", "aesthetic", "music", "painting"],
        "systems-theory": ["systems theory", "feedback", "dynamical system", "control system"],
        "structura-reditus-core": ["structura reditus", "gcd", "umcp", "rcft", "ulrc", "tier-2", "tier-1", "tier-0", "reditus", "research library"],
    },
    "structural_focus": {
        "return": ["return", "returns", "returning"], "identity": ["identity", "identifiable"], "continuity": ["continuity", "continuous"],
        "recovery": ["recovery", "recover"], "compression": ["compression", "compress"], "heterogeneity": ["heterogene"],
        "translation": ["translation", "translate"], "failure": ["failure", "fails", "failed"], "causation": ["causal", "causation"],
        "recurrence": ["recurrence", "recurrent", "iteration"], "memory": ["memory"], "robustness": ["robust"],
        "residual-migration": ["residual", "migration"], "boundary": ["boundary", "boundaries"], "missingness": ["missing", "missingness"],
        "adaptation": ["adapt"],
    },
    "functional_locus": {"umcp": ["umcp"], "rcft": ["rcft"], "ulrc": ["ulrc"]},
}

AXIS_FIELDS = {"evidence_mode": "evidence_mode.primary", "tier2_class": "tier2_class.primary", "domain": "domain.primary",
               "structural_focus": "structural_focus.primary", "functional_locus": "functional_locus"}


def suggest_classifications(text: str, taxonomies: dict, publication_hints: list = None) -> dict:
    """{field_path: {"term", "matched": [...], "alternatives": [...]}} — deterministic, keyword-based, always uncertain."""
    folded = _fold(text)
    allowed = {
        "evidence_mode": set(taxonomies.get("evidence_modes", [])), "tier2_class": set(taxonomies.get("tier2_classes", [])),
        "domain": set(taxonomies.get("domains", [])), "structural_focus": set(taxonomies.get("focuses", [])),
        "functional_locus": set(taxonomies.get("functional_loci", [])),
    }
    suggestions = {}
    for axis, terms in KEYWORDS.items():
        scores = Counter()
        matched: dict = {}
        for term, keywords in terms.items():
            if term not in allowed.get(axis, set()):
                continue
            for keyword in keywords:
                count = folded.count(keyword)
                if count:
                    scores[term] += count
                    matched.setdefault(term, []).append(f"{keyword} ×{count}")
        if not scores:
            continue
        ranked = scores.most_common()
        top_term, top_score = ranked[0]
        if len(ranked) > 1 and ranked[1][1] == top_score and axis != "structural_focus":
            # A tie is not a suggestion; list the tied terms and let the researcher choose.
            suggestions[AXIS_FIELDS[axis]] = {"term": None, "matched": [], "alternatives": [f"{t} ({s})" for t, s in ranked[:4]],
                                              "note": "tied terms; choose one"}
            continue
        suggestions[AXIS_FIELDS[axis]] = {"term": top_term, "matched": matched[top_term],
                                          "alternatives": [f"{t} ({s})" for t, s in ranked[1:4]]}
        if axis in ("domain", "structural_focus") and len(ranked) > 1:
            suggestions[AXIS_FIELDS[axis]]["secondary"] = [t for t, s in ranked[1:3] if s >= max(1, top_score // 3)]
    for hint in publication_hints or []:
        if hint["value"] in set(taxonomies.get("publication_states", [])):
            suggestions["publication_state"] = {"term": hint["value"], "matched": hint.get("matched", []), "alternatives": []}
            break
    return suggestions


# --------------------------------------------------------------------------- assessment

def _value_at(candidate: dict, path: str):
    head, _, tail = path.partition(".")
    value = candidate.get(head)
    if tail and isinstance(value, dict):
        value = value.get(tail)
    return value


def assess(candidate: dict, evidence_rows: list, findings: list = None, version_ambiguity: str = None,
           source_type_unconfirmed: bool = False) -> dict:
    """Readiness per field and the remaining questions.

    evidence_rows: iterable of objects/dicts with field_path, origin, uncertain.
    Returns {"ready": [...], "needs_confirmation": [...], "missing": [...], "questions": [...]}.
    """
    by_field: dict = {}
    for row in evidence_rows:
        path = row["field_path"] if isinstance(row, dict) else row.field_path
        origin = row["origin"] if isinstance(row, dict) else row.origin
        uncertain = row["uncertain"] if isinstance(row, dict) else row.uncertain
        by_field.setdefault(path, []).append((origin, uncertain))
    ready, confirm, missing, questions = [], [], [], []
    for path, meta in FIELD_META.items():
        if path.startswith("_"):
            continue
        value = _value_at(candidate, path)
        present = value not in (None, "", [], {})
        if not present and path in ("exclusions", "missingness") and path in candidate and isinstance(value, list):
            ready.append(path)  # explicitly declared empty: Gate G accepts an empty list
            continue
        rows = by_field.get(path, [])
        confirmed = any(origin == "researcher-statement" for origin, _ in rows)
        uncertain = any(uncertain for _, uncertain in rows) and not confirmed
        if present and not uncertain:
            ready.append(path)
            continue
        status = "needs_confirmation" if present else "missing"
        (confirm if present else missing).append(path)
        if not present and not meta["blocks"] and path in ("exclusions", "missingness"):
            continue  # optional-empty fields are not asked as questions
        questions.append({"field": path, "question": QUESTION_TEXT[path], "status": status, "why": meta["why"],
                          "blocks": meta["blocks"], "resolves": meta["resolves"]})
    if version_ambiguity and not candidate.get("_version_resolution"):
        questions.insert(0, {"field": "_version", "question": QUESTION_TEXT["_version"], "status": "needs_confirmation",
                             "why": FIELD_META["_version"]["why"], "blocks": True, "resolves": FIELD_META["_version"]["resolves"],
                             "detail": version_ambiguity})
    duplicates = [f for f in (findings or []) if f["kind"] == "possible_duplicate_object"]
    if duplicates and not candidate.get("_duplicate_resolution"):
        questions.insert(0, {"field": "_duplicate", "question": QUESTION_TEXT["_duplicate"], "status": "needs_confirmation",
                             "why": FIELD_META["_duplicate"]["why"], "blocks": True, "resolves": FIELD_META["_duplicate"]["resolves"],
                             "detail": "; ".join(f"{f['id']} — {f['title']} ({f['basis']})" for f in duplicates[:3])})
    if source_type_unconfirmed:
        questions.append({"field": "_source_type", "question": QUESTION_TEXT["_source_type"], "status": "needs_confirmation",
                          "why": FIELD_META["_source_type"]["why"], "blocks": False, "resolves": FIELD_META["_source_type"]["resolves"]})
    blocking_open = [q for q in questions if q["blocks"]]
    for question in questions:
        question["status_label"] = {"missing": "Missing", "needs_confirmation": "Needs confirmation"}.get(question["status"], question["status"])
    return {"ready": ready, "needs_confirmation": confirm, "missing": missing, "questions": questions,
            "blocking_open": len(blocking_open), "submittable": not blocking_open}


def repair_focus(receipt: dict) -> list:
    """Field paths named by a repair/rejection receipt's missing structure or violations."""
    lines = list(receipt.get("missing_structure") or []) + list(receipt.get("fields_still_blocked") or [])
    if receipt.get("established_violation"):
        lines += receipt["established_violation"].split("; ")
    fields = []
    mapping = [
        (r"AuthorID|author reference|authors list", "authors"), (r"SourceID|source_ids", "source_ids"),
        (r"RelationID|relations is missing|relation '", "relations"), (r"governing reference", "governing_refs"),
        (r"missingness", "missingness"), (r"claim_layers", "claim_layers"), (r"authority\.tier|authority", "authority"),
        (r"tier2_class", "tier2_class.primary"), (r"domain\.primary|domain\.secondary", "domain.primary"),
        (r"structural_focus", "structural_focus.primary"), (r"evidence_mode", "evidence_mode.primary"),
    ]
    simple = ["object_id", "title", "provenance", "source_boundary", "main_question", "authority_boundary", "scope", "version",
              "date", "next_burden", "repair_route", "preserved_meaning", "object_of_study", "lens", "distortion_or_substitution_risk",
              "secondary_questions", "exclusions", "notes", "maturity", "functional_locus", "publication_state"]
    for line in lines:
        hit = None
        for pattern, field in mapping:
            if re.search(pattern, line):
                hit = field
                break
        if hit is None:
            for name in simple:
                if re.search(rf"\b{re.escape(name)}\b", line):
                    hit = name
                    break
        if hit and hit not in fields:
            fields.append(hit)
    return fields

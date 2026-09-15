"""Deterministic, bounded extraction of candidate fields from uploaded files.

Document text is untrusted *source material*; it is never executed, rendered
unescaped, or treated as instructions. Parsers keep page/paragraph/line
locators. Nothing is inferred beyond what a parser can point to; every gap
becomes a plain-language question for the researcher.
"""

from __future__ import annotations

import csv
import io
import json
import re
import time
import zipfile
from dataclasses import dataclass, field

import yaml

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".md", ".markdown", ".txt", ".tex", ".json", ".yaml", ".yml", ".csv", ".tsv", ".zip"}
MEDIA_TYPES = {
    ".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown", ".markdown": "text/markdown", ".txt": "text/plain", ".tex": "application/x-tex",
    ".json": "application/json", ".yaml": "application/yaml", ".yml": "application/yaml", ".csv": "text/csv",
    ".tsv": "text/tab-separated-values", ".zip": "application/zip",
}

OBJECT_FIELDS_TEXT = ("title", "lens", "object_of_study", "main_question", "source_boundary", "authority_boundary",
                      "scope", "preserved_meaning", "distortion_or_substitution_risk", "next_burden", "repair_route", "notes")


@dataclass
class Extracted:
    """Candidate fields with locators and the processing record."""

    fields: dict = field(default_factory=dict)        # field_path -> {"value", "locator", "uncertain", "origin"}
    text_excerpt: str = ""
    processing: dict = field(default_factory=dict)
    problems: list = field(default_factory=list)
    members: list = field(default_factory=list)       # archive members: {"name", "bytes", "sha256", "data"}
    record: dict | None = None                        # when the upload *is* a structured record

    def put(self, path: str, value, locator: str, uncertain: bool = False, origin: str = "source-extraction") -> None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return
        self.fields.setdefault(path, {"value": value, "locator": locator, "uncertain": uncertain, "origin": origin})


def suffix_of(filename: str) -> str:
    name = filename.lower()
    for suffix in sorted(SUPPORTED_SUFFIXES, key=len, reverse=True):
        if name.endswith(suffix):
            return suffix
    return ""


def detect_media_type(filename: str, head: bytes) -> str:
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"PK\x03\x04"):
        return MEDIA_TYPES[".docx"] if filename.lower().endswith(".docx") else "application/zip"
    return MEDIA_TYPES.get(suffix_of(filename), "application/octet-stream")


def _clean(text: str, limit: int = 2000) -> str:
    text = re.sub(r"[ \t]+", " ", text or "").strip()
    return text[:limit]


# --------------------------------------------------------------------------- parsers

def extract_pdf(data: bytes, filename: str) -> Extracted:
    from pypdf import PdfReader

    out = Extracted(processing={"parser": "pypdf", "ocr": False})
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        out.problems.append("PDF is encrypted; text could not be read. Complete the fields manually.")
        return out
    meta = reader.metadata or {}
    if meta.get("/Title"):
        out.put("title", _clean(str(meta.get("/Title")), 500), "pdf metadata: Title", uncertain=True)
    if meta.get("/Author"):
        out.put("_source_authors", [a.strip() for a in re.split(r"[;,]| and ", str(meta.get("/Author"))) if a.strip()],
                "pdf metadata: Author", uncertain=True)
    pages_text = []
    for number, page in enumerate(reader.pages[:60], start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001 - a broken page is a problem to report, not a crash
            text = ""
        pages_text.append((number, text))
    total_chars = sum(len(t) for _, t in pages_text)
    if total_chars < 200:
        out.problems.append("Very little text could be extracted (scanned PDF?). OCR was not run; results are uncertain. "
                            "Complete the fields manually or supply a text version.")
        out.processing["ocr_needed"] = True
    if pages_text and "title" not in out.fields:
        first_lines = [l.strip() for l in pages_text[0][1].splitlines() if l.strip()]
        if first_lines:
            out.put("title", _clean(first_lines[0], 500), "page 1, line 1", uncertain=True)
    abstract = _find_abstract("\n".join(t for _, t in pages_text))
    if abstract:
        page = next((n for n, t in pages_text if "abstract" in t.lower()), 1)
        out.put("_abstract", abstract, f"page {page} (Abstract)", uncertain=True)
    out.text_excerpt = _clean("\n".join(t for _, t in pages_text[:3]), 4000)
    out.processing["pages"] = len(reader.pages)
    return out


def extract_docx(data: bytes, filename: str) -> Extracted:
    import docx

    out = Extracted(processing={"parser": "python-docx"})
    document = docx.Document(io.BytesIO(data))
    core = document.core_properties
    if core.title:
        out.put("title", _clean(core.title, 500), "docx core properties: title", uncertain=True)
    if core.author:
        out.put("_source_authors", [a.strip() for a in re.split(r"[;,]", core.author) if a.strip()], "docx core properties: author", uncertain=True)
    paragraphs = [(i, p.text.strip()) for i, p in enumerate(document.paragraphs, start=1) if p.text.strip()]
    if paragraphs and "title" not in out.fields:
        out.put("title", _clean(paragraphs[0][1], 500), f"paragraph {paragraphs[0][0]}", uncertain=True)
    abstract = _find_abstract("\n".join(t for _, t in paragraphs))
    if abstract:
        out.put("_abstract", abstract, "paragraph containing 'Abstract'", uncertain=True)
    out.text_excerpt = _clean("\n".join(t for _, t in paragraphs[:40]), 4000)
    return out


def extract_text_like(data: bytes, filename: str) -> Extracted:
    suffix = suffix_of(filename)
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    out = Extracted(processing={"parser": "text", "kind": suffix.lstrip(".")})
    if suffix == ".tex":
        for macro, path in (("title", "title"), ("author", "_source_authors")):
            match = re.search(r"\\" + macro + r"\*?\s*(\[[^\]]*\])?\s*\{((?:[^{}]|\{[^{}]*\})*)\}", text)
            if match:
                value = re.sub(r"\\\\|\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", match.group(2))
                value = re.sub(r"[{}$~]", "", value)
                line_no = text[: match.start()].count("\n") + 1
                if path == "_source_authors":
                    out.put(path, [a.strip() for a in re.split(r"\\and|,|;", match.group(2)) if a.strip()], f"line {line_no} (\\author)")
                else:
                    out.put(path, _clean(value, 500), f"line {line_no} (\\title)")
        abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.S)
        if abstract:
            out.put("_abstract", _clean(abstract.group(1), 2000), f"line {text[: abstract.start()].count(chr(10)) + 1} (abstract environment)")
    else:
        for number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("# "):
                out.put("title", _clean(stripped[2:], 500), f"line {number} (heading)")
                break
        if "title" not in out.fields:
            first = next(((n, l.strip()) for n, l in enumerate(lines, start=1) if l.strip()), None)
            if first:
                out.put("title", _clean(first[1], 500), f"line {first[0]}", uncertain=True)
        abstract = _find_abstract(text)
        if abstract:
            out.put("_abstract", abstract, "section headed 'Abstract'", uncertain=True)
    out.text_excerpt = _clean("\n".join(lines[:80]), 4000)
    return out


def extract_record(data: bytes, filename: str) -> Extracted:
    """A JSON/YAML research record supplied by the researcher: fields are researcher statements, not extractions."""
    suffix = suffix_of(filename)
    out = Extracted(processing={"parser": "record", "format": suffix.lstrip(".")})
    try:
        record = yaml.safe_load(data.decode("utf-8")) if suffix in (".yaml", ".yml") else json.loads(data.decode("utf-8"))
    except (ValueError, yaml.YAMLError) as exc:
        out.problems.append(f"The file is not valid {suffix.lstrip('.').upper()}: {type(exc).__name__}. Fix the file or complete the fields manually.")
        return out
    if not isinstance(record, dict):
        out.problems.append("The record must be a JSON/YAML object with research-object fields.")
        return out
    out.record = record
    for key, value in record.items():
        out.put(key, value, f"record:{key}", origin="researcher-statement")
    return out


def extract_table(data: bytes, filename: str) -> Extracted:
    delimiter = "\t" if suffix_of(filename) == ".tsv" else ","
    out = Extracted(processing={"parser": "csv"})
    text = data.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    header = rows[0] if rows else []
    out.put("_supporting_data", {"columns": header[:50], "rows": max(0, len(rows) - 1)}, "header row", origin="source-extraction")
    out.text_excerpt = _clean("\n".join(delimiter.join(r) for r in rows[:10]), 2000)
    return out


def _find_abstract(text: str) -> str | None:
    match = re.search(r"abstract[\s:.\-—]*\n?(.{40,2500}?)(?:\n\s*\n|\n\s*(?:1\.?\s+)?introduction\b|keywords\b)", text, re.I | re.S)
    if match:
        return _clean(match.group(1), 2000)
    return None


# --------------------------------------------------------------------------- archives

class ArchiveLimit(RuntimeError):
    """Bounded expansion, member count, nesting depth, or time budget exceeded — an intake issue, never a rejection."""


def expand_zip(data: bytes, *, max_members: int, max_expanded_bytes: int, max_depth: int, per_file_bytes: int,
               time_budget: float, _depth: int = 1, _started: float = None) -> list:
    """Return [{name, bytes, data}] for members, refusing unsafe or oversized content."""
    started = _started or time.monotonic()
    members = []
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = [i for i in archive.infolist() if not i.is_dir()]
        if len(infos) > max_members:
            raise ArchiveLimit(f"archive has {len(infos)} members; the limit is {max_members}")
        for info in infos:
            if time.monotonic() - started > time_budget:
                raise ArchiveLimit("archive processing exceeded its time budget")
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in name.split("/") or "\x00" in name:
                raise ArchiveLimit(f"archive member has an unsafe path: {name[:80]}")
            if info.file_size > per_file_bytes:
                raise ArchiveLimit(f"archive member {name[:80]} is larger than the per-file limit")
            total += info.file_size
            if total > max_expanded_bytes:
                raise ArchiveLimit("archive expands beyond the total size limit")
            payload = archive.open(info).read(per_file_bytes + 1)
            if len(payload) > per_file_bytes:
                raise ArchiveLimit(f"archive member {name[:80]} declared a smaller size than it contains")
            if name.lower().endswith(".zip"):
                if _depth >= max_depth:
                    raise ArchiveLimit(f"archive nesting deeper than {max_depth} levels")
                for nested in expand_zip(payload, max_members=max_members, max_expanded_bytes=max_expanded_bytes,
                                         max_depth=max_depth, per_file_bytes=per_file_bytes, time_budget=time_budget,
                                         _depth=_depth + 1, _started=started):
                    nested["name"] = f"{name}/{nested['name']}"
                    members.append(nested)
                continue
            members.append({"name": name, "bytes": len(payload), "data": payload})
    return members


# --------------------------------------------------------------------------- dispatch

def extract(data: bytes, filename: str) -> Extracted:
    suffix = suffix_of(filename)
    if suffix == ".pdf":
        return extract_pdf(data, filename)
    if suffix == ".docx":
        return extract_docx(data, filename)
    if suffix in (".json", ".yaml", ".yml"):
        return extract_record(data, filename)
    if suffix in (".csv", ".tsv"):
        return extract_table(data, filename)
    if suffix in (".md", ".markdown", ".txt", ".tex"):
        return extract_text_like(data, filename)
    out = Extracted(processing={"parser": None})
    out.problems.append(f"Unsupported file type for automatic preparation: {filename[-40:]}. The file is saved; complete the fields manually.")
    return out


# --------------------------------------------------------------------------- candidate assembly

REQUIRED_QUESTIONS = {
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
    "next_burden": "What remains untested within the scope of this work — the next burden?",
    "repair_route": "If the record is returned for repair, how would it be repaired?",
    "claim_layers": "Which claims are source observations, and which are local interpretation, translation, structural mapping, or candidate claims?",
    "missingness": "What information is missing or unresolved, and which missingness class applies?",
    "tier2_class.primary": "Which one Tier-2 class best describes the work (library classification)?",
    "domain.primary": "Which primary domain applies (library classification)?",
    "structural_focus.primary": "Which primary structural focus applies (library classification)?",
    "evidence_mode.primary": "Which primary evidence mode applies (library classification)?",
    "provenance": "What is the provenance type of this record?",
    "maturity": "What maturity state applies?",
    "functional_locus": "Which functional locus applies (or 'none')?",
    "publication_state": "What is the publication state of the source?",
    "version": "Which version of the record is this (MAJOR.MINOR.PATCH)?",
}


def assemble_candidate(extractions: list, existing: dict, owner_author_id: str | None, source_reference: str = "") -> tuple:
    """Merge extractions into a candidate record; return (candidate, evidence rows, questions, problems)."""
    candidate = dict(existing or {})
    evidence = []
    problems = []
    source_authors: list = []
    abstracts = []
    for upload_id, filename, extracted in extractions:
        problems += [f"{filename}: {p}" for p in extracted.problems]
        if extracted.record:
            for key, value in extracted.record.items():
                if key not in candidate or not candidate.get(key):
                    candidate[key] = value
                evidence.append((key, "researcher-statement", f"record:{key}", upload_id, str(value)[:500], False, extracted.processing))
            continue
        for path, info in extracted.fields.items():
            if path == "_source_authors":
                source_authors += [a for a in info["value"] if a not in source_authors]
                evidence.append(("_source_authors", "source-extraction", info["locator"], upload_id, ", ".join(info["value"])[:500], info["uncertain"], extracted.processing))
            elif path == "_abstract":
                abstracts.append((info["value"], info["locator"], upload_id))
                evidence.append(("_abstract", "source-extraction", info["locator"], upload_id, info["value"][:500], info["uncertain"], extracted.processing))
            elif path == "_supporting_data":
                evidence.append(("_supporting_data", "source-extraction", info["locator"], upload_id, json.dumps(info["value"])[:500], False, extracted.processing))
            else:
                if not candidate.get(path):
                    candidate[path] = info["value"]
                evidence.append((path, info["origin"], info["locator"], upload_id, str(info["value"])[:500], info["uncertain"], extracted.processing))
    candidate.setdefault("authority", {"tier": "tier-2"})
    candidate.setdefault("authors", [owner_author_id] if owner_author_id else [])
    candidate.setdefault("tier2_class", {"primary": "", "secondary": []})
    candidate.setdefault("domain", {"primary": "", "secondary": []})
    candidate.setdefault("structural_focus", {"primary": "", "secondary": []})
    candidate.setdefault("evidence_mode", {"primary": "", "secondary": []})
    candidate.setdefault("secondary_questions", [])
    candidate.setdefault("claim_layers", [])
    candidate.setdefault("relations", [])
    candidate.setdefault("source_ids", [])
    candidate.setdefault("exclusions", [])
    candidate.setdefault("missingness", [])
    candidate.setdefault("version", "1.0.0")
    candidate.setdefault("notes", "")
    if abstracts and not candidate.get("_abstract_hint"):
        candidate["_abstract_hint"] = abstracts[0][0]
    if source_authors:
        candidate["_source_authors_hint"] = source_authors
    if source_reference:
        candidate["_source_reference_hint"] = source_reference
    questions = []
    for path, question in REQUIRED_QUESTIONS.items():
        head, _, tail = path.partition(".")
        value = candidate.get(head)
        if tail and isinstance(value, dict):
            value = value.get(tail)
        if value in (None, "", [], {}):
            questions.append({"field": path, "question": question})
    if len(extractions) > 1 and any(e.processing.get("parser") in ("pypdf", "python-docx", "text") for _, _, e in extractions):
        titles = {e.fields.get("title", {}).get("value") for _, _, e in extractions if e.fields.get("title")}
        if len(titles) > 1:
            questions.insert(0, {"field": "_version", "question": "We found more than one manuscript version or title among your files. Which version governs this submission?"})
    return candidate, evidence, questions, problems

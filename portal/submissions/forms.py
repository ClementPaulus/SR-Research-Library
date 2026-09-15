"""Guided record editor forms covering every required object-schema field, plus proposed sources and relations."""

from __future__ import annotations

import re

from django import forms
from django.conf import settings

from registry_bridge.engine import import_engine

_TAXONOMIES = None


def taxonomies() -> dict:
    global _TAXONOMIES
    if _TAXONOMIES is None:
        _TAXONOMIES = import_engine(settings.PORTAL_REGISTRY_REPO_PATH)["loader"].load_taxonomies()
    return _TAXONOMIES


def _choices(terms, blank="— choose —"):
    return [("", blank)] + [(t, t) for t in terms]


def _lines(value: str) -> list:
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def _ids(value: str, pattern: str) -> list:
    items = [v.strip() for v in re.split(r"[,\s]+", value or "") if v.strip()]
    bad = [v for v in items if not re.match(pattern, v)]
    if bad:
        raise forms.ValidationError(f"Not valid identifiers: {', '.join(bad)}")
    return items


CLAIM_LAYERS = ["source-observation", "local-interpretation", "translation", "structural-mapping", "candidate-claim"]


class DraftForm(forms.Form):
    """Plain-language main flow; identifiers and JSON live in the expandable advanced view."""

    title = forms.CharField(label="Title (exactly as the source states it)", max_length=1000, widget=forms.Textarea(attrs={"rows": 2}))
    object_of_study = forms.CharField(label="What does this work actually examine?", widget=forms.Textarea(attrs={"rows": 2}))
    main_question = forms.CharField(label="What single main question does it address?", widget=forms.Textarea(attrs={"rows": 2}))
    secondary_questions = forms.CharField(label="Other questions (one per line)", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    lens = forms.CharField(label="Through what lens or framing?", widget=forms.Textarea(attrs={"rows": 2}))
    claim_layers = forms.CharField(
        label="Claims, one per line, as  layer | claim",
        help_text="Layers: " + ", ".join(CLAIM_LAYERS) + ". Source observations must stay distinct from your local interpretation.",
        widget=forms.Textarea(attrs={"rows": 5}))
    source_boundary = forms.CharField(label="What do the sources establish, and what do they not?", widget=forms.Textarea(attrs={"rows": 2}))
    authority_boundary = forms.CharField(label="What does this work not claim authority over?", widget=forms.Textarea(attrs={"rows": 2}))
    scope = forms.CharField(label="What is inside the scope?", widget=forms.Textarea(attrs={"rows": 2}))
    exclusions = forms.CharField(label="What is explicitly excluded? (one per line)", required=False, widget=forms.Textarea(attrs={"rows": 2}))
    preserved_meaning = forms.CharField(label="Which source-native meaning must be preserved?", widget=forms.Textarea(attrs={"rows": 2}))
    distortion_or_substitution_risk = forms.CharField(label="Where could classification distort or substitute the source's claim?", widget=forms.Textarea(attrs={"rows": 2}))
    missingness = forms.CharField(
        label="Missing or unresolved information, one per line, as  CLASS | item | notes",
        required=False, help_text="Record gaps instead of guessing. Blocking classes (EVALUABILITY_BLOCKING, REPAIRABLE, CONTRACT_VIOLATING) prevent admission until resolved.",
        widget=forms.Textarea(attrs={"rows": 3}))
    next_burden = forms.CharField(label="What remains untested within the scope of this work?", widget=forms.Textarea(attrs={"rows": 2}))
    repair_route = forms.CharField(label="If returned for repair, how would it be repaired?", widget=forms.Textarea(attrs={"rows": 2}))
    notes = forms.CharField(label="Notes", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    tier2_class_primary = forms.ChoiceField(label="Tier-2 class (library classification)")
    tier2_class_secondary = forms.MultipleChoiceField(label="Secondary Tier-2 classes", required=False)
    domain_primary = forms.ChoiceField(label="Primary domain")
    domain_secondary = forms.MultipleChoiceField(label="Secondary domains", required=False)
    structural_focus_primary = forms.ChoiceField(label="Primary structural focus")
    structural_focus_secondary = forms.MultipleChoiceField(label="Secondary structural focuses", required=False)
    evidence_mode_primary = forms.ChoiceField(label="Primary evidence mode")
    evidence_mode_secondary = forms.MultipleChoiceField(label="Secondary evidence modes", required=False)
    provenance = forms.ChoiceField(label="Provenance")
    maturity = forms.ChoiceField(label="Maturity")
    functional_locus = forms.ChoiceField(label="Functional locus")
    publication_state = forms.ChoiceField(label="Publication state of the source")

    authors = forms.CharField(label="AuthorIDs (comma-separated)", help_text="Your own AuthorID is added automatically. Other authors' IDs require attribution review.")
    source_ids = forms.CharField(label="SourceIDs (registered SRC-* or proposed SRC-NEW-*)", required=False)
    relations = forms.CharField(label="RelationIDs (registered REL-* or proposed REL-NEW-*)", required=False)
    governing_refs = forms.CharField(label="Governing references (SR-GOV-*)", required=False, help_text="Optional; constrains the record and transfers no authority.")
    version = forms.RegexField(label="Record version", regex=r"^[0-9]+\.[0-9]+\.[0-9]+$", initial="1.0.0")
    date = forms.RegexField(label="Record date (ISO 8601 with time zone; blank = now)", required=False,
                            regex=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})$")
    supersedes = forms.RegexField(label="Supersedes ObjectID", required=False, regex=r"^SR-OBJ-[0-9]{6}$")

    def __init__(self, *args, taxonomies: dict, **kwargs):
        super().__init__(*args, **kwargs)
        t = taxonomies
        self.fields["tier2_class_primary"].choices = _choices(t["tier2_classes"])
        self.fields["tier2_class_secondary"].choices = [(x, x) for x in t["tier2_classes"]]
        self.fields["domain_primary"].choices = _choices(t["domains"])
        self.fields["domain_secondary"].choices = [(x, x) for x in t["domains"]]
        self.fields["structural_focus_primary"].choices = _choices(t["focuses"])
        self.fields["structural_focus_secondary"].choices = [(x, x) for x in t["focuses"]]
        self.fields["evidence_mode_primary"].choices = _choices(t["evidence_modes"])
        self.fields["evidence_mode_secondary"].choices = [(x, x) for x in t["evidence_modes"]]
        self.fields["provenance"].choices = _choices(t["provenance_types"])
        self.fields["maturity"].choices = _choices(t["maturity_states"])
        self.fields["functional_locus"].choices = _choices(t["functional_loci"])
        self.fields["publication_state"].choices = _choices(t["publication_states"])
        self.missingness_classes = t["missingness_classes"]
        # Saving a partial draft must be possible; only confirmation requires completeness.
        for field in self.fields.values():
            field.required = False

    @classmethod
    def from_submission(cls, submission, taxonomies: dict):
        d = submission.draft or {}

        def axis(name):
            v = d.get(name) or {}
            return (v.get("primary", ""), v.get("secondary", [])) if isinstance(v, dict) else (v, [])

        initial = {k: d.get(k, "") for k in ("title", "object_of_study", "main_question", "lens", "source_boundary", "authority_boundary",
                                              "scope", "preserved_meaning", "distortion_or_substitution_risk", "next_burden", "repair_route",
                                              "notes", "provenance", "maturity", "functional_locus", "publication_state", "version", "date", "supersedes")}
        initial["secondary_questions"] = "\n".join(d.get("secondary_questions") or [])
        initial["exclusions"] = "\n".join(d.get("exclusions") or [])
        initial["claim_layers"] = "\n".join(f"{c.get('layer', '')} | {c.get('claim', '')}" for c in d.get("claim_layers") or [] if isinstance(c, dict))
        initial["missingness"] = "\n".join(f"{m.get('class', '')} | {m.get('item', '')} | {m.get('notes', '')}".rstrip(" |")
                                           for m in d.get("missingness") or [] if isinstance(m, dict))
        for name in ("tier2_class", "domain", "structural_focus", "evidence_mode"):
            primary, secondary = axis(name)
            initial[f"{name}_primary"], initial[f"{name}_secondary"] = primary, secondary
        initial["authors"] = ", ".join(d.get("authors") or ([submission.owner.author_id] if submission.owner.author_id else []))
        initial["source_ids"] = ", ".join(d.get("source_ids") or [])
        initial["relations"] = ", ".join(d.get("relations") or [])
        initial["governing_refs"] = ", ".join(d.get("governing_refs") or [])
        initial["version"] = d.get("version") or "1.0.0"
        return cls(initial=initial, taxonomies=taxonomies)

    def clean_claim_layers(self):
        rows = []
        for line in _lines(self.cleaned_data.get("claim_layers")):
            layer, _, claim = line.partition("|")
            layer, claim = layer.strip(), claim.strip()
            if layer not in CLAIM_LAYERS:
                raise forms.ValidationError(f"Unknown claim layer '{layer}'. Use one of: {', '.join(CLAIM_LAYERS)}")
            if not claim:
                raise forms.ValidationError("Each claim line needs text after the '|'.")
            rows.append({"layer": layer, "claim": claim})
        return rows

    def clean_missingness(self):
        rows = []
        for line in _lines(self.cleaned_data.get("missingness")):
            parts = [p.strip() for p in line.split("|")]
            cls = parts[0] if parts else ""
            if cls not in self.missingness_classes:
                raise forms.ValidationError(f"Unknown missingness class '{cls}'. Use one of: {', '.join(self.missingness_classes)}")
            if len(parts) < 2 or not parts[1]:
                raise forms.ValidationError("Each missingness line needs an item after the class.")
            entry = {"item": parts[1], "class": cls}
            if len(parts) > 2 and parts[2]:
                entry["notes"] = parts[2]
            rows.append(entry)
        return rows

    def clean_authors(self):
        return _ids(self.cleaned_data.get("authors"), r"^AUTH-[0-9]{4}$")

    def clean_source_ids(self):
        return _ids(self.cleaned_data.get("source_ids"), r"^(SRC-[0-9]{6}|SRC-NEW-[A-Za-z0-9_-]{1,40})$")

    def clean_relations(self):
        return _ids(self.cleaned_data.get("relations"), r"^(REL-[0-9]{6}|REL-NEW-[A-Za-z0-9_-]{1,40})$")

    def clean_governing_refs(self):
        return _ids(self.cleaned_data.get("governing_refs"), r"^SR-GOV-[0-9]{6}$")

    def to_record(self, submission) -> tuple:
        c = self.cleaned_data
        d = dict(submission.draft or {})
        record = {k: v for k, v in d.items() if k.startswith("_")}  # keep hints
        record.update({
            "object_id": d.get("object_id") or ("SR-OBJ-NEW" if not submission.intended_object_id else submission.intended_object_id),
            "title": c["title"], "authors": c["authors"] or ([submission.owner.author_id] if submission.owner.author_id else []),
            "authority": {"tier": "tier-2"},
            "tier2_class": {"primary": c["tier2_class_primary"], "secondary": c["tier2_class_secondary"]},
            "functional_locus": c["functional_locus"], "source_ids": c["source_ids"], "lens": c["lens"],
            "domain": {"primary": c["domain_primary"], "secondary": c["domain_secondary"]},
            "object_of_study": c["object_of_study"],
            "structural_focus": {"primary": c["structural_focus_primary"], "secondary": c["structural_focus_secondary"]},
            "main_question": c["main_question"], "secondary_questions": _lines(c["secondary_questions"]),
            "claim_layers": c["claim_layers"],
            "evidence_mode": {"primary": c["evidence_mode_primary"], "secondary": c["evidence_mode_secondary"]},
            "provenance": c["provenance"], "maturity": c["maturity"], "relations": c["relations"],
            "version": c["version"] or "1.0.0", "publication_state": c["publication_state"],
            "source_boundary": c["source_boundary"], "authority_boundary": c["authority_boundary"], "scope": c["scope"],
            "exclusions": _lines(c["exclusions"]), "preserved_meaning": c["preserved_meaning"], "missingness": c["missingness"],
            "distortion_or_substitution_risk": c["distortion_or_substitution_risk"], "next_burden": c["next_burden"],
            "repair_route": c["repair_route"], "notes": c["notes"] or "",
        })
        if c["governing_refs"]:
            record["governing_refs"] = c["governing_refs"]
        if c["date"]:
            record["date"] = c["date"]
        if c["supersedes"]:
            record["supersedes"] = c["supersedes"]
        return record, submission.proposed_sources or {}, submission.proposed_relations or {}


class ProposedSourceForm(forms.Form):
    title = forms.CharField(label="Source title", max_length=1000)
    source_type = forms.ChoiceField(choices=[(x, x) for x in ("external", "corpus-native", "historical", "dataset")])
    source_authors = forms.CharField(label="Source authors (one per line, exactly as attributable)", widget=forms.Textarea(attrs={"rows": 2}))
    doi = forms.RegexField(label="DOI (only if the source establishes it)", required=False, regex=r"^10\.[0-9]{4,9}/\S+$")
    url = forms.URLField(label="Canonical or archive URL", required=False)
    archive_reference = forms.CharField(label="Archive reference", required=False, max_length=300)
    publication_year = forms.IntegerField(required=False, min_value=1000, max_value=2100)
    venue = forms.CharField(required=False, max_length=300)
    version = forms.CharField(label="Source version (as stated)", required=False, max_length=100)
    source_native_claims = forms.CharField(label="Claims the source itself makes (one per line)", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    missingness = forms.CharField(label="Unavailable metadata (one per line)", required=False, widget=forms.Textarea(attrs={"rows": 2}))
    ambiguous_version = forms.CharField(label="Version ambiguity (leave blank if none)", required=False, max_length=500,
                                        help_text="e.g. 'Two manuscript versions were uploaded; the DOI resolves to v2.'")
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def to_record(self, submission) -> tuple:
        c = self.cleaned_data
        n = len(submission.proposed_sources or {}) + 1
        placeholder = f"SRC-NEW-{n}"
        while placeholder in (submission.proposed_sources or {}):
            n += 1
            placeholder = f"SRC-NEW-{n}"
        identifier = {}
        if c.get("doi"):
            identifier["doi"] = c["doi"]
            identifier["url"] = f"https://doi.org/{c['doi']}"
        elif c.get("url"):
            identifier["url"] = c["url"]
        if c.get("archive_reference"):
            identifier["archive_reference"] = c["archive_reference"]
        links = []
        if c.get("doi"):
            links.append({"label": "Canonical DOI", "type": "canonical", "url": f"https://doi.org/{c['doi']}", "preferred": True})
        elif c.get("url"):
            links.append({"label": "Source page", "type": "canonical", "url": c["url"], "preferred": True})
        missing = _lines(c.get("missingness"))
        if not c.get("doi") and not c.get("url") and not c.get("archive_reference"):
            missing.append("No DOI, URL, or archive reference was supplied; source identity rests on the uploaded manuscript.")
        if not c.get("publication_year"):
            missing.append("No publication year supplied.")
        record = {
            "source_id": placeholder, "source_type": c["source_type"], "title": c["title"],
            "source_authors": _lines(c["source_authors"]), "source_native_claims": _lines(c.get("source_native_claims")),
            "identifier": identifier, "publication_year": c.get("publication_year"), "venue": c.get("venue") or None,
            "links": links, "missingness": missing, "status": "active", "notes": c.get("notes") or "",
        }
        if c.get("version"):
            record["version"] = c["version"]
        if c.get("ambiguous_version"):
            record["_ambiguous_version"] = c["ambiguous_version"]
        return placeholder, record


class ProposedRelationForm(forms.Form):
    relation_type = forms.ChoiceField()
    to_id = forms.RegexField(label="Target (SR-OBJ-* or SRC-* / proposed SRC-NEW-*)", regex=r"^(SR-OBJ-[0-9]{6}|SRC-[0-9]{6}|SRC-NEW-[A-Za-z0-9_-]{1,40})$")
    evidence = forms.CharField(label="What evidence supports this proposed connection?", widget=forms.Textarea(attrs={"rows": 3}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["relation_type"].choices = [(x, x) for x in taxonomies()["relation_types"]]

    def to_record(self, submission) -> tuple:
        c = self.cleaned_data
        n = len(submission.proposed_relations or {}) + 1
        placeholder = f"REL-NEW-{n}"
        return placeholder, {"relation_id": placeholder, "relation_type": c["relation_type"], "from_id": "SR-OBJ-NEW",
                             "to_id": c["to_id"], "notes": c.get("notes") or "", "evidence": c["evidence"]}

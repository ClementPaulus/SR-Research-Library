"""Browser journeys against a live dev server (headless Chromium).

    python portal/tests/browser_journeys.py http://127.0.0.1:8123 /tmp/portal-mail docs/portal-evidence/journeys [--outage-file PATH --reconcile-cmd "..."]

Journeys (each writes screenshots and a JSON ledger; fixtures are synthetic and describe only the library's own machinery):
  J1  new researcher: sign up → verify → automatic AuthorID → upload a PDF manuscript → review prepared draft
      (progress steps, readiness, evidence per field, suggestions kept by saving) → answer remaining questions → submit → Registered
  J2  ambiguous submission: two manuscript versions + a near-duplicate title → version and duplicate questions must be resolved
  J3  repair: submit with a missing required field → RETURNED_FOR_REPAIR → Start repair (flagged fields, evidence reused) → resubmit → Registered
  J4  interruption: GitHub unavailable after ACCEPTED → "Accepted — awaiting registration" → outage ends → reconcile → Registered, one receipt
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pdf_fixture import make_pdf  # noqa: E402

PASSWORD = "journey-acceptance-passphrase-77"


def manuscript(title: str, version: str, extra: str = "") -> bytes:
    lines = [
        title, "Synthetic Researcher", f"Version {version} (2026-09-14). Preprint; not peer reviewed.",
        "This manuscript is a synthetic acceptance fixture: it describes only the research library's own intake machinery.", "",
        "Abstract",
        "We test whether the intake pipeline's bounded ZIP expansion returns the same member set under repeated runs. In a simulation of "
        "two hundred synthetic archives the simulated pipeline returned identical member sets in every run; one archive with a nested depth "
        "of four failed as designed. The failure is reported as a result, not as missing information." + extra, "",
        "Introduction",
        "The pipeline is a diagnostic of the library's own robustness. Bounded expansion, member-count limits and a time budget are the "
        "contract under test; nothing here is a scholarly claim about any external domain.", "",
        "Method", "Two hundred synthetic archives were generated with controlled depth and member counts and passed through the expansion "
        "routine ten times each. Identity of the returned member set was checked by hashing.", "",
        "Result", "All archives within the contract returned identical member sets on every run. The single archive nested beyond depth "
        "three was refused each time, as the contract requires.",
    ]
    return make_pdf(lines, title=title, author="Synthetic Researcher")


TERMINAL = {"Registered", "Needs repair", "Not admitted", "Review needed", "Processing unavailable", "Needs your review"}


class Journey:
    def __init__(self, base: str, mail_dir: Path, out: Path, browser):
        self.base, self.mail_dir, self.out, self.browser = base, mail_dir, out, browser
        self.ledger: dict = {}
        self.shot = 0

    # ------------------------------------------------------------------ helpers
    def snap(self, page, name: str) -> None:
        self.shot += 1
        page.screenshot(path=str(self.out / f"{self.shot:02d}-{name}.png"), full_page=True)

    def confirm_link(self, email: str) -> str:
        deadline = time.time() + 20
        while time.time() < deadline:
            text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in sorted(self.mail_dir.glob("*.log")))
            text = text.replace("=\n", "").replace("=3D", "=")
            for chunk in text.split("Subject:"):
                if email in chunk:
                    links = re.findall(r"https?://[^\s\"<>]+/accounts/confirm-email/[^\s/\"<>]+/", chunk)
                    if links:
                        return links[-1]
            time.sleep(0.5)
        raise SystemExit("verification email not captured")

    def signup(self, page, email: str, name: str) -> str:
        page.goto(f"{self.base}/signup")
        page.fill("#id_display_name", name)
        page.fill("#id_email", email)
        page.fill("#id_password1", PASSWORD)
        page.fill("#id_password2", PASSWORD)
        page.check("#id_accept_terms")
        page.click("main form button[type=submit]")
        page.wait_for_load_state("networkidle")
        page.goto(self.confirm_link(email))
        page.wait_for_load_state("networkidle")
        if page.locator("main form button[type=submit]").count() and "confirm" in page.content().lower():
            page.click("main form button[type=submit]")
            page.wait_for_load_state("networkidle")
        self.login(page, email)
        for _ in range(30):
            badge = re.search(r"(AUTH-[0-9]{4}) · ([a-z_]+)", page.content())
            if badge and badge.group(2) in ("registered", "linked"):
                return badge.group(1)
            time.sleep(1)
            page.reload()
        raise SystemExit("author registration did not complete")

    def login(self, page, email: str) -> None:
        page.goto(f"{self.base}/login")
        page.fill("#id_login", email)
        page.fill("#id_password", PASSWORD)
        page.click("main form button[type=submit]")
        page.wait_for_url(re.compile(r".*/workspace/?$"), timeout=20000)

    def upload(self, page, files: list, label: str) -> str:
        page.goto(f"{self.base}/workspace/submissions/new")
        page.fill("#label", label)
        page.set_input_files("#files", [str(f) for f in files])
        page.click("main form button[type=submit]")
        page.wait_for_load_state("networkidle")
        return page.url

    def wait_state(self, page, wanted: set, timeout: int = 180) -> str:
        deadline = time.time() + timeout
        state = ""
        while time.time() < deadline:
            state = page.locator("#state-badge").inner_text().strip()
            if state in wanted:
                return state
            time.sleep(2)
            page.reload()
            page.wait_for_load_state("networkidle")
        return state

    def fill_missing(self, page, values: dict) -> None:
        for field, value in values.items():
            locator = page.locator(f"#id_{field}")
            if locator.count() == 0:
                continue
            tag = locator.evaluate("e => e.tagName")
            if tag == "SELECT":
                locator.select_option(value)
            else:
                locator.fill(value)

    def readiness(self, page) -> dict:
        text = page.locator(".readiness").inner_text()
        counts = {k: int(re.search(rf"(\d+) {k}", text).group(1)) for k in ("ready", "to confirm", "missing") if re.search(rf"(\d+) {k}", text)}
        counts["blocking"] = int(m.group(1)) if (m := re.search(r"(\d+) blocking question", text)) else 0
        return counts

    # ------------------------------------------------------------------ journeys
    def j1_new_researcher(self) -> dict:
        page = self.browser.new_page(viewport={"width": 1280, "height": 900})
        page.set_default_timeout(120000)
        email = f"j1-{int(time.time())}@example.invalid"
        led = {"email": email}
        led["author_id"] = self.signup(page, email, "Journey One Researcher")
        self.snap(page, "j1-workspace-author-assigned")
        pdf = self.out / "j1-manuscript-v2.pdf"
        pdf.write_bytes(manuscript("Bounded Archive Expansion in the Structura Reditus Intake Pipeline", "2"))
        detail = self.upload(page, [pdf], "Bounded archive expansion (journey 1)")
        led["detail_url"] = detail
        self.snap(page, "j1-uploaded-detail")
        led["state_after_upload"] = self.wait_state(page, {"Needs your review"}, 60)
        steps = json.loads(page.evaluate(f"fetch('{detail}/status.json',{{headers:{{Accept:'application/json'}}}}).then(r=>r.text())"))["steps"]
        led["preparation_steps"] = [(s["key"], s["status"]) for s in steps]
        led["duplicates_detail"] = next(s["detail"] for s in steps if s["key"] == "duplicates")
        page.click("text=Review and edit the draft")
        page.wait_for_load_state("networkidle")
        self.snap(page, "j1-editor-readiness")
        led["readiness_initial"] = self.readiness(page)
        led["title_prefilled"] = page.input_value("#id_title")
        led["evidence_mode_suggested"] = page.input_value("#id_evidence_mode_primary")
        led["tier2_class_suggested"] = page.input_value("#id_tier2_class_primary")
        led["publication_state_suggested"] = page.input_value("#id_publication_state")
        led["evidence_rows_with_locators"] = page.locator(".field-evidence").count()
        led["classification_origin_visible"] = page.locator(".origin-library-classification").count() > 0
        led["uncertain_marked"] = page.locator(".field-evidence em:has-text('uncertain')").count()
        # Answer only what is still missing; keep the extracted/suggested values (saving confirms them).
        self.fill_missing(page, {
            "object_of_study": "The intake pipeline's bounded ZIP expansion routine.",
            "main_question": "Does bounded archive expansion return identical member sets under repeated runs?",
            "lens": "Diagnostic of the library's own intake machinery.",
            "claim_layers": "source-observation | The simulated pipeline returned identical member sets in every run; one archive nested beyond depth three failed as designed.\nlocal-interpretation | A bounded expansion contract is a prerequisite for reproducible intake.",
            "source_boundary": "The manuscript establishes the simulated behaviour of the expansion routine; it does not establish behaviour on real-world archives.",
            "authority_boundary": "Claims no Tier-0 or Tier-1 authority and no endorsement of any external source.",
            "scope": "The library's own intake pipeline under synthetic archives.",
            "preserved_meaning": "The failure of the deeply nested archive is a designed refusal, not missing information.",
            "distortion_or_substitution_risk": "Classifying the work as diagnostic could be mistaken for a claim about external archives; none is made.",
            "missingness": "NON_BLOCKING | Behaviour on real-world archives | Only synthetic archives were used.",
            "next_burden": "Run the same expansion contract on real-world archive samples.",
            "repair_route": "Amend this record and resubmit through the same seven gates.",
            "structural_focus_primary": "robustness", "provenance": "corpus-native", "maturity": "prospectively-tested", "functional_locus": "none",
        })
        page.click("#draft-form button[value=save]")
        page.wait_for_load_state("networkidle")
        led["readiness_after_answers"] = self.readiness(page)
        led["title_confirmed_on_save"] = page.locator(".field-evidence:has-text('confirmed in the editor')").count() > 0
        self.snap(page, "j1-editor-answered")
        page.click("#draft-form button[value=preview]")
        page.wait_for_load_state("networkidle")
        self.snap(page, "j1-confirm")
        led["source_type_question_shown"] = page.locator("#st-corpus").count() > 0
        if page.locator("#st-corpus").count():
            page.check("#st-corpus")
        page.check("#acknowledge_claims")
        page.check("#acknowledge")
        page.click("main form button.primary")
        page.wait_for_load_state("networkidle")
        led["final_state"] = self.wait_state(page, TERMINAL, 240)
        self.snap(page, "j1-registered")
        body = page.content()
        led["receipt_id"] = (re.search(r"RCPT-[0-9]{6}", body) or [None])[0] if False else (m.group(0) if (m := re.search(r"RCPT-[0-9]{6}", body)) else None)
        led["object_id"] = m.group(1) if (m := re.search(r"/research/(SR-OBJ-[0-9]{6})", body)) else None
        led["profile_link_shown"] = f"/authors/{led['author_id']}" in body
        if led["object_id"]:
            page.goto(f"{self.base}/research/{led['object_id']}")
            page.wait_for_load_state("networkidle")
            self.snap(page, "j1-public-record")
            led["public_record_shows_source_and_receipt"] = "SRC-" in page.content() and (led["receipt_id"] or "") in page.content()
            page.goto(f"{self.base}/research?q=bounded+archive+expansion")
            led["searchable"] = led["object_id"] in page.content()
            page.goto(f"{self.base}/authors/{led['author_id']}")
            led["profile_counts_one_object"] = page.locator("dt:has-text('Registered research objects') + dd").inner_text().strip()
        with page.expect_download() as dl:
            page.goto(detail)
            page.click("text=Handoff r1 (public-safe)")
        target = self.out / "j1-handoff-r1-public.zip"
        dl.value.save_as(str(target))
        led["handoff_bytes"] = target.stat().st_size
        page.close()
        return led

    def j2_ambiguous(self) -> dict:
        page = self.browser.new_page(viewport={"width": 1280, "height": 900})
        page.set_default_timeout(120000)
        email = f"j2-{int(time.time())}@example.invalid"
        led = {"email": email}
        led["author_id"] = self.signup(page, email, "Journey Two Researcher")
        v1 = self.out / "j2-manuscript-v1.pdf"
        v2 = self.out / "j2-manuscript-v2.pdf"
        title = "Bounded Archive Expansion in the Structura Reditus Intake Pipeline: Reliability Under Nested Depth"
        v1.write_bytes(manuscript(title, "1"))
        v2.write_bytes(manuscript(title, "2", " This revision adds the nested-depth analysis."))
        detail = self.upload(page, [v1, v2], "Ambiguous versions (journey 2)")
        led["state_after_upload"] = self.wait_state(page, {"Needs your review"}, 60)
        self.snap(page, "j2-detail-ambiguity")
        page.click("text=Review and edit the draft")
        page.wait_for_load_state("networkidle")
        body = page.content()
        led["version_ambiguity_shown"] = "Version ambiguity" in body
        led["duplicate_shown"] = "Possible duplicates found" in body
        led["blocking_questions"] = self.readiness(page)["blocking"]
        led["question_explains_why"] = "Why it matters" in body and "What resolves it" in body
        self.snap(page, "j2-editor-questions")
        self.fill_missing(page, {
            "object_of_study": "The intake pipeline's bounded ZIP expansion routine under nested depth.",
            "main_question": "Does nested archive depth change the reliability of bounded expansion?",
            "lens": "Diagnostic of the library's own intake machinery.",
            "claim_layers": "source-observation | Archives nested beyond depth three were refused on every run.\nlocal-interpretation | Depth limits are part of the reproducibility contract.",
            "source_boundary": "Establishes simulated behaviour under nesting; not real-world archives.",
            "authority_boundary": "Claims no Tier-0 or Tier-1 authority.",
            "scope": "Synthetic archives with controlled nesting depth.",
            "preserved_meaning": "Refusal at depth is a designed result.",
            "distortion_or_substitution_risk": "Could be mistaken for a claim about external archives; none is made.",
            "next_burden": "Vary member counts jointly with depth.",
            "repair_route": "Amend this record and resubmit through the same seven gates.",
            "structural_focus_primary": "robustness", "provenance": "corpus-native", "maturity": "prospectively-tested", "functional_locus": "none",
        })
        page.click("#draft-form button[value=preview]")
        page.wait_for_load_state("networkidle")
        self.snap(page, "j2-confirm-resolutions-required")
        led["confirm_requires_version"] = page.locator("#version_resolution").count() > 0
        led["confirm_requires_duplicate_decision"] = page.locator("#dup-distinct").count() > 0
        # Attempt without resolving: the server refuses.
        page.check("#acknowledge_claims")
        page.check("#acknowledge")
        if led["confirm_requires_version"]:
            page.fill("#version_resolution", "")
        page.evaluate("document.querySelectorAll('[required]').forEach(e => e.removeAttribute('required'))")
        page.click("main form button.primary")
        page.wait_for_load_state("networkidle")
        led["refused_without_resolution"] = "before submitting" in page.content()
        self.snap(page, "j2-refused-without-resolution")
        # Resolve: v2 governs; distinct study.
        if page.locator("#version_resolution").count():
            page.fill("#version_resolution", "Version 2 in j2-manuscript-v2.pdf governs; v1 is an earlier version of the same source.")
        if page.locator("#dup-distinct").count():
            page.check("#dup-distinct")
        if page.locator("#st-corpus").count():
            page.check("#st-corpus")
        page.check("#acknowledge_claims")
        page.check("#acknowledge")
        page.click("main form button.primary")
        page.wait_for_load_state("networkidle")
        led["final_state"] = self.wait_state(page, TERMINAL, 240)
        led["object_id"] = m.group(1) if (m := re.search(r"/research/(SR-OBJ-[0-9]{6})", page.content())) else None
        self.snap(page, "j2-registered-distinct")
        page.close()
        return led

    def j3_repair(self) -> dict:
        page = self.browser.new_page(viewport={"width": 1280, "height": 900})
        page.set_default_timeout(120000)
        email = f"j3-{int(time.time())}@example.invalid"
        led = {"email": email}
        led["author_id"] = self.signup(page, email, "Journey Three Researcher")
        pdf = self.out / "j3-manuscript.pdf"
        pdf.write_bytes(manuscript("Member-Count Limits in the Structura Reditus Intake Pipeline", "1"))
        detail = self.upload(page, [pdf], "Repair journey (journey 3)")
        self.wait_state(page, {"Needs your review"}, 60)
        page.click("text=Review and edit the draft")
        page.wait_for_load_state("networkidle")
        # Deliberately leave next_burden and scope empty.
        self.fill_missing(page, {
            "object_of_study": "The intake pipeline's member-count limit.",
            "main_question": "Does the member-count limit refuse oversized archives deterministically?",
            "lens": "Diagnostic of the library's own intake machinery.",
            "claim_layers": "source-observation | Archives above the member limit were refused on every run.",
            "source_boundary": "Establishes simulated behaviour; not real-world archives.",
            "authority_boundary": "Claims no Tier-0 or Tier-1 authority.",
            "preserved_meaning": "Refusal above the limit is a designed result.",
            "distortion_or_substitution_risk": "Could be mistaken for a claim about external archives; none is made.",
            "repair_route": "Amend this record and resubmit through the same seven gates.",
            "structural_focus_primary": "boundary", "provenance": "corpus-native", "maturity": "prospectively-tested", "functional_locus": "none",
        })
        page.click("#draft-form button[value=preview]")
        page.wait_for_load_state("networkidle")
        led["confirm_warns_blocking"] = "blocking question" in page.content()
        self.snap(page, "j3-confirm-with-blocking-warning")
        if page.locator("#st-corpus").count():
            page.check("#st-corpus")
        page.check("#acknowledge_claims")
        page.check("#acknowledge")
        page.click("main form button.primary")
        page.wait_for_load_state("networkidle")
        led["state_after_first_submit"] = self.wait_state(page, TERMINAL, 240)
        body = page.content()
        led["repair_receipt"] = m.group(0) if (m := re.search(r"RCPT-[0-9]{6}", body)) else None
        led["exact_repair_listed"] = "next_burden is missing" in body and "scope is missing" in body
        self.snap(page, "j3-needs-repair-receipt")
        page.click("form[action$='/repair'] button")
        page.wait_for_load_state("networkidle")
        body = page.content()
        led["repair_flags_fields"] = "flagged by receipt" in body
        led["repair_reused_evidence"] = "reused from revision r1" in body
        led["readiness_in_repair"] = self.readiness(page)
        self.snap(page, "j3-repair-editor-flagged")
        self.fill_missing(page, {"next_burden": "Vary the member limit and re-run the refusal test.", "scope": "Synthetic archives near the member limit."})
        page.click("#draft-form button[value=preview]")
        page.wait_for_load_state("networkidle")
        page.check("#acknowledge_claims")
        page.check("#acknowledge")
        page.click("main form button.primary")
        page.wait_for_load_state("networkidle")
        led["final_state"] = self.wait_state(page, TERMINAL, 240)
        body = page.content()
        led["receipts_in_history"] = sorted(set(re.findall(r"RCPT-[0-9]{6}", body)))
        led["revisions_shown"] = len(re.findall(r"<td>r[0-9]+</td>", body))
        led["object_id"] = m.group(1) if (m := re.search(r"/research/(SR-OBJ-[0-9]{6})", body)) else None
        self.snap(page, "j3-registered-after-repair")
        if led["object_id"]:
            page.goto(f"{self.base}/research/{led['object_id']}")
            body = page.content()
            led["public_page_shows_both_attempts"] = "RETURNED_FOR_REPAIR" in body and "ACCEPTED" in body
            self.snap(page, "j3-public-record-history")
        page.close()
        return led

    def j4_interruption(self, outage_file: Path, reconcile_cmd: str) -> dict:
        page = self.browser.new_page(viewport={"width": 1280, "height": 900})
        page.set_default_timeout(120000)
        email = f"j4-{int(time.time())}@example.invalid"
        led = {"email": email}
        led["author_id"] = self.signup(page, email, "Journey Four Researcher")
        pdf = self.out / "j4-manuscript.pdf"
        pdf.write_bytes(manuscript("Time Budgets in the Structura Reditus Intake Pipeline", "1"))
        detail = self.upload(page, [pdf], "Interruption journey (journey 4)")
        self.wait_state(page, {"Needs your review"}, 60)
        page.click("text=Review and edit the draft")
        page.wait_for_load_state("networkidle")
        self.fill_missing(page, {
            "object_of_study": "The intake pipeline's extraction time budget.",
            "main_question": "Does the time budget stop archive processing deterministically?",
            "lens": "Diagnostic of the library's own intake machinery.",
            "claim_layers": "source-observation | Processing stopped at the budget on every run.",
            "source_boundary": "Establishes simulated behaviour; not real-world archives.",
            "authority_boundary": "Claims no Tier-0 or Tier-1 authority.",
            "scope": "Synthetic archives exceeding the time budget.",
            "preserved_meaning": "Stopping at the budget is a designed result.",
            "distortion_or_substitution_risk": "Could be mistaken for a claim about external archives; none is made.",
            "next_burden": "Measure budget behaviour under worker contention.",
            "repair_route": "Amend this record and resubmit through the same seven gates.",
            "structural_focus_primary": "boundary", "provenance": "corpus-native", "maturity": "prospectively-tested", "functional_locus": "none",
        })
        page.click("#draft-form button[value=preview]")
        page.wait_for_load_state("networkidle")
        if page.locator("#st-corpus").count():
            page.check("#st-corpus")
        page.check("#acknowledge_claims")
        page.check("#acknowledge")
        outage_file.write_text("GitHub unavailable (injected)\n")  # interruption begins before publication
        page.click("main form button.primary")
        page.wait_for_load_state("networkidle")
        led["state_during_outage"] = self.wait_state(page, {"Accepted — registration pending"} | TERMINAL, 240)
        body = page.content()
        led["receipt_during_outage"] = m.group(0) if (m := re.search(r"RCPT-[0-9]{6}", body)) else None
        led["registered_shown_prematurely"] = "Your work is registered" in body
        self.snap(page, "j4-accepted-awaiting-registration")
        outage_file.unlink()
        for _ in range(3):
            proc = subprocess.run(reconcile_cmd, shell=True, capture_output=True, text=True)
            led.setdefault("reconcile_output", []).append(proc.stdout.strip()[-200:] or proc.stderr.strip()[-200:])
            page.reload()
            page.wait_for_load_state("networkidle")
            if page.locator("#state-badge").inner_text().strip() == "Registered":
                break
            time.sleep(2)
        led["final_state"] = self.wait_state(page, {"Registered"}, 60)
        body = page.content()
        led["receipts_after_recovery"] = sorted(set(re.findall(r"RCPT-[0-9]{6}", body)))
        led["single_receipt"] = len(led["receipts_after_recovery"]) == 1 and led["receipts_after_recovery"][0] == led["receipt_during_outage"]
        self.snap(page, "j4-registered-after-recovery")
        page.close()
        return led


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    parser.add_argument("mail_dir")
    parser.add_argument("out_dir")
    parser.add_argument("--outage-file", default="")
    parser.add_argument("--reconcile-cmd", default="")
    args = parser.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ledger = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        journey = Journey(args.base, Path(args.mail_dir), out, browser)
        ledger["J1_new_researcher_pdf_to_registered"] = journey.j1_new_researcher()
        ledger["J2_ambiguous_versions_and_duplicate"] = journey.j2_ambiguous()
        ledger["J3_repair_and_resubmission"] = journey.j3_repair()
        if args.outage_file and args.reconcile_cmd:
            ledger["J4_interruption_recovery"] = journey.j4_interruption(Path(args.outage_file), args.reconcile_cmd)
        else:
            ledger["J4_interruption_recovery"] = {"status": "NOT RUN: --outage-file and --reconcile-cmd not supplied"}
        browser.close()
    (out / "journeys-ledger.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    print(json.dumps(ledger, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

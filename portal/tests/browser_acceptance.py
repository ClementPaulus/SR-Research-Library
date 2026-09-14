"""Browser acceptance run against a live dev server (A01, A02, U01, P01, E01/G01, O03).

Usage (dev server started with CELERY_TASK_ALWAYS_EAGER=true, the git-backed GitHub double, and the
console/locmem email backend writing to a file):

    python portal/tests/browser_acceptance.py http://127.0.0.1:8123 /tmp/portal-mail.log docs/portal-evidence/browser

Screenshots and a JSON ledger are written to the evidence directory. Nothing scholarly is invented:
the uploaded record is the library's own synthetic self-test fixture.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.conftest import SYNTHETIC_OBJECT  # noqa: E402


def confirm_link(mail_log: Path, email: str) -> str:
    deadline = time.time() + 20
    while time.time() < deadline:
        if mail_log.is_dir():
            text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in sorted(mail_log.glob("*.log")))
        else:
            text = mail_log.read_text(encoding="utf-8", errors="replace") if mail_log.exists() else ""
        text = text.replace("=\n", "").replace("=3D", "=")  # quoted-printable soft breaks
        for chunk in text.split("Subject:"):
            if email in chunk:
                links = re.findall(r"https?://[^\s\"<>]+/accounts/confirm-email/[^\s/\"<>]+/", chunk)
                if links:
                    return links[-1]
        time.sleep(0.5)
    raise SystemExit("verification email not captured")


def main(base: str, mail_log: str, out_dir: str) -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ledger = {}
    email = f"browser-{int(time.time())}@example.invalid"
    password = "browser-acceptance-passphrase-77"
    record = dict(SYNTHETIC_OBJECT, object_id="SR-OBJ-NEW", relations=[], source_ids=["SRC-000001"])
    record_path = out / "synthetic-record.json"
    record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        # A01: signup
        page.goto(f"{base}/signup")
        page.fill("#id_display_name", "Browser Acceptance Researcher")
        page.fill("#id_email", email)
        page.fill("#id_password1", password)
        page.fill("#id_password2", password)
        page.check("#id_accept_terms")
        page.screenshot(path=str(out / "01-signup.png"), full_page=True)
        page.click("main form button[type=submit]")
        page.wait_for_load_state("networkidle")
        ledger["A01.signup_page_after_submit"] = page.url
        page.screenshot(path=str(out / "02-verification-sent.png"), full_page=True)
        link = confirm_link(Path(mail_log), email)
        page.goto(link)
        page.wait_for_load_state("networkidle")
        if page.locator("form button[type=submit]").count() and "confirm" in page.content().lower():
            page.click("form button[type=submit]")
            page.wait_for_load_state("networkidle")
        ledger["A01.after_verification_url"] = page.url
        # Log in explicitly (verification does not auto-login by configuration).
        page.goto(f"{base}/login")
        page.fill("#id_login", email)
        page.fill("#id_password", password)
        page.click("main form button[type=submit]")
        page.wait_for_url(re.compile(r".*/workspace/?$"), timeout=15000)
        page.screenshot(path=str(out / "03-workspace.png"), full_page=True)
        body = page.content()
        author = re.search(r"AUTH-[0-9]{4}", body)
        ledger["A01.author_id_in_workspace"] = author.group(0) if author else None
        badge = re.search(r"(AUTH-[0-9]{4}) · ([a-z_]+)", body)
        ledger["A01.state"] = badge.group(2) if badge else ("pending" if author else "missing")
        for _ in range(20):  # author publication runs eagerly; allow the page to reflect it
            if ledger["A01.state"] in ("registered", "linked"):
                break
            time.sleep(1)
            page.reload()
            body = page.content()
            badge = re.search(r"(AUTH-[0-9]{4}) · ([a-z_]+)", body)
            ledger["A01.state"] = badge.group(2) if badge else ledger["A01.state"]

        # U01/P01: upload the synthetic record and review the prepared draft
        page.goto(f"{base}/workspace/submissions/new")
        page.fill("#label", "Browser acceptance synthetic submission")
        page.set_input_files("#files", str(record_path))
        page.click("main form button[type=submit]")
        page.wait_for_load_state("networkidle")
        ledger["U01.detail_url"] = page.url
        page.screenshot(path=str(out / "04-submission-detail.png"), full_page=True)
        ledger["U01.state_label"] = page.locator("#state-badge").inner_text()
        page.click("text=Review and edit the draft")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(out / "05-editor-evidence.png"), full_page=True)
        ledger["P01.evidence_rows"] = page.locator(".field-evidence").count()
        ledger["P01.title_prefilled"] = page.input_value("#id_title")[:60]
        # The synthetic fixture names AUTH-0001; the browser researcher submits under their own identity.
        if author:
            page.click("summary:has-text('Advanced')")
            page.fill("#id_authors", author.group(0))

        # O03: keyboard navigation and 200% zoom on the editor
        page.keyboard.press("Tab")
        focused = page.evaluate("document.activeElement && document.activeElement.tagName")
        ledger["O03.first_tab_focus"] = focused
        zoom = browser.new_page(viewport={"width": 640, "height": 960}, device_scale_factor=2)
        zoom.context.add_cookies(page.context.cookies())
        zoom.goto(page.url)
        zoom.evaluate("document.documentElement.style.zoom='2'")
        zoom.screenshot(path=str(out / "06-editor-200pct-zoom.png"), full_page=False)
        overflow = zoom.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 4")
        ledger["O03.horizontal_overflow_at_200pct"] = overflow
        mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        mobile.context.add_cookies(page.context.cookies())
        mobile.goto(f"{base}/workspace/submissions/new")
        mobile.screenshot(path=str(out / "07-upload-mobile.png"), full_page=True)
        ledger["O03.mobile_upload_input_visible"] = mobile.locator("#files").is_visible()
        mobile.close()
        zoom.close()

        # E01/G01: save, continue, submit, wait for Registered
        page.click("#draft-form button[value=preview]")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(out / "08-confirm-preflight.png"), full_page=True)
        ledger["E01.preflight_visible"] = "Preflight" in page.content()
        page.check("#acknowledge")
        page.click("main form button.primary")
        page.wait_for_load_state("networkidle")
        deadline = time.time() + 120
        state = ""
        while time.time() < deadline:
            state = page.locator("#state-badge").inner_text()
            if state in ("Registered", "Needs repair", "Not admitted", "Processing unavailable", "Review needed"):
                break
            time.sleep(3)
            page.reload()
            page.wait_for_load_state("networkidle")
        ledger["E01.final_state"] = state
        page.screenshot(path=str(out / "09-registered.png"), full_page=True)
        receipt = re.search(r"RCPT-[0-9]{6}", page.content())
        ledger["E01.receipt_id"] = receipt.group(0) if receipt else None
        obj = re.search(r"/research/(SR-OBJ-[0-9]{6})", page.content())
        ledger["G01.public_record_link"] = obj.group(1) if obj else None
        if obj:
            page.goto(f"{base}/research/{obj.group(1)}")
            page.wait_for_load_state("networkidle")
            page.screenshot(path=str(out / "10-public-record.png"), full_page=True)
            ledger["G01.public_record_status"] = 200 if obj.group(1) in page.content() else None
        # Handoff export downloads
        with page.expect_download() as download_info:
            page.goto(ledger["U01.detail_url"])
            page.click("text=Handoff r1 (public-safe)")
        download = download_info.value
        target = out / "handoff-r1-public.zip"
        download.save_as(str(target))
        ledger["H02.public_handoff_bytes"] = target.stat().st_size

        # A02: new session, same account
        fresh = browser.new_context().new_page()
        fresh.goto(f"{base}/login")
        fresh.fill("#id_login", email)
        fresh.fill("#id_password", password)
        fresh.click("main form button[type=submit]")
        fresh.wait_for_url(re.compile(r".*/workspace/?$"), timeout=15000)
        ledger["A02.same_author_id"] = (re.search(r"AUTH-[0-9]{4}", fresh.content()) or [None])[0] if False else \
            (re.search(r"AUTH-[0-9]{4}", fresh.content()).group(0) if re.search(r"AUTH-[0-9]{4}", fresh.content()) else None)
        ledger["A02.submission_listed"] = "Synthetic self-test object" in fresh.content()
        fresh.screenshot(path=str(out / "11-returning-session.png"), full_page=True)
        browser.close()

    (out / "browser-ledger.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    print(json.dumps(ledger, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))

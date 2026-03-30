"""Craigslist posting flow via Playwright.

Post-publish verification:
  CL has two verification gates when posting anonymously (not logged in):

  1. EMAIL CONFIRMATION ("loginloop" URL):
     CL sends a confirmation email to the FromEMail address. The email contains
     a one-time link like:
       https://accounts.craigslist.org/login/onetime?key=XXXXXX-YYYYYYY
     Visiting this link publishes the listing. This happens for every post.

  2. PHONE VERIFICATION ("s=pn" / "s=pc" URL):
     After several posts, CL requires phone verification. This involves:
     a) Entering a phone number and selecting SMS + language (s=pn page)
     b) Receiving a 3-5 digit code via SMS to the phone
     c) Entering the code in the 'userCode' input field (s=pc page)
     d) Clicking submit (button name="authstep")

     Key gotchas discovered during testing:
     - Radio buttons (callType, callLang) MUST be selected via Playwright's
       .check() method — JS click alone doesn't register them reliably
     - The code input field is named 'userCode' (id='userCode'), NOT 'code'
     - There are multiple submit buttons named 'authstep' — use .first
     - Codes expire quickly — must enter in the same browser session
     - CL may reuse the pending SMS rather than sending a new one
     - The code is read from iMessage via SQLite (~/Library/Messages/chat.db),
       sender handle '51908', embedded in NSAttributedString blob

  Both gates are handled by _handle_phone_verification() below, which is
  called from post_to_craigslist() after the publish step detects a
  loginloop or phone verification URL.
"""
from __future__ import annotations

import os
import re
import sqlite3
import time

from playwright.sync_api import Page, BrowserContext

from cross_poster.browser import (
    launch_browser,
    close_browser,
    human_pause,
    save_error_screenshot,
    POST_DELAY,
)
from cross_poster.config import Listing, map_category_cl, resolve_photo_paths

# Phone number for CL verification (Karthik's mobile)
CL_PHONE = "2024920358"
# iMessage sender handle for CL verification SMS
CL_SMS_HANDLE = "51908"


def _wait_for_page_change(page: Page, old_url: str, timeout: int = 15000) -> None:
    """Wait until the URL changes from old_url."""
    try:
        page.wait_for_function(
            f"() => window.location.href !== '{old_url}'",
            timeout=timeout,
        )
    except Exception:
        # URL didn't change — page may have reloaded with same URL (validation error)
        pass
    page.wait_for_load_state("domcontentloaded")
    human_pause()


def _get_page_step(page: Page) -> str:
    """Detect which CL posting step we're on from the URL."""
    url = page.url
    # Order matters: check longer strings first to avoid substring matches
    # (e.g., "editimage" before "edit", "subarea" before "area")
    # Post-publish steps: "loginloop" (email confirm), "s=pn"/"s=pc" (phone verify)
    for step in ["copyfromanother", "subarea", "area", "type", "cat",
                  "geoverify", "editimage", "edit", "preview",
                  "posting confirmation", "loginloop", "s=pn", "s=pc"]:
        if step in url:
            return step
    return "unknown"


def _select_radio_and_continue(page: Page, label_text: str) -> None:
    """Select a radio by label text, click continue, wait for page change."""
    old_url = page.url
    # Use JS for reliable radio selection (Playwright clicks can miss on CL)
    page.evaluate(f"""() => {{
        const labels = document.querySelectorAll('label');
        for (const l of labels) {{
            if (l.textContent.trim() === '{label_text}') {{
                const radio = l.querySelector('input[type="radio"]');
                if (radio) {{ radio.checked = true; radio.click(); }}
            }}
        }}
    }}""")
    human_pause(1)
    # Click the continue/submit button
    page.evaluate("""() => {
        const buttons = document.querySelectorAll('button[type="submit"]');
        for (const b of buttons) {
            if (b.textContent.includes('continue')) { b.click(); return; }
        }
        // Fallback: click first submit button
        if (buttons.length > 0) buttons[0].click();
    }""")
    _wait_for_page_change(page, old_url)


def _handle_step(page: Page, listing: Listing) -> None:
    """Handle the current CL posting step."""
    step = _get_page_step(page)

    if step == "copyfromanother":
        old_url = page.url
        page.evaluate("""() => {
            const buttons = document.querySelectorAll('button');
            for (const b of buttons) {
                if (b.textContent.includes('skip')) { b.click(); return; }
            }
        }""")
        _wait_for_page_change(page, old_url)

    elif step == "area":
        _select_radio_and_continue(page, "district of columbia")

    elif step == "subarea":
        _select_radio_and_continue(page, "district of columbia")

    elif step == "type":
        _select_radio_and_continue(page, "for sale by owner")

    elif step == "cat":
        cl_cat = map_category_cl(listing.category)
        _select_radio_and_continue(page, cl_cat)

    elif step == "edit":
        page.fill("[name='PostingTitle']", listing.title)
        page.fill("[name='price']", str(int(listing.price)))
        page.fill("[name='geographic_area']", listing.location)
        page.fill("[name='postal']", listing.zip)
        page.fill("[name='PostingBody']", listing.description)

        # Set condition — use JS to find any valid non-empty option
        page.evaluate("""() => {
            const sel = document.querySelector('[name="condition"]');
            if (!sel) return;
            // Try to select "good" by text, fall back to first non-empty option
            for (const opt of sel.options) {
                if (opt.text.toLowerCase().includes('good')) {
                    sel.value = opt.value;
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                    return;
                }
            }
            // Fallback: select first option that isn't the blank/placeholder
            for (const opt of sel.options) {
                if (opt.value && opt.value !== '-' && opt.value !== '') {
                    sel.value = opt.value;
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                    return;
                }
            }
        }""")

        # Fill email and select CL mail relay if not logged in
        page.evaluate("""() => {
            // Fill email if the field exists and is empty
            const emailField = document.querySelector('[name="FromEMail"]');
            if (emailField && !emailField.value) {
                emailField.value = 'kartbala@gmail.com';
                emailField.dispatchEvent(new Event('input', {bubbles: true}));
                emailField.dispatchEvent(new Event('change', {bubbles: true}));
            }
            // Ensure 'CL mail relay' privacy option is selected
            const privacyRadios = document.querySelectorAll('[name="Privacy"]');
            for (const r of privacyRadios) {
                if (r.value === 'C') { r.checked = true; r.click(); }
            }
        }""")

        old_url = page.url
        page.locator("button[type='submit']").first.click()
        _wait_for_page_change(page, old_url)

    elif step == "geoverify":
        old_url = page.url
        page.evaluate("""() => {
            const buttons = document.querySelectorAll('button');
            for (const b of buttons) {
                if (b.textContent.trim() === 'continue') { b.click(); return; }
            }
        }""")
        _wait_for_page_change(page, old_url)

    elif step == "editimage":
        resolved = resolve_photo_paths(listing.photos)
        if resolved:
            file_input = page.locator("input[type='file']")
            file_input.set_input_files(resolved)
            human_pause(5)

        old_url = page.url
        page.evaluate("""() => {
            const buttons = document.querySelectorAll('button');
            for (const b of buttons) {
                if (b.textContent.includes('done with images')) { b.click(); return; }
            }
        }""")
        _wait_for_page_change(page, old_url)


def _read_cl_code_from_imessage(after_timestamp: float | None = None) -> str | None:
    """Read the latest CL verification code from iMessage SQLite DB.

    CL sends codes via SMS from handle '51908'. The message text is stored
    in the attributedBody blob as an NSAttributedString. The code appears as:
      "craigslist secret code for kartbala@gmail.com is XXXX"

    Args:
        after_timestamp: Only consider messages newer than this iMessage
            timestamp (nanoseconds since 2001-01-01). If None, reads the
            latest message regardless of age.

    Returns:
        The 3-5 digit code string, or None if not found.
    """
    db_path = os.path.expanduser("~/Library/Messages/chat.db")
    if not os.path.isfile(db_path):
        return None

    conn = sqlite3.connect(db_path)
    try:
        query = """
            SELECT m.attributedBody, m.text FROM message m
            LEFT JOIN handle h ON m.handle_id = h.ROWID
            WHERE h.id = ?
        """
        params: list = [CL_SMS_HANDLE]
        if after_timestamp is not None:
            query += " AND m.date > ?"
            params.append(after_timestamp)
        query += " ORDER BY m.date DESC LIMIT 1"

        row = conn.execute(query, params).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    body, text = row
    # Try plain text first
    if text and "code" in text.lower():
        nums = re.findall(r"(\d{3,5})", text)
        if nums:
            return nums[0]

    # Fall back to NSAttributedString blob
    if body:
        decoded = body.decode("utf-8", errors="ignore")
        match = re.search(r"code[^\d]*(\d{3,5})", decoded)
        if match:
            return match.group(1)

    return None


def _get_imessage_max_date() -> float:
    """Get the latest message timestamp from the CL SMS handle."""
    db_path = os.path.expanduser("~/Library/Messages/chat.db")
    if not os.path.isfile(db_path):
        return 0
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT MAX(m.date) FROM message m "
            "LEFT JOIN handle h ON m.handle_id = h.ROWID "
            "WHERE h.id = ?",
            (CL_SMS_HANDLE,),
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row and row[0] else 0


def _handle_phone_verification(page: Page) -> bool:
    """Handle CL phone verification (SMS code flow).

    This is triggered when CL requires phone verification after multiple
    anonymous posts. The flow is:
      1. Enter phone number, select SMS + English
      2. Submit and wait for SMS
      3. Read code from iMessage SQLite DB
      4. Enter code in 'userCode' field and submit

    Returns True if verification succeeded, False otherwise.
    """
    url = page.url

    # Step 1: If on the phone number entry page (s=pn), submit phone
    if "s=pn" in url:
        print("  Phone verification required. Submitting phone number...")
        # Record timestamp BEFORE requesting SMS so we can find the new one
        pre_sms_timestamp = _get_imessage_max_date()

        page.fill('[name="pn_number"]', CL_PHONE)
        page.locator('[name="callType"][value="sms"]').check()
        page.locator('[name="callLang"][value="en"]').check()
        human_pause(1)
        page.locator('button[name="go"]').click()
        human_pause(5)

        # Verify we reached the code entry page
        body_text = page.inner_text("body")[:500]
        if "authorization code" not in body_text.lower():
            print("  ERROR: Phone submission failed. Page says:")
            print(f"  {body_text[:200]}")
            return False

        # Step 2: Wait for fresh SMS and read code
        print(f"  SMS requested to ({CL_PHONE[:3]}) {CL_PHONE[3:6]}-{CL_PHONE[6:]}.")
        print("  Waiting for verification code in iMessage...")
        code = None
        for attempt in range(12):  # Wait up to 60 seconds
            time.sleep(5)
            code = _read_cl_code_from_imessage(after_timestamp=pre_sms_timestamp)
            if code:
                break
            print(f"    Waiting... ({attempt + 1}/12)")

        if not code:
            # Fall back to reading the most recent code (CL may resend same one)
            code = _read_cl_code_from_imessage()
            if code:
                print(f"  Using most recent code (CL may have reused it).")

        if not code:
            print("  ERROR: No verification code found in iMessage after 60s.")
            print("  Check your phone for a text from 51908 and run manually.")
            return False

        print(f"  Got verification code: {code}")

    elif "s=pc" in url:
        # Already on the code entry page (e.g., from a retry)
        code = _read_cl_code_from_imessage()
        if not code:
            print("  ERROR: On code entry page but no code found in iMessage.")
            return False
        print(f"  Found existing code: {code}")

    else:
        return False

    # Step 3: Enter code and submit
    # The code input is named 'userCode' (id='userCode'), NOT 'code'
    code_input = page.locator("#userCode")
    if not code_input.is_visible(timeout=5000):
        print("  ERROR: Code input field (#userCode) not found on page.")
        return False

    code_input.fill(code)
    human_pause(1)
    # There are multiple buttons named 'authstep' — use .first for submit
    page.locator('button[name="authstep"]').first.click()
    human_pause(8)

    # Check result
    result_text = page.inner_text("body")[:300]
    if "incorrect" in result_text.lower():
        print("  ERROR: Code was incorrect (may have expired).")
        print("  CL codes expire quickly — must enter in same browser session.")
        return False

    if "posting confirmation" in page.title().lower() or "thanks" in result_text.lower():
        print("  Phone verification successful!")
        return True

    print(f"  Phone verification result unclear. Page: {result_text[:150]}")
    return True


def _publish(page: Page, dry_run: bool = False) -> str | None:
    if "preview" not in page.url:
        return None

    if dry_run:
        print("  [DRY RUN] Stopping at preview — not publishing.")
        return "DRY_RUN"

    old_url = page.url
    page.evaluate("""() => {
        const buttons = document.querySelectorAll('button');
        for (const b of buttons) {
            if (b.textContent.includes('publish')) { b.click(); return; }
        }
    }""")
    _wait_for_page_change(page, old_url)

    # Try to extract the posting URL
    link = page.locator("a[href*='craigslist.org/doc/']").first
    if link.is_visible(timeout=3000):
        return link.get_attribute("href")

    text = page.inner_text("body")
    for line in text.split():
        if "craigslist.org" in line and "/d/" in line:
            return line.strip()

    return page.url


# The steps CL walks through in order
CL_STEPS = ["copyfromanother", "area", "subarea", "type", "cat", "edit",
             "geoverify", "editimage", "preview"]


def post_to_craigslist(
    listing: Listing, context: BrowserContext, dry_run: bool = False
) -> str | None:
    page = context.new_page()
    try:
        page.goto("https://post.craigslist.org/c/")
        human_pause()

        # Walk through steps until we reach preview
        max_steps = 15  # safety limit
        seen_steps = set()
        for _ in range(max_steps):
            step = _get_page_step(page)
            if step == "preview":
                break
            if step == "posting confirmation":
                break
            if step == "unknown":
                print(f"  WARNING: unknown page state: {page.url}")
                break
            if step in seen_steps:
                print(f"  WARNING: stuck on step '{step}', checking for errors...")
                screenshot = save_error_screenshot(page, f"cl_stuck_{listing.title[:20]}")
                print(f"  Screenshot saved: {screenshot}")
                # Check for error messages on the page
                errors = page.locator(".error, .errormsg, [style*='color: red']")
                if errors.count() > 0:
                    print(f"  CL validation error: {errors.first.inner_text()}")
                # Print page text for debugging
                try:
                    body = page.inner_text("body")[:500]
                    print(f"  Page text: {body[:200]}")
                except Exception:
                    pass
                break
            seen_steps.add(step)
            _handle_step(page, listing)

        url = _publish(page, dry_run)

        # Handle post-publish verification gates
        if url and not dry_run:
            current_url = page.url
            if "s=pn" in current_url or "s=pc" in current_url:
                # Phone verification required
                if _handle_phone_verification(page):
                    url = page.url
                else:
                    print("  Post submitted but phone verification failed.")
                    print("  The listing may still be pending — check CL account.")
            elif "loginloop" in (url or ""):
                # Email confirmation needed (anonymous posting)
                print("  Email confirmation required — CL sent a link to kartbala@gmail.com.")
                print("  Use 'python -m cross_poster confirm' or check Gmail.")

        if url:
            print(f"  Posted: {url}")
        return url

    except Exception as e:
        screenshot = save_error_screenshot(page, f"cl_{listing.title[:30]}")
        print(f"  ERROR posting to CL: {e}")
        print(f"  Screenshot saved: {screenshot}")
        return None
    finally:
        page.close()


def post_all_to_craigslist(
    listings: list[Listing], dry_run: bool = False
) -> dict[str, str | None]:
    pw, context = launch_browser("craigslist", headless=False)
    results = {}
    try:
        for i, listing in enumerate(listings):
            if "craigslist" not in listing.platforms:
                continue
            print(f"\n[CL {i+1}/{len(listings)}] {listing.title} — ${listing.price}")
            url = post_to_craigslist(listing, context, dry_run)
            results[listing.title] = url
            if i < len(listings) - 1:
                human_pause(POST_DELAY)
    finally:
        close_browser(pw, context, "craigslist")
    return results

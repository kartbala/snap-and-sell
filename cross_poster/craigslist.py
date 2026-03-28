"""Craigslist posting flow via Playwright."""
from __future__ import annotations

from playwright.sync_api import Page, BrowserContext

from cross_poster.browser import (
    launch_browser,
    close_browser,
    human_pause,
    save_error_screenshot,
    POST_DELAY,
)
from cross_poster.config import Listing, map_category_cl, resolve_photo_paths


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
    for step in ["copyfromanother", "subarea", "area", "type", "cat",
                  "geoverify", "editimage", "edit", "preview", "posting confirmation"]:
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

        condition = page.locator("[name='condition']")
        if condition.is_visible(timeout=1000):
            condition.select_option("40")

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
                # Already handled this step — CL may have validation errors
                # or the page didn't actually change. Take a screenshot and bail.
                print(f"  WARNING: stuck on step '{step}', checking for errors...")
                # Check for error messages on the page
                errors = page.locator(".error, .errormsg, [style*='color: red']")
                if errors.count() > 0:
                    print(f"  CL validation error: {errors.first.inner_text()}")
                break
            seen_steps.add(step)
            _handle_step(page, listing)

        url = _publish(page, dry_run)
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

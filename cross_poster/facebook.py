"""Facebook Marketplace posting flow via Playwright."""
from __future__ import annotations

from playwright.sync_api import Page, BrowserContext

from cross_poster.browser import (
    launch_browser,
    close_browser,
    human_pause,
    save_error_screenshot,
    POST_DELAY,
)
from cross_poster.config import Listing, map_category_fb, resolve_photo_paths


def _upload_photos(page: Page, photo_paths: list[str]) -> None:
    resolved = resolve_photo_paths(photo_paths)
    if not resolved:
        return
    file_input = page.locator("input[type='file']").first
    file_input.set_input_files(resolved)
    human_pause(5)


def _fill_form(page: Page, listing: Listing) -> None:
    title_input = page.locator("[aria-label='Title']")
    if title_input.is_visible(timeout=3000):
        title_input.fill(listing.title)

    price_input = page.locator("[aria-label='Price']")
    if price_input.is_visible(timeout=3000):
        price_input.fill(str(int(listing.price)))

    desc_input = page.locator("textarea[aria-label='Description'], [aria-label='Description']")
    if desc_input.is_visible(timeout=3000):
        desc_input.fill(listing.description)

    condition_dropdown = page.locator("[aria-label='Condition']")
    if condition_dropdown.is_visible(timeout=2000):
        condition_dropdown.click()
        human_pause(1)
        page.locator("text=Used - Like New").click()
        human_pause(1)

    human_pause()


def _publish(page: Page, dry_run: bool = False) -> str | None:
    next_btn = page.locator("button:has-text('Next'), [aria-label='Next']")
    if next_btn.is_visible(timeout=3000):
        if dry_run:
            print("  [DRY RUN] Stopping before Next — not publishing.")
            return None
        next_btn.click()
        human_pause()

    publish_btn = page.locator("button:has-text('Publish'), button:has-text('Update')")
    if publish_btn.is_visible(timeout=5000):
        publish_btn.click()
        human_pause(5)

    return page.url


def post_to_facebook(
    listing: Listing, context: BrowserContext, dry_run: bool = False
) -> str | None:
    page = context.new_page()
    try:
        page.goto("https://www.facebook.com/marketplace/create/item")
        human_pause(3)

        _upload_photos(page, listing.photos)
        _fill_form(page, listing)
        url = _publish(page, dry_run)

        if url:
            print(f"  Posted: {url}")
        return url

    except Exception as e:
        screenshot = save_error_screenshot(page, f"fb_{listing.title[:30]}")
        print(f"  ERROR posting to FB: {e}")
        print(f"  Screenshot saved: {screenshot}")
        return None
    finally:
        page.close()


def post_all_to_facebook(
    listings: list[Listing], dry_run: bool = False
) -> dict[str, str | None]:
    pw, context = launch_browser("facebook", headless=False)
    results = {}
    try:
        for i, listing in enumerate(listings):
            if "facebook" not in listing.platforms:
                continue
            print(f"\n[FB {i+1}/{len(listings)}] {listing.title} — ${listing.price}")
            url = post_to_facebook(listing, context, dry_run)
            results[listing.title] = url
            if i < len(listings) - 1:
                human_pause(POST_DELAY)
    finally:
        close_browser(pw, context, "facebook")
    return results

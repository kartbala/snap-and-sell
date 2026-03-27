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


def _skip_copy_from_previous(page: Page) -> None:
    if "copyfromanother" in page.url:
        skip_btn = page.locator("button:has-text('skip')")
        if skip_btn.is_visible(timeout=3000):
            skip_btn.click()
            page.wait_for_url("**/s=area**", timeout=10000)
            human_pause()


def _select_radio_by_label(page: Page, label_text: str) -> None:
    page.locator(f"label:has-text('{label_text}') input[type='radio']").click()
    page.locator("button[type='submit']:has-text('continue')").click()
    human_pause()


def _select_area(page: Page) -> None:
    if "s=area" in page.url:
        _select_radio_by_label(page, "district of columbia")
        page.wait_for_url("**/s=subarea**", timeout=10000)

    if "s=subarea" in page.url:
        _select_radio_by_label(page, "district of columbia")
        page.wait_for_url("**/s=type**", timeout=10000)


def _select_type(page: Page) -> None:
    if "s=type" in page.url:
        _select_radio_by_label(page, "for sale by owner")
        page.wait_for_url("**/s=cat**", timeout=10000)


def _select_category(page: Page, category: str) -> None:
    if "s=cat" in page.url:
        cl_cat = map_category_cl(category)
        _select_radio_by_label(page, cl_cat)
        page.wait_for_url("**/s=edit**", timeout=10000)


def _fill_form(page: Page, listing: Listing) -> None:
    if "s=edit" not in page.url:
        return

    page.fill("[name='PostingTitle']", listing.title)
    page.fill("[name='price']", str(int(listing.price)))
    page.fill("[name='geographic_area']", listing.location)
    page.fill("[name='postal']", listing.zip)
    page.fill("[name='PostingBody']", listing.description)

    condition = page.locator("[name='condition']")
    if condition.is_visible(timeout=1000):
        condition.select_option("40")

    page.locator("button[type='submit']").first.click()
    human_pause()


def _handle_map(page: Page) -> None:
    if "geoverify" in page.url:
        page.locator("button:has-text('continue')").click()
        page.wait_for_url("**/s=editimage**", timeout=10000)
        human_pause()


def _upload_images(page: Page, photo_paths: list[str]) -> None:
    if "editimage" not in page.url:
        return

    resolved = resolve_photo_paths(photo_paths)
    if resolved:
        file_input = page.locator("input[type='file']")
        file_input.set_input_files(resolved)
        human_pause(5)

    page.locator("button:has-text('done with images')").click()
    page.wait_for_url("**/s=preview**", timeout=15000)
    human_pause()


def _publish(page: Page, dry_run: bool = False) -> str | None:
    if "preview" not in page.url:
        return None

    if dry_run:
        print("  [DRY RUN] Stopping at preview — not publishing.")
        return None

    page.locator("button:has-text('publish')").click()
    page.wait_for_url("**/posting confirmation**", timeout=15000)
    human_pause()

    link = page.locator("a[href*='craigslist.org/doc/']").first
    if link.is_visible(timeout=3000):
        return link.get_attribute("href")

    text = page.inner_text("body")
    for line in text.split():
        if "craigslist.org" in line and "/d/" in line:
            return line.strip()

    return page.url


def post_to_craigslist(
    listing: Listing, context: BrowserContext, dry_run: bool = False
) -> str | None:
    page = context.new_page()
    try:
        page.goto("https://post.craigslist.org/c/")
        human_pause()

        _skip_copy_from_previous(page)
        _select_area(page)
        _select_type(page)
        _select_category(page, listing.category)
        _fill_form(page, listing)
        _handle_map(page)
        _upload_images(page, listing.photos)
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
        close_browser(pw, context)
    return results

"""Playwright browser setup with persistent profiles."""
from __future__ import annotations

import json
import os
import time
from playwright.sync_api import sync_playwright, BrowserContext, Page

# Use local filesystem — Google Drive sync breaks browser session cookies/LevelDB
PROFILES_DIR = os.path.expanduser("~/.cross_poster_profiles")

HUMAN_DELAY = 2.5
POST_DELAY = 5.0


def get_profile_dir(platform: str) -> str:
    profile_dir = os.path.join(PROFILES_DIR, platform)
    os.makedirs(profile_dir, exist_ok=True)
    return profile_dir


def _cookies_path(platform: str) -> str:
    return os.path.join(get_profile_dir(platform), "saved_cookies.json")


def _save_cookies(context: BrowserContext, platform: str) -> None:
    cookies = context.cookies()
    with open(_cookies_path(platform), "w") as f:
        json.dump(cookies, f)


def _load_cookies(context: BrowserContext, platform: str) -> bool:
    path = _cookies_path(platform)
    if not os.path.isfile(path):
        return False
    with open(path) as f:
        cookies = json.load(f)
    if cookies:
        context.add_cookies(cookies)
        return True
    return False


def launch_browser(platform: str, headless: bool = False) -> tuple:
    pw = sync_playwright().start()
    profile_dir = get_profile_dir(platform)
    context = pw.chromium.launch_persistent_context(
        profile_dir,
        headless=headless,
        viewport={"width": 1280, "height": 900},
        locale="en-US",
    )
    # Restore saved cookies if available
    _load_cookies(context, platform)
    return pw, context


def close_browser(pw, context: BrowserContext, platform: str = "") -> None:
    if platform:
        _save_cookies(context, platform)
    context.close()
    pw.stop()


def setup_login(platform: str) -> None:
    urls = {
        "craigslist": "https://accounts.craigslist.org/login",
        "facebook": "https://www.facebook.com/login",
    }
    url = urls.get(platform)
    if not url:
        raise ValueError(f"Unknown platform: {platform}")

    print(f"Opening {platform} login page...")
    print("Log in manually, then close the browser window when done.")
    pw, context = launch_browser(platform, headless=False)
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(url)

    # Wait for user to close the browser or for the page to navigate away from login
    try:
        page.wait_for_event("close", timeout=300_000)
    except Exception:
        pass

    # Save cookies before closing
    _save_cookies(context, platform)
    close_browser(pw, context, platform)
    print(f"{platform} login saved to browser profile.")


def human_pause(seconds: float | None = None) -> None:
    time.sleep(seconds or HUMAN_DELAY)


def save_error_screenshot(page: Page, name: str) -> str:
    errors_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "errors")
    os.makedirs(errors_dir, exist_ok=True)
    path = os.path.join(errors_dir, f"{name}.png")
    page.screenshot(path=path)
    return path

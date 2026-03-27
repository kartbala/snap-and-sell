"""CLI entry point for cross_poster."""
from __future__ import annotations

import argparse
import json
import os

from cross_poster.config import load_listings, Listing
from cross_poster.browser import setup_login


def cmd_setup(args: argparse.Namespace) -> None:
    setup_login(args.platform)


def cmd_list(args: argparse.Namespace) -> None:
    listings = _load(args)
    if not listings:
        print("No listings found.")
        return
    for i, item in enumerate(listings, 1):
        platforms = ", ".join(item.platforms)
        photos = len(_resolve_existing_photos(item.photos))
        print(
            f"  {i}. {item.title} — ${item.price:.0f} "
            f"[{platforms}] ({photos} photos)"
        )


def cmd_post(args: argparse.Namespace) -> None:
    listings = _load(args)
    if not listings:
        print("No listings found.")
        return

    if args.item:
        query = args.item.lower()
        listings = [l for l in listings if query in l.title.lower()]
        if not listings:
            print(f"No listings matching '{args.item}'.")
            return

    platforms = (
        [args.platform] if args.platform else ["craigslist", "facebook"]
    )
    all_results = {}

    if "craigslist" in platforms:
        cl_listings = [l for l in listings if "craigslist" in l.platforms]
        if cl_listings:
            print(f"\n=== Craigslist ({len(cl_listings)} items) ===")
            from cross_poster.craigslist import post_all_to_craigslist

            results = post_all_to_craigslist(cl_listings, dry_run=args.dry_run)
            all_results["craigslist"] = results
            _record_results(cl_listings, results, "craigslist", args)

    if "facebook" in platforms:
        fb_listings = [l for l in listings if "facebook" in l.platforms]
        if fb_listings:
            print(f"\n=== Facebook Marketplace ({len(fb_listings)} items) ===")
            from cross_poster.facebook import post_all_to_facebook

            results = post_all_to_facebook(fb_listings, dry_run=args.dry_run)
            all_results["facebook"] = results
            _record_results(fb_listings, results, "facebook", args)

    print("\n=== Summary ===")
    for platform, results in all_results.items():
        posted = sum(1 for v in results.values() if v)
        print(f"  {platform}: {posted}/{len(results)} posted")


def _load(args: argparse.Namespace) -> list[Listing]:
    json_path = getattr(args, "json", None)
    api_url = getattr(args, "api_url", "http://localhost:5001")
    return load_listings(json_path=json_path, api_url=api_url)


def _resolve_existing_photos(photos: list[str]) -> list[str]:
    result = []
    for p in photos:
        expanded = os.path.expanduser(p)
        if os.path.isfile(expanded):
            result.append(expanded)
    return result


def _record_results(
    listings: list[Listing],
    results: dict[str, str | None],
    platform: str,
    args: argparse.Namespace,
) -> None:
    if args.dry_run:
        return

    api_url = getattr(args, "api_url", "http://localhost:5001")
    saved_to_api = False

    for listing in listings:
        url = results.get(listing.title)
        if not url or not listing.listing_id:
            continue
        try:
            import requests

            requests.post(
                f"{api_url}/api/listings/{listing.listing_id}/external-posts",
                json={
                    "platform": platform,
                    "url": url,
                    "last_price_posted": listing.price,
                },
                timeout=5,
            )
            saved_to_api = True
        except Exception:
            pass

    if not saved_to_api:
        results_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "results.json"
        )
        existing = []
        if os.path.isfile(results_path):
            with open(results_path) as f:
                existing = json.load(f)
        for title, url in results.items():
            if url:
                existing.append(
                    {"title": title, "platform": platform, "url": url}
                )
        with open(results_path, "w") as f:
            json.dump(existing, f, indent=2)
        print(f"  Results saved to {results_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cross_poster",
        description="Post Snap & Sell listings to Craigslist and Facebook Marketplace",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:5001",
        help="Snap & Sell API base URL (default: http://localhost:5001)",
    )
    parser.add_argument(
        "--json",
        default=None,
        help="Path to listings JSON file (fallback if API unavailable)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    setup_parser = sub.add_parser("setup", help="Log in to a platform")
    setup_parser.add_argument(
        "--platform",
        required=True,
        choices=["craigslist", "facebook"],
    )

    sub.add_parser("list", help="List items that would be posted")

    post_parser = sub.add_parser("post", help="Post listings")
    post_parser.add_argument(
        "--platform",
        choices=["craigslist", "facebook"],
        help="Post to one platform only",
    )
    post_parser.add_argument(
        "--item",
        help="Filter by title substring",
    )
    post_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Walk through flow without publishing",
    )

    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "post":
        cmd_post(args)


if __name__ == "__main__":
    main()

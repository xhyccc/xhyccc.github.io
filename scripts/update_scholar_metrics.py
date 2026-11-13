#!/usr/bin/env python3
"""Refresh the Google Scholar citation metrics shown in the site hero.

Fetches the public Scholar profile once, extracts the all-time citation count,
h-index, and i10-index from the profile summary table, and writes
assets/scholar-metrics.json. The page keeps its last known values when the
fetch fails, so a blocked or changed profile never blanks the hero.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROFILE_ID = "f_Kcie0AAAAJ"
PROFILE_URL = f"https://scholar.google.com/citations?user={PROFILE_ID}&hl=en"
DEFAULT_OUT = Path("assets/scholar-metrics.json")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
CELL = re.compile(r'<td class="gsc_rsb_std">([\d,]+)</td>')


def fetch(url: str, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} from Google Scholar")
        return response.read().decode("utf-8", errors="replace")


def fetch_serpapi(profile_id: str, api_key: str, timeout: int = 30) -> dict[str, int]:
    """Read the same three all-time values through SerpAPI when configured."""
    query = urllib.parse.urlencode(
        {
            "engine": "google_scholar_author",
            "author_id": profile_id,
            "api_key": api_key,
        }
    )
    with urllib.request.urlopen(
        f"https://serpapi.com/search.json?{query}", timeout=timeout
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("error"):
        raise RuntimeError(payload["error"])
    table = payload.get("cited_by", {}).get("table", [])
    values: dict[str, int] = {}
    for row in table:
        for key in ("citations", "h_index", "i10_index"):
            if key in row and "all" in row[key]:
                values[key] = int(row[key]["all"])
    if not {"citations", "h_index", "i10_index"} <= set(values):
        raise RuntimeError("SerpAPI response did not include the citation table")
    return values


def parse(html_text: str) -> dict[str, int]:
    values = [int(value.replace(",", "")) for value in CELL.findall(html_text)]
    if len(values) < 6:
        raise RuntimeError(
            "profile summary table not found (Google may be showing a CAPTCHA)"
        )
    # Columns: citations all/since, h-index all/since, i10-index all/since.
    return {"citations": values[0], "h_index": values[2], "i10_index": values[4]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--profile-id", default=PROFILE_ID)
    parser.add_argument("--check", action="store_true", help="print values without writing")
    parser.add_argument(
        "--soft-fail",
        action="store_true",
        help="exit 0 when Google blocks the request, keeping the last values",
    )
    args = parser.parse_args()

    url = f"https://scholar.google.com/citations?user={args.profile_id}&hl=en"
    api_key = os.environ.get("SERPAPI_API_KEY", "").strip()
    try:
        try:
            metrics = parse(fetch(url))
        except (urllib.error.URLError, RuntimeError, TimeoutError) as direct_error:
            if not api_key:
                raise
            print(f"direct Scholar fetch failed ({direct_error}); using SerpAPI", file=sys.stderr)
            metrics = fetch_serpapi(args.profile_id, api_key)
    except (urllib.error.URLError, RuntimeError, TimeoutError, json.JSONDecodeError) as exc:
        message = f"scholar refresh failed: {exc}"
        print(message, file=sys.stderr)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if args.soft_fail:
            if summary:
                with open(summary, "a", encoding="utf-8") as handle:
                    handle.write(
                        f"Scholar refresh skipped: {exc}. "
                        "The site kept its last committed values. "
                        "Set a `SERPAPI_API_KEY` repository secret to refresh "
                        "from GitHub Actions.\n"
                    )
            print("keeping the last committed metrics")
            return
        raise SystemExit(1)

    payload = {
        "source": "google_scholar",
        "profile_id": args.profile_id,
        "profile_url": url,
        "citations": metrics["citations"],
        "h_index": metrics["h_index"],
        "i10_index": metrics["i10_index"],
        "retrieved_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    if args.check:
        print(json.dumps(payload, indent=2))
        return

    args.out.parent.mkdir(parents=True, exist_ok=True)
    previous = {}
    if args.out.is_file():
        try:
            previous = json.loads(args.out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}
    unchanged = all(previous.get(key) == payload[key]
                    for key in ("citations", "h_index", "i10_index"))
    if unchanged:
        # Refresh the timestamp only when a value actually changed, so the
        # scheduled workflow does not create a commit every day.
        print("metrics unchanged")
        return
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: {payload['citations']} citations, "
          f"h-index {payload['h_index']}, i10-index {payload['i10_index']}")


if __name__ == "__main__":
    main()

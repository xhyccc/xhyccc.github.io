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
import re
import sys
import urllib.error
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
    args = parser.parse_args()

    url = f"https://scholar.google.com/citations?user={args.profile_id}&hl=en"
    try:
        metrics = parse(fetch(url))
    except (urllib.error.URLError, RuntimeError, TimeoutError) as exc:
        print(f"scholar refresh failed: {exc}", file=sys.stderr)
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

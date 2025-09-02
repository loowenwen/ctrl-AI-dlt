
"""
Lambda entry + local CLI wrapper for TikTok Discover scraping.

EVENT SHAPE (Lambda):
{
  "url": "https://www.tiktok.com/discover/...",   # required
  "limit": 60,                                    # optional (int)
  "timeout_s": 30,                                # optional (int)
  "include_page": false                           # optional (bool)
}

RETURNS (Lambda):
{
  "ok": true,
  "data": { "items": [...], "page": {...}? }
}
or
{
  "ok": false,
  "error": "message"
}

Local CLI:
  python main_lambda.py --url "https://www.tiktok.com/discover/..." --limit 60 --include-page
"""

from __future__ import annotations
import argparse
import json
import sys
from typing import Any, Dict

from tiktok_discover import scrape_discover

# ------------- AWS Lambda handler -------------

def lambda_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    try:
        if not isinstance(event, dict):
            raise ValueError("Event must be a JSON object.")

        url = event.get("url")
        if not url or not isinstance(url, str):
            raise ValueError("Missing required 'url' (string).")

        limit = int(event.get("limit", 50))
        timeout_s = int(event.get("timeout_s", 30))
        include_page = bool(event.get("include_page", False))

        data = scrape_discover(
            url,
            limit=limit,
            timeout_s=timeout_s,
            include_page=include_page,
        )
        return {"ok": True, "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ------------- Local CLI wrapper -------------

def _cli() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="TikTok Discover URL")
    ap.add_argument("--limit", type=int, default=50, help="Max items to return")
    ap.add_argument("--timeout-s", type=int, default=30, help="Page load timeout (seconds)")
    ap.add_argument("--include-page", action="store_true", help="Include entire SIGI_STATE blob")
    ap.add_argument("--ndjson", action="store_true", help="Print items as NDJSON (one line per item)")
    args = ap.parse_args()

    try:
        payload = scrape_discover(
            args.url,
            limit=args.limit,
            timeout_s=args.timeout_s,
            include_page=args.include_page,
        )

        if args.ndjson:
            for rec in payload.get("items", []):
                print(json.dumps(rec, ensure_ascii=False))
        else:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(_cli())
# python3 tiktok_discovery_lambda.py --url "https://www.tiktok.com/discover/july-bto-launch-toa-payoh"
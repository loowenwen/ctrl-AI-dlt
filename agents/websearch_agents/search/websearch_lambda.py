#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AWS Lambda entry + local CLI wrapper for web aggregation.

Lambda EVENT (two modes):
1) Topic search + fetch:
{
  "mode": "topic",
  "topic": "HDB BTO Toa Payoh July Launch 2025 ...",
  "max_results": 5,
  "max_response_size": 220000,
  "per_url_timeout_s": 10,
  "allow_domains": ["straitstimes.com", "hdb.gov.sg"],
  "block_domains": ["facebook.com"]
}

2) Direct URLs:
{
  "mode": "urls",
  "urls": ["https://example.com/a", "https://example.com/b"],
  "max_response_size": 220000,
  "per_url_timeout_s": 10
}

RETURNS:
{ "ok": true, "data": {...} } or { "ok": false, "error": "..." }

Local CLI examples:
  python main_lambda.py --topic "HDB BTO Toa Payoh July Launch 2025" --max-results 5
  python main_lambda.py --urls https://a.com https://b.com --max-response-size 150000
"""

from __future__ import annotations
import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from websearch import find_topic_sources, fetch_urls

# ---------------- Lambda handler ----------------

def lambda_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    try:
        if not isinstance(event, dict):
            raise ValueError("Event must be a JSON object")

        mode = (event.get("mode") or "topic").lower()
        max_response_size = int(event.get("max_response_size", 220000))
        per_url_timeout_s = int(event.get("per_url_timeout_s", 10))

        if mode == "urls":
            urls = event.get("urls") or []
            if not isinstance(urls, list) or not urls:
                raise ValueError("In 'urls' mode, provide a non-empty list under 'urls'")
            data = fetch_urls(
                urls,
                max_response_size=max_response_size,
                per_url_timeout_s=per_url_timeout_s,
            )
            return {"ok": True, "data": data}

        # Default: topic mode
        topic = event.get("topic")
        if not topic or not isinstance(topic, str):
            raise ValueError("In 'topic' mode, provide 'topic' (string)")

        max_results = int(event.get("max_results", 5))
        allow_domains = event.get("allow_domains")
        block_domains = event.get("block_domains")

        data = find_topic_sources(
            topic,
            max_results=max_results,
            max_response_size=max_response_size,
            per_url_timeout_s=per_url_timeout_s,
            allow_domains=allow_domains if isinstance(allow_domains, list) else None,
            block_domains=block_domains if isinstance(block_domains, list) else None,
        )
        return {"ok": True, "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------- Local CLI ----------------

def _cli() -> int:
    ap = argparse.ArgumentParser(description="Web aggregation (topic search or direct URLs)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--topic", help="Topic to search, then fetch pages")
    mode.add_argument("--urls", nargs="+", help="One or more URLs to fetch directly")
    ap.add_argument("--max-results", type=int, default=5, help="Max search results for topic mode")
    ap.add_argument("--max-response-size", type=int, default=220000, help="Total byte budget for aggregated content")
    ap.add_argument("--per-url-timeout-s", type=int, default=10, help="Timeout per URL fetch in seconds")
    ap.add_argument("--allow-domains", nargs="*", help="Only include URLs containing any of these substrings")
    ap.add_argument("--block-domains", nargs="*", help="Exclude URLs containing any of these substrings")
    ap.add_argument("--ndjson", action="store_true", help="Print each source as one JSON line (topic mode only)")
    args = ap.parse_args()

    try:
        if args.urls:
            payload = fetch_urls(
                args.urls,
                max_response_size=args.max_response_size,
                per_url_timeout_s=args.per_url_timeout_s,
            )
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0

        # Topic mode
        payload = find_topic_sources(
            args.topic,
            max_results=args.max_results,
            max_response_size=args.max_response_size,
            per_url_timeout_s=args.per_url_timeout_s,
            allow_domains=args.allow_domains,
            block_domains=args.block_domains,
        )
        if args.ndjson:
            for rec in payload.get("sources", []):
                print(json.dumps(rec, ensure_ascii=False))
        else:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_cli())
#python3 websearch_lambda.py --topic "Find me information on the latest BTO launch"
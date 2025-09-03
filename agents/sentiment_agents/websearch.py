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

import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
try:
    import boto3  # optional: only needed if saving to S3
except Exception:  # pragma: no cover
    boto3 = None

from websearch_functions import find_topic_sources, fetch_urls

# --------------- Helpers: matching & saving ---------------

def _normalize_words(words: Any) -> list[str]:
    if not words:
        return []
    if isinstance(words, str):
        words = [words]
    if not isinstance(words, list):
        return []
    return [str(w).strip().lower() for w in words if str(w).strip()]


def _record_iter(payload: Dict[str, Any]):
    """Yield minimal records with url and text for matching.
    Supports shapes from find_topic_sources() and fetch_urls()."""
    if not isinstance(payload, dict):
        return
    # topic mode typical: {"sources": [{"url":..., "content":...}, ...]}
    if isinstance(payload.get("sources"), list):
        for rec in payload["sources"]:
            if isinstance(rec, dict):
                yield {
                    "url": rec.get("url") or rec.get("link") or rec.get("href"),
                    "title": rec.get("title"),
                    "content": rec.get("content") or rec.get("text") or "",
                    "meta": {k: rec.get(k) for k in rec.keys() if k not in {"url", "link", "href", "title", "content", "text"}},
                }
    # urls mode typical: {"results": [{"url":..., "content":...}, ...]}
    if isinstance(payload.get("results"), list):
        for rec in payload["results"]:
            if isinstance(rec, dict):
                yield {
                    "url": rec.get("url") or rec.get("link") or rec.get("href"),
                    "title": rec.get("title"),
                    "content": rec.get("content") or rec.get("text") or "",
                    "meta": {k: rec.get(k) for k in rec.keys() if k not in {"url", "link", "href", "title", "content", "text"}},
                }


def _match_records(payload: Dict[str, Any], words: list[str]) -> list[Dict[str, Any]]:
    """Return subset of records where any word appears in content/title/url (case-insensitive)."""
    if not words:
        return []
    out: list[Dict[str, Any]] = []
    for rec in _record_iter(payload):
        url = (rec.get("url") or "")
        title = (rec.get("title") or "")
        text = (rec.get("content") or "")
        hay = f"{title}\n{url}\n{text}".lower()
        if any(w in hay for w in words):
            out.append(rec)
    return out


def _save_matches_local(matches: list[Dict[str, Any]], topic: Optional[str], path: str) -> str:
    """Save as NDJSON locally. Returns file path."""
    if not matches:
        return ""
    p = Path(path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for rec in matches:
            f.write(json.dumps({"topic": topic, **rec}, ensure_ascii=False) + "\n")
    return str(p)


def _save_matches_s3(matches: list[Dict[str, Any]], topic: Optional[str], bucket: str, prefix: str | None) -> str:
    """Save as NDJSON to S3. Returns s3:// URI. Requires boto3 and credentials."""
    if not matches or not boto3:
        return ""
    session = boto3.session.Session()
    s3 = session.client("s3")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha = hashlib.sha256(json.dumps(matches, ensure_ascii=False).encode("utf-8")).hexdigest()[:10]
    key = f"{(prefix or 'websearch-matches/').rstrip('/')}/{ts}_{sha}.ndjson"
    lines = "\n".join(json.dumps({"topic": topic, **rec}, ensure_ascii=False) for rec in matches) + "\n"
    s3.put_object(Bucket=bucket, Key=key, Body=lines.encode("utf-8"), ContentType="application/x-ndjson")
    return f"s3://{bucket}/{key}"

# ---------------- Lambda handler ----------------

def lambda_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    try:
        if not isinstance(event, dict):
            raise ValueError("Event must be a JSON object")

        mode = (event.get("mode") or "topic").lower()
        save_words = _normalize_words(event.get("save_if_contains"))
        save_bucket = event.get("save_bucket") or os.environ.get("WEBSEARCH_SAVE_BUCKET")
        save_prefix = event.get("save_prefix") or os.environ.get("WEBSEARCH_SAVE_PREFIX") or "websearch-matches/"

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
            saved = None
            match_count = 0
            if save_words:
                matches = _match_records(data, save_words)
                match_count = len(matches)
                if matches:
                    if save_bucket and boto3:
                        saved = _save_matches_s3(matches, topic=None, bucket=save_bucket, prefix=save_prefix)
                    else:
                        # No bucket provided in Lambda mode; just attach matches (truncated) to response
                        pass
            return {"ok": True, "data": data, "matches": match_count, **({"saved": saved} if saved else {})}

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
        saved = None
        match_count = 0
        if save_words:
            matches = _match_records(data, save_words)
            match_count = len(matches)
            if matches:
                if save_bucket and boto3:
                    saved = _save_matches_s3(matches, topic=topic, bucket=save_bucket, prefix=save_prefix)
                else:
                    pass
        return {"ok": True, "data": data, "matches": match_count, **({"saved": saved} if saved else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def process_websearch(
    topic: Optional[str] = None,
    urls: Optional[List[str]] = None,
    max_results: int = 5,
    max_response_size: int = 220000,
    per_url_timeout_s: int = 10,
    allow_domains: Optional[List[str]] = None,
    block_domains: Optional[List[str]] = None,
    save_if_contains: Optional[List[str]] = None,
    save_path: Optional[str] = None,
    save_bucket: Optional[str] = None,
    save_prefix: str = "websearch-matches/"
) -> Dict[str, Any]:
    """
    Process web search through topic search or direct URLs.
    
    Args:
        topic: Topic to search and fetch pages
        urls: List of URLs to fetch directly
        max_results: Max search results for topic mode
        max_response_size: Total byte budget for aggregated content
        per_url_timeout_s: Timeout per URL fetch in seconds
        allow_domains: Only include URLs containing any of these substrings
        block_domains: Exclude URLs containing any of these substrings
        save_if_contains: If any words appear in content/title/url, save matches
        save_path: Local path to save NDJSON matches
        save_bucket: S3 bucket to save NDJSON matches
        save_prefix: S3 key prefix for matches
    
    Returns:
        Dict containing search results and optional save information
    """
    try:
        if urls:
            # Direct URLs mode
            payload = fetch_urls(
                urls,
                max_response_size=max_response_size,
                per_url_timeout_s=per_url_timeout_s,
            )
            
            if save_if_contains:
                words = _normalize_words(save_if_contains)
                matches = _match_records(payload, words)
                if matches:
                    if save_bucket and boto3:
                        uri = _save_matches_s3(matches, topic=None, bucket=save_bucket, prefix=save_prefix)
                        return {"ok": True, "data": payload, "saved": uri, "match_count": len(matches)}
                    elif save_path:
                        fp = _save_matches_local(matches, topic=None, path=save_path)
                        return {"ok": True, "data": payload, "saved": fp, "match_count": len(matches)}
            
            return {"ok": True, "data": payload}

        # Topic mode
        if not topic:
            raise ValueError("Either topic or urls must be provided")

        payload = find_topic_sources(
            topic,
            max_results=max_results,
            max_response_size=max_response_size,
            per_url_timeout_s=per_url_timeout_s,
            allow_domains=allow_domains,
            block_domains=block_domains,
        )

        if save_if_contains:
            words = _normalize_words(save_if_contains)
            matches = _match_records(payload, words)
            if matches:
                if save_bucket and boto3:
                    uri = _save_matches_s3(matches, topic=topic, bucket=save_bucket, prefix=save_prefix)
                    return {"ok": True, "data": payload, "saved": uri, "match_count": len(matches)}
                elif save_path:
                    fp = _save_matches_local(matches, topic=topic, path=save_path)
                    return {"ok": True, "data": payload, "saved": fp, "match_count": len(matches)}

        return {"ok": True, "data": payload}

    except Exception as e:
        return {"ok": False, "error": str(e)}

# Example usage
if __name__ == "__main__":
    # Example: Search by topic
    result = process_websearch(
        topic="HDB BTO Toa Payoh July 2025 4-room flat reviews, MRT access, school proximity, resale value sentiment on TikTok and YouTube",
        max_results=5,
        save_if_contains=["BTO", "launch"]
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))

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

from tiktok_discover_functions import scrape_discover

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

def process_tiktok_discover(
    url: str,
    limit: int = 50,
    timeout_s: int = 30,
    include_page: bool = False,
    ndjson: bool = False
) -> Dict[str, Any]:
    """
    Process TikTok Discover page scraping.
    
    Args:
        url: TikTok Discover URL to scrape
        limit: Maximum number of items to return
        timeout_s: Page load timeout in seconds
        include_page: Include entire SIGI_STATE blob in response
        ndjson: Print items as NDJSON (one line per item)
    
    Returns:
        Dict containing scraping results or error information
    """
    try:
        if not url or not isinstance(url, str):
            raise ValueError("Missing required 'url' (string).")

        payload = scrape_discover(
            url,
            limit=limit,
            timeout_s=timeout_s,
            include_page=include_page,
        )

        if ndjson:
            result = {"ok": True, "data": [], "format": "ndjson"}
            for rec in payload.get("items", []):
                result["data"].append(json.dumps(rec, ensure_ascii=False))
            return result
        
        return {"ok": True, "data": payload}

    except Exception as e:
        return {"ok": False, "error": str(e)}

# Update lambda handler to use the new function
def lambda_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    if not isinstance(event, dict):
        return {"ok": False, "error": "Event must be a JSON object."}
    
    return process_tiktok_discover(
        url=event.get("url"),
        limit=int(event.get("limit", 50)),
        timeout_s=int(event.get("timeout_s", 30)),
        include_page=bool(event.get("include_page", False))
    )

# Example usage
if __name__ == "__main__":
    # Example: Scrape TikTok discover page
    result = process_tiktok_discover(
        url="https://www.tiktok.com/discover/july-bto-launch-toa-payoh",
        limit=10,
        include_page=True
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
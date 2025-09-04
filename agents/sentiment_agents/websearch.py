from __future__ import annotations
import json
import os
import sys
import ssl
import certifi
import urllib.request
from typing import List, Dict, Any, Optional
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import boto3
from bs4 import BeautifulSoup
from googlesearch import search as google_search  # pip: googlesearch-python
from strands import Agent, tool

# ---- Config ----
DEFAULT_MAX_RESPONSE_SIZE = int(os.getenv("MAX_RESPONSE_SIZE", "220000"))
UA = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"
)
GOOGLE_MAX_RESULTS = int(os.getenv("GOOGLE_MAX_RESULTS", "10"))

# Ensure certs (esp. in Lambda)
os.environ["SSL_CERT_FILE"] = certifi.where()
SSL_CTX = ssl.create_default_context(cafile=certifi.where())


# ----------------------------- Core fetch -----------------------------

def get_page_content(url: str, timeout_s: int = 10) -> Optional[str]:
    """
    Fetch a web page and return cleaned plain text (no script/style).
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout_s, context=SSL_CTX) as resp:
            # Respect server encoding if present
            charset = resp.headers.get_content_charset() or "utf-8"
            html = resp.read().decode(charset, errors="replace")
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator=" ")
        # Normalize whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        cleaned = "\n".join(chunk for chunk in chunks if chunk)
        return cleaned or None
    except Exception as e:
        # Don't print in library; return None and let caller decide logging
        return None


def search_google(query: str, max_results: int = 10, sleep_interval: float = 2.0) -> List[str]:
    """
    Use python googlesearch to get URLs.
    """
    try:
        return list(google_search(query, num_results=max_results, sleep_interval=sleep_interval))
    except Exception:
        return []


def find_topic_sources(
    topic: str,
    *,
    max_results: int = 5,
    max_response_size: int = DEFAULT_MAX_RESPONSE_SIZE,
    per_url_timeout_s: int = 10,
    allow_domains: Optional[List[str]] = None,
    block_domains: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Find & aggregate content about a topic (e.g. 'HDB BTO Toa Payoh').

    Returns:
        {
          "topic": str,
          "sources": [ { "url": str, "content": str } | { "url": str, "error": str }, ... ],
          "truncated": bool
        }
    """
    if not topic:
        return {"error": "No topic provided"}

    urls = search_google(topic, max_results=max_results) or []
    if not urls:
        return {"topic": topic, "sources": [], "truncated": False, "warning": "No search results found"}

    def _allowed(u: str) -> bool:
        if block_domains and any(b in u for b in block_domains):
            return False
        if allow_domains:
            return any(a in u for a in allow_domains)
        return True

    aggregated_size = 0
    truncated = False
    results: List[Dict[str, Any]] = []

    for url in urls:
        if not _allowed(url):
            results.append({"url": url, "skipped": "domain filtered"})
            continue

        content = get_page_content(url, timeout_s=per_url_timeout_s)
        if not content:
            results.append({"url": url, "error": "Failed to fetch"})
            continue

        # Build a block with a header to give the consumer context
        block = f"URL: {url}\n\n{content}\n\n{'=' * 100}\n\n"
        block_size = len(block.encode("utf-8", errors="ignore"))

        # If adding this block would exceed the cap, truncate the block to fit.
        if aggregated_size + block_size > max_response_size:
            remaining = max_response_size - aggregated_size
            if remaining > 0:
                # Truncate on byte boundary
                truncated_block = block.encode("utf-8", errors="ignore")[:remaining].decode("utf-8", errors="ignore")
                results.append({
                    "url": url,
                    "content": truncated_block,
                    "warning": "Content truncated due to size cap"
                })
                aggregated_size = max_response_size
            truncated = True
            break

        aggregated_size += block_size
        results.append({"url": url, "content": content})

    return {
        "topic": topic,
        "sources": results,
        "truncated": truncated
    }


# ----------------------------- Optional: direct URLs mode -----------------------------

def fetch_urls(
    urls: List[str],
    *,
    max_response_size: int = DEFAULT_MAX_RESPONSE_SIZE,
    per_url_timeout_s: int = 10,
) -> Dict[str, Any]:
    """
    Fetch a provided list of URLs and return cleaned contents with truncation.
    """
    aggregated_size = 0
    truncated = False
    results: List[Dict[str, Any]] = []

    for url in urls:
        content = get_page_content(url, timeout_s=per_url_timeout_s)
        if not content:
            results.append({"url": url, "error": "Failed to fetch"})
            continue

        block = f"URL: {url}\n\n{content}\n\n{'=' * 100}\n\n"
        block_size = len(block.encode("utf-8", errors="ignore"))

        if aggregated_size + block_size > max_response_size:
            remaining = max_response_size - aggregated_size
            if remaining > 0:
                truncated_block = block.encode("utf-8", errors="ignore")[:remaining].decode("utf-8", errors="ignore")
                results.append({
                    "url": url,
                    "content": truncated_block,
                    "warning": "Content truncated due to size cap"
                })
                aggregated_size = max_response_size
            truncated = True
            break

        aggregated_size += block_size
        results.append({"url": url, "content": content})

    return {"urls": urls, "sources": results, "truncated": truncated}

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


@tool
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
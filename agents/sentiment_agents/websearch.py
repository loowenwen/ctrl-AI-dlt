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
import requests
import logging
from strands import Agent, tool
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel
from botocore.config import Config
from dotenv import load_dotenv
load_dotenv(".env")

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

NOVA_PRO_MODEL_ID = os.environ.get("CLAUDE_35")
WS_DEFAULT_REGION = "us-east-1"
BRAVE_API_KEY = os.environ.get("BRAVE_SEARCH_API")


logger.info("Bedrock region=%s model_id=%s", WS_DEFAULT_REGION, NOVA_PRO_MODEL_ID)

session = boto3.Session(region_name=WS_DEFAULT_REGION)

# Some BedrockModel versions accept inference_profile_arn; if not, it will be ignored safely
model = BedrockModel(
    model_id=NOVA_PRO_MODEL_ID,
    max_tokens=1024,
    boto_client_config=Config(
        read_timeout=120,
        connect_timeout=120,
        retries=dict(max_attempts=3, mode="adaptive"),
    ),
    boto_session=session
)

SYSTEM_PROMPT = (
    "Based on your inserted query, determine if we are websearching for a normal google search query or a url. If it is a normal google query, insert the query into 'topic' parameters in [process_websearch] tool." \
    "Else, insert the url into 'url' parameters in [process_websearch] tool."
    "Return the search results in the form of summarizing text content and ALL URLS (text, videos, tiktok, youtube, etc) "
)

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


# def search_google(query: str, max_results: int = 10, sleep_interval: float = 2.0) -> List[str]:
#     """
#     Use Google Custom Search API to get URLs.
#     """
#     if not GOOGLE_API_KEY:
#         logger.warning("Google API key not found. Cannot perform search.")
#         return []
#     
#     try:
#         # Google Custom Search API endpoint
#         url = "https://www.googleapis.com/customsearch/v1"
#         
#         params = {
#             'key': GOOGLE_API_KEY,
#             'cx': GOOGLE_CSE_ID,
#             'q': query,
#             'num': min(max_results, 10),  # API limit is 10 per request
#         }
#         
#         response = requests.get(url, params=params, timeout=10)
#         response.raise_for_status()
#         
#         data = response.json()
#         
#         if 'items' not in data:
#             logger.warning("No search results found for query: %s", query)
#             return []
#         
#         urls = []
#         for item in data['items']:
#             if 'link' in item:
#                 urls.append(item['link'])
#         
#         return urls
#         
#     except requests.RequestException as e:
#         logger.error("Google Custom Search API request failed: %s", e)
#         return []
#     except Exception as e:
#         logger.error("Unexpected error in Google search: %s", e)
#         return []


def search_google(query: str, max_results: int = 10, sleep_interval: float = 2.0) -> List[str]:
    """
    Use Brave Search API to get URLs.
    """
    if not BRAVE_API_KEY:
        logger.warning("Brave API key not found. Cannot perform search.")
        return []
    
    try:
        # Brave Search API endpoint
        url = "https://api.search.brave.com/res/v1/web/search"
        
        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'X-Subscription-Token': BRAVE_API_KEY
        }
        
        params = {
            'q': query,
            'count': min(max_results, 20),  # Brave allows up to 20 results per request
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'web' not in data or 'results' not in data['web']:
            logger.warning("No search results found for query: %s", query)
            return []
        
        urls = []
        for item in data['web']['results']:
            if 'url' in item:
                urls.append(item['url'])
        
        return urls
        
    except requests.RequestException as e:
        logger.error("Brave Search API request failed: %s", e)
        return []
    except Exception as e:
        logger.error("Unexpected error in Brave search: %s", e)
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
        print(payload)
        return {"ok": True, "data": payload}

    except Exception as e:
        return {"ok": False, "error": str(e)}
    

websearch_agent=Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[process_websearch],
    callback_handler=PrintingCallbackHandler(),
)

# # Example usage
# if __name__ == "__main__":
#     # Example: Search by topic
#     result = websearch_agent("HDB BTO Toa Payoh July 2025 4-room flat reviews, MRT access, school proximity, resale value sentiment on TikTok and YouTube")
    
#     result2=websearch_agent("https://www.tiktok.com/discover/july-bto-launch-toa-payoh")
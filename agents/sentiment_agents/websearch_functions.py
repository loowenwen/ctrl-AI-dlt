#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reusable web aggregation utilities (search + fetch + truncate) for local and Lambda use.

Env overrides:
  MAX_RESPONSE_SIZE   (default: 220000 bytes)
  USER_AGENT          (default: macOS Chrome UA below)
  GOOGLE_MAX_RESULTS  (default: 10)
"""

from __future__ import annotations
import json
import os
import sys
import ssl
import certifi
import urllib.request
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup
from googlesearch import search as google_search  # pip: googlesearch-python

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
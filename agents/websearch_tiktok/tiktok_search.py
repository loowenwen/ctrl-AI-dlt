import json
import urllib.request
import urllib.parse
import sys
from bs4 import BeautifulSoup
from googlesearch import search 
import certifi
import os

os.environ['SSL_CERT_FILE'] = certifi.where()

MAX_RESPONSE_SIZE = 22000  # ~22 KB

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"

def get_page_content(url: str) -> str | None:
    """Fetch a web page and clean it into plain text."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='replace')
        soup = BeautifulSoup(html, 'html.parser')
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
        text = soup.get_text(separator=" ")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        cleaned = "\n".join(chunk for chunk in chunks if chunk)
        return cleaned
    except Exception as e:
        print(f"[error] failed fetching {url}: {e}")
        return None

def search_google(query: str, max_results: int = 10) -> list[str]:
    """Use googlesearch to get URLs."""
    try:
        return list(search(query, num_results=max_results, sleep_interval=2))
    except Exception as e:
        print(f"[error] google search failed: {e}")
        return []

def find_topic_sources(topic: str, max_results: int = 5) -> dict:
    """
    Find & aggregate content about a topic (e.g. 'HDB BTO Toa Payoh').

    Returns:
        { "topic": topic, "sources": [ {url, content}, ... ], "truncated": bool }
    """
    if not topic:
        return {"error": "No topic provided"}

    urls = search_google(topic, max_results=max_results)
    if not urls:
        return {"error": "No search results found"}

    aggregated, results, total_size, truncated = "", [], 0, False
    for url in urls:
        content = get_page_content(url)
        if not content:
            results.append({"url": url, "error": "Failed to fetch"})
            continue

        block = f"URL: {url}\n\n{content}\n\n{'='*100}\n\n"
        block_size = sys.getsizeof(block)

        if total_size + block_size > MAX_RESPONSE_SIZE:
            remaining = MAX_RESPONSE_SIZE - total_size
            aggregated += block[:remaining]
            results.append({
                "url": url,
                "content": block[:remaining],
                "warning": "Content truncated due to size cap"
            })
            truncated = True
            break

        aggregated += block
        total_size += block_size
        results.append({"url": url, "content": content})

    return {
        "topic": topic,
        "sources": results,
        "truncated": truncated
    }

# -------------------------
# CLI for quick testing
# -------------------------
if __name__ == "__main__":
    topic = "HDB BTO Toa Payoh July Launch 2025 TikTok videos regarding location, sentiment, price, etc"
    out = find_topic_sources(topic, max_results=5)
    print(json.dumps(out, indent=2, ensure_ascii=False))
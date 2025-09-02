import argparse
import json
import re
import time
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-SG,en;q=0.9",
}


def http_get_with_retries(url: str, headers: Dict[str, str], max_retries: int = 3, timeout: int = 20) -> str:
    backoff_seconds = 1.0
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:  # noqa: BLE001 - surface any error as-is after retries
            last_exc = exc
            if attempt < max_retries:
                time.sleep(backoff_seconds)
                backoff_seconds *= 2
            else:
                raise
    # Should not reach here
    if last_exc:
        raise last_exc
    raise RuntimeError("Unexpected state in http_get_with_retries")


def scrape_cards(
    soup: BeautifulSoup,
    card_selector: str,
    title_selector: Optional[str] = None,
    price_selector: Optional[str] = None,
    lat_attr: Optional[str] = None,
    lon_attr: Optional[str] = None,
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not card_selector:
        return items

    cards = soup.select(card_selector)
    for c in cards:
        title_text: Optional[str] = None
        price_text: Optional[str] = None
        lat_val: Optional[str] = None
        lon_val: Optional[str] = None

        if title_selector:
            el = c.select_one(title_selector)
            if el:
                title_text = el.get_text(strip=True)

        if price_selector:
            el = c.select_one(price_selector)
            if el:
                price_text = el.get_text(strip=True)

        if lat_attr:
            lat_val = c.get(lat_attr)
        if lon_attr:
            lon_val = c.get(lon_attr)

        items.append({
            "name": title_text,
            "price": price_text,
            "lat": lat_val,
            "lon": lon_val,
        })
    return items


def scrape_json_from_scripts(soup: BeautifulSoup, inline_key_regex: Optional[str]) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []

    # 1) JSON-LD blocks
    for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            if not s.string:
                continue
            data = json.loads(s.string)
            if isinstance(data, dict):
                collected.append(data)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        collected.append(item)
        except Exception:
            continue

    # 2) Inline JSON like window.__INITIAL_STATE__ = {...}; controlled by regex
    if inline_key_regex:
        pattern = re.compile(inline_key_regex)
        for s in soup.find_all("script"):
            content = s.string or s.text or ""
            if not content:
                continue
            if not pattern.search(content):
                continue
            # Try to extract the first top-level JSON object in the script
            m = re.search(r"(\{[\s\S]*\})", content)
            if not m:
                continue
            json_str = m.group(1)
            try:
                data = json.loads(json_str)
                if isinstance(data, dict):
                    collected.append(data)
            except Exception:
                continue

    return collected


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape static HTML or embedded JSON and print items as JSON")
    parser.add_argument("--url", required=True, help="Target page URL")
    parser.add_argument("--card", default="", help="CSS selector for each card/container")
    parser.add_argument("--title", default="", help="CSS selector for title inside card")
    parser.add_argument("--price", default="", help="CSS selector for price inside card")
    parser.add_argument("--lat-attr", dest="lat_attr", default="", help="Attribute on card holding latitude")
    parser.add_argument("--lon-attr", dest="lon_attr", default="", help="Attribute on card holding longitude")
    parser.add_argument(
        "--inline-json-key",
        default="",
        help="Regex to detect inline script containing JSON (e.g. __INITIAL_STATE__)",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    html = http_get_with_retries(args.url, DEFAULT_HEADERS)
    soup = BeautifulSoup(html, "lxml")

    items_from_cards: List[Dict[str, Any]] = []
    if args.card:
        items_from_cards = scrape_cards(
            soup,
            card_selector=args.card,
            title_selector=(args.title or None),
            price_selector=(args.price or None),
            lat_attr=(args.lat_attr or None),
            lon_attr=(args.lon_attr or None),
        )

    items_from_json_blocks: List[Dict[str, Any]] = []
    if args.inline_json_key:
        items_from_json_blocks = scrape_json_from_scripts(
            soup, inline_key_regex=args.inline_json_key
        )

    output: Dict[str, Any] = {
        "url": args.url,
        "items": items_from_cards,
        "embedded_json": items_from_json_blocks,
    }

    if args.pretty:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(output, separators=(",", ":"), ensure_ascii=False))


if __name__ == "__main__":
    main()



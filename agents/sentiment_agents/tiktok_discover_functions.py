"""
Reusable TikTok Discover scraper (Playwright, sync).
- Exposes scrape_discover() which returns a Python dict (no printing).
- Safe to import in AWS Lambda (assuming Playwright runtime/layer present).
"""

from __future__ import annotations
import json
import time
from typing import List, Dict, Any, Optional

from playwright.sync_api import sync_playwright, Page

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36"
)

# ------------------------- helpers -------------------------

def _extract_sigi_state(page: Page) -> Optional[Dict[str, Any]]:
    try:
        data = page.evaluate("() => window.SIGI_STATE || null")
        if data:
            return data
    except Exception:
        pass
    try:
        raw = page.eval_on_selector('#SIGI_STATE', 'el => el.textContent')
        return json.loads(raw) if raw else None
    except Exception:
        return None

def _items_from_sigi(sigi: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prefer ItemModule. If empty, try to reconstruct IDs from other lists.
    Return a dict mapping video_id -> (possibly sparse) item dict.
    """
    item_module: Dict[str, Any] = (sigi.get("ItemModule") or {})
    if item_module:
        return item_module

    # Mine IDs from any nested object that exposes a "list" of numeric IDs
    candidate_ids = set()

    def collect_ids(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "list" and isinstance(v, list):
                    for x in v:
                        xs = str(x)
                        if xs.isdigit() and len(xs) >= 10:
                            candidate_ids.add(xs)
                else:
                    collect_ids(v)
        elif isinstance(obj, list):
            for it in obj:
                collect_ids(it)

    for key in ("ItemList", "ExploreList", "TopicPage", "TopicModule", "DiscoverList", "SearchModule"):
        if key in sigi:
            collect_ids(sigi[key])

    # Sparse shells (no metadata yet); DOM enrich later
    return {vid: {"id": vid} for vid in candidate_ids}

def _scroll_to_load(page: Page, target_count: int, max_rounds: int = 24, sleep_s: float = 0.6):
    last_height = 0
    for _ in range(max_rounds):
        page.mouse.wheel(0, 6000)
        time.sleep(sleep_s)
        count = page.eval_on_selector_all('a[href*="/video/"]', "els => els.length") or 0
        if count >= target_count:
            break
        h = page.evaluate("() => document.body.scrollHeight")
        if h == last_height:
            break
        last_height = h

def _dom_cards(page: Page):
    sels = [
        'div[data-e2e*="search_card"]',
        'div[data-e2e*="search-card"]',
        'div[data-e2e*="video-card"]',
        'div[data-e2e*="search-video-card"]',
    ]
    for sel in sels:
        els = page.query_selector_all(sel)
        if els:
            return els
    # fallback: look for any container with a video link
    anchors = page.query_selector_all('a[href*="/video/"]')
    return [a.evaluate_handle("a => a.closest('div')").as_element() for a in anchors if a.evaluate_handle("a => a.closest('div')")]

def _text_or_none(el, sel: str) -> Optional[str]:
    try:
        return el.eval_on_selector(sel, "n => n ? n.textContent.trim() : null")
    except Exception:
        return None

def _href_or_none(el, sel: str) -> Optional[str]:
    try:
        return el.eval_on_selector(sel, "a => a ? a.href.split('?')[0] : null")
    except Exception:
        return None

def _attr_or_none(el, sel: str, attr: str) -> Optional[str]:
    try:
        return el.eval_on_selector(sel, f"n => n ? n.getAttribute('{attr}') : null")
    except Exception:
        return None

def _dom_snapshot(card) -> Dict[str, Any]:
    """
    Grab a broad set of fields from the card DOM. We don't try to interpret;
    we just capture what's commonly present.
    """
    data: Dict[str, Any] = {}
    data["url"] = _href_or_none(card, 'a[href*="/video/"]')
    # caption candidates
    for sel in (
        '[data-e2e*="desc"]',
        '[data-e2e*="search-card-desc"]',
        'span[class*="Desc"]',
        'div[class*="Desc"]',
        'div:has(> a[href*="/video/"]) + div span',
    ):
        txt = _text_or_none(card, sel)
        if txt:
            data["caption"] = txt
            break
    # author link / name
    a = _href_or_none(card, 'a[href^="https://www.tiktok.com/@"]')
    if a and "/@" in a:
        data["author_url"] = a
        data["author"] = a.rstrip("/").rsplit("/@", 1)[-1]
    uname = _text_or_none(card, '[data-e2e*="user-name"], [class*="UserName"], [class*="user-name"]')
    if uname:
        data["author_display"] = uname
    # cover: img src or bg-image
    img = _attr_or_none(card, "img[src]", "src")
    if img:
        data["cover"] = img
    else:
        try:
            bg = card.eval_on_selector('[style*="background-image"]', "n => n ? getComputedStyle(n).backgroundImage : null")
            if bg and 'url("' in bg:
                data["cover"] = bg.split('url("', 1)[1].split('"', 1)[0]
        except Exception:
            pass
    # any counters if present
    for label, sel in {
        "likes": '[data-e2e*="like-count"], [class*="like-count"]',
        "comments": '[data-e2e*="comment-count"], [class*="comment-count"]',
        "shares": '[data-e2e*="share-count"], [class*="share-count"]'
    }.items():
        val = _text_or_none(card, sel)
        if val:
            data[f"dom_{label}"] = val
    return data

def _merge_item(vid: str, sigi_item: Optional[Dict[str, Any]], dom: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a maximal record. Keep raw blobs under 'sigi_item' and 'dom' to avoid losing fields.
    Also lift a few obvious top-level conveniences: id, url.
    """
    out: Dict[str, Any] = {"id": str(vid)}
    if sigi_item:
        out["sigi_item"] = sigi_item  # full raw item (video, author, stats, etc.)
        # try to surface a canonical url if present
        share_url = sigi_item.get("shareUrl") or sigi_item.get("shareMeta", {}).get("shareUrl")
        if share_url:
            out["url"] = share_url
    if dom:
        out["dom"] = dom
        if not out.get("url") and dom.get("url"):
            out["url"] = dom["url"]
    # final fallback URL
    if not out.get("url"):
        # if we know author from sigi, synthesize
        author = (sigi_item or {}).get("author")
        out["url"] = f"https://www.tiktok.com/@{author}/video/{vid}" if author else f"https://www.tiktok.com/video/{vid}"
    return out

# ------------------------- public API -------------------------

def scrape_discover(
    url: str,
    *,
    limit: int = 50,
    timeout_s: int = 30,
    include_page: bool = False
) -> Dict[str, Any]:
    """
    Core scraper. Returns a dict:
      {
        "items": [ { "id": "...", "url": "...", "sigi_item": {...}, "dom": {...} }, ... ],
        "page": { "sigi_state": {...} }   # only if include_page=True
      }
    Raises exceptions to the caller (so Lambda handler / CLI can decide).
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=UA, viewport={"width": 1366, "height": 900})
        page = context.new_page()

        if "lang=" not in url:
            url = url + ("&lang=en" if "?" in url else "?lang=en")

        page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
        page.wait_for_timeout(1200)
        try:
            page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            pass

        _scroll_to_load(page, target_count=limit)

        sigi = _extract_sigi_state(page) or {}
        items_by_id: Dict[str, Any] = _items_from_sigi(sigi) if sigi else {}

        # DOM index keyed by video id (so we can merge)
        dom_by_id: Dict[str, Dict[str, Any]] = {}
        for card in _dom_cards(page):
            dom = _dom_snapshot(card)
            href = dom.get("url")
            if not href or "/video/" not in href:
                continue
            vid = href.rsplit("/video/", 1)[-1]
            dom_by_id[vid] = dom

        # Build results by union of IDs seen in SIGI and DOM
        all_ids = set(items_by_id.keys()) | set(dom_by_id.keys())
        results: List[Dict[str, Any]] = []
        for vid in all_ids:
            results.append(_merge_item(vid, items_by_id.get(vid), dom_by_id.get(vid)))

        # Order: prefer DOM order for nicer UX
        ordered: List[Dict[str, Any]] = []
        for card in _dom_cards(page):
            href = _href_or_none(card, 'a[href*="/video/"]')
            if not href:
                continue
            vid = href.rsplit("/video/", 1)[-1]
            for i, r in enumerate(results):
                if r["id"] == vid:
                    ordered.append(r)
                    results.pop(i)
                    break
        ordered.extend(results)  # leftovers
        ordered = ordered[:limit]

        payload: Dict[str, Any] = {"items": ordered}
        if include_page:
            payload["page"] = {"sigi_state": sigi}

        browser.close()
        return payload
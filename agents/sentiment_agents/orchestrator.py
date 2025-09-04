#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Orchestrator Agent (pure Python, no Lambda invoke)
- Accepts either a direct topic string OR `query_params` (used by query_builder) OR a raw `query` string; if `topic` is absent, it will synthesize one from `query`/`query_params`.
- Calls your websearch function to fetch URLs by topic (or takes direct URLs)
- Classifies each URL
- For video URLs -> calls your video ingestion function
- For TikTok Discover URLs -> calls tiktok discover, then ingests top-N items
- Returns a unified JSON: { ok, data: { items: [...] }, meta, error? } to a sentiment_analysis agent 
- Returns final sentiment
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import re
import concurrent.futures as cf
import time
import random

# ---- import your provided functions ----
from websearch import process_websearch
from tiktok_discovery import process_tiktok_discover
from video_ingestion import process_video

# ---- optional agents: query builder & sentiment ----
try:
    # prefer an explicit function if your module exposes it
    from query_builder import build_query as qb_build_query  # type: ignore
except Exception:
    try:
        from query_builder import build_topic_query as qb_build_query  # type: ignore
    except Exception:
        qb_build_query = None  # will be handled at runtime

try:
    from sentiment_agent import analyze_sentiment as sa_analyze_sentiment  # type: ignore
except Exception:
    sa_analyze_sentiment = None  # will be handled at runtime

# ----------------- helpers -----------------

def _ok(data: Dict[str, Any], meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {"ok": True, "data": data, "meta": (meta or {"component": "orchestrator"}), "error": None}

def _err(msg: str, meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {"ok": False, "data": {}, "meta": (meta or {"component": "orchestrator"}), "error": msg}

def classify_url(u: str) -> str:
    """
    Return one of: 'youtube_video' | 'tiktok_discover' | 'tiktok_video' | 'generic_video' | 'article'
    """
    if not isinstance(u, str) or not u:
        return "article"
    low = u.lower()
    if "tiktok.com/discover" in low:
        return "tiktok_discover"
    if "tiktok.com" in low:
        return "tiktok_video"
    if re.search(r"(youtube\.com/watch|youtu\.be/)", low):
        return "youtube_video"
    if re.search(r"\.(mp4|m3u8|webm|mov|mkv)(\?|$)", low):
        return "generic_video"
    return "article"

def _safe_get(d: Dict[str, Any], *keys, default=None):
    x = d
    for k in keys:
        if not isinstance(x, dict) or k not in x:
            return default
        x = x[k]
    return x

def _maybe_build_topic(topic: Optional[str], query_params: Optional[dict]) -> Tuple[Optional[str], dict]:
    """If topic is empty and query_params are provided and a query builder is available,
    call it to synthesize a natural topic string (and optional domain hints).
    Returns (topic, qb_meta).
    """
    qb_meta: dict = {"used_query_builder": False}
    if topic and isinstance(topic, str) and topic.strip():
        return topic, qb_meta
    if not query_params or qb_build_query is None:
        return topic, qb_meta
    try:
        out = qb_build_query(**query_params) if isinstance(query_params, dict) else qb_build_query(query_params)
        qb_meta["used_query_builder"] = True
        # Support either a string or a dict payload
        if isinstance(out, str):
            return out.strip() or topic, qb_meta
        if isinstance(out, dict):
            # Common keys we might accept from your query builder
            new_topic = out.get("topic") or out.get("query") or out.get("llm_topic")
            qb_meta["qb"] = {k: out.get(k) for k in ("allow_domains","block_domains","model","raw") if k in out}
            return (str(new_topic).strip() if new_topic else topic), qb_meta
    except Exception as e:
        qb_meta["qb_error"] = str(e)
    return topic, qb_meta


def _collect_text_for_sentiment(items: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Extract normalized text blobs and lightweight source map from orchestrated items.
    Sources shape: [{"url", "kind", "has_video", "title"}]
    """
    texts: List[str] = []
    sources: List[Dict[str, Any]] = []
    def _add_text(s: Optional[str]):
        if isinstance(s, str):
            st = s.strip()
            if st:
                texts.append(st)
    for it in items:
        url = it.get("url")
        kind = it.get("kind")
        title = it.get("title")
        has_video = False
        # page/article text
        _add_text(it.get("content"))
        # video outputs for single videos
        v = it.get("video") or {}
        if isinstance(v, dict) and v.get("ok"):
            nova_text = _safe_get(v, "data", "nova")
            _add_text(nova_text)
            # transcript optional
            _add_text(_safe_get(v, "data", "transcript"))
            has_video = True
        # tiktok discover bundle
        for sub in it.get("videos") or []:
            if isinstance(sub, dict):
                vv = sub.get("video") or {}
                if isinstance(vv, dict) and vv.get("ok"):
                    _add_text(_safe_get(vv, "data", "nova"))
                    _add_text(_safe_get(vv, "data", "transcript"))
                    has_video = True
        sources.append({"url": url, "kind": kind, "title": title, "has_video": has_video})
    return texts, sources

# ----------------- core orchestrator -----------------

def run_orchestrator(
    topic: Optional[str] = None,
    query: Optional[str] = None,
    urls: Optional[List[str]] = None,
    *,
    # NEW: front agent inputs
    query_params: Optional[Dict[str, Any]] = None,
    use_query_builder: bool = True,
    # existing knobs
    top_discover: int = 10,
    web_max_results: int = 10,
    web_allow_domains: Optional[List[str]] = None,
    web_block_domains: Optional[List[str]] = None,
    parallel_videos: bool = True,
    max_workers: int = 4,
    video_prompt: str = "Summarize key points, locations, dates, figures, and caveats in bullet points. Highlight the positives and negatives.",
    return_transcript: bool = False,
    retry_attempts: int = 3,
    backoff_base: float = 1.8,
    backoff_jitter: float = 0.25,
    throttle_sleep: float = 0.0,
    # NEW: back agent flag
    run_sentiment: bool = True,
) -> Dict[str, Any]:
    """
    Unified pipeline:
      - topic mode: use process_websearch(topic=...) to get URLs
      - urls mode: use provided list
      - classify each URL and dispatch:
          * youtube/tiktok/generic video -> process_video
          * tiktok_discover -> process_tiktok_discover then process_video for top N
          * article -> keep as-is
      - combine into a single items[] list

    Returns:
      { ok, data: { items: [...] }, meta, error? }
    """

    qb_meta = {}

    # Prefer explicit topic if given; else allow a raw query string; else try query_builder
    eff_topic: Optional[str] = (topic.strip() if isinstance(topic, str) and topic.strip() else None)
    if not eff_topic and isinstance(query, str) and query.strip():
        eff_topic = query.strip()

    if not eff_topic and use_query_builder:
        eff_topic, qb_meta = _maybe_build_topic(None, query_params)

    # Last-resort naive synthesis if no builder available
    if not eff_topic and isinstance(query_params, dict) and query_params:
        # Create a simple, readable topic from common keys
        parts = []
        for k in ("intent", "location", "flat_type", "age"):
            v = query_params.get(k)
            if v is None:
                continue
            if isinstance(v, (list, tuple)):
                v = ", ".join(map(str, v))
            parts.append(f"{k}: {v}")
        if parts:
            eff_topic = " | ".join(parts)

    # 1) Gather URLs
    if urls and isinstance(urls, list) and len(urls) > 0:
        # direct URLs mode
        items_in = [{"url": u} for u in urls if isinstance(u, str) and u]
    else:
        if not eff_topic or not isinstance(eff_topic, str):
            return _err("Provide either topic/query or urls, or pass query_params for query builder.")
        # Allow the front agent to hint domains if the caller didn't pass any
        if not web_allow_domains and isinstance(qb_meta.get("qb"), dict):
            web_allow_domains = qb_meta["qb"].get("allow_domains") or web_allow_domains
        if not web_block_domains and isinstance(qb_meta.get("qb"), dict):
            web_block_domains = qb_meta["qb"].get("block_domains") or web_block_domains

        web_out = process_websearch(
            topic=eff_topic,
            max_results=web_max_results,
            allow_domains=web_allow_domains,
            block_domains=web_block_domains,
        )
        if not web_out.get("ok"):
            return _err(f"websearch failed: {web_out.get('error') or 'unknown'}")

        # websearch shapes supported: data.sources[] or data.results[] or data.items[] or data.urls[]
        data = web_out.get("data", {})
        items_in = []
        # try common keys in priority order
        for key in ("items", "sources", "results", "urls"):
            arr = data.get(key)
            if isinstance(arr, list) and arr:
                for rec in arr:
                    if isinstance(rec, str):
                        items_in.append({
                            "url": rec,
                            "title": None,
                            "source": None,
                            "content": None,
                            "meta": {}
                        })
                    elif isinstance(rec, dict):
                        url = rec.get("url") or rec.get("link") or rec.get("href")
                        if url:
                            items_in.append({
                                "url": url,
                                "title": rec.get("title"),
                                "source": rec.get("source"),
                                "content": rec.get("content") or rec.get("text") or rec.get("summary"),
                                "meta": {k: rec.get(k) for k in rec.keys() if k not in {"url","link","href","title","source","content","text","summary"}}
                            })
                break

    # de-dup while preserving order
    seen = set()
    items_in = [it for it in items_in if not (it["url"] in seen or seen.add(it["url"]))]

    # 2) Classify
    for it in items_in:
        it["kind"] = classify_url(it["url"])

    unified: List[Dict[str, Any]] = []

    def _ingest_with_retry(u: str) -> Dict[str, Any]:
        """Call process_video with retries on Bedrock throttling and transient errors."""
        attempt = 0
        last: Dict[str, Any] | None = None
        while attempt < max(1, retry_attempts):
            if throttle_sleep and attempt == 0:
                time.sleep(throttle_sleep)
            resp = process_video(
                input_path=u,
                mode="transcribe_to_text",
                prompt=video_prompt,
                return_transcript=return_transcript,
            )
            last = resp
            ok = bool(resp.get("ok"))
            err = str(resp.get("error", ""))
            # success
            if ok:
                return {"url": u, "video": resp}
            # retry only for throttling / rate / timeout style errors
            retryable = any(s in err for s in (
                "ThrottlingException",
                "Too many requests",
                "Rate exceeded",
                "Timeout",
                "timed out",
                "429",
            ))
            attempt += 1
            if not retryable or attempt >= retry_attempts:
                break
            # exponential backoff with jitter
            sleep_s = (backoff_base ** attempt) + (random.random() * backoff_jitter)
            time.sleep(sleep_s)
        return {"url": u, "video": (last or {"ok": False, "error": "unknown error"})}

    # 3) TikTok Discover first (so we can add its discovered videos)
    for it in items_in:
        if it["kind"] != "tiktok_discover":
            continue
        d = process_tiktok_discover(url=it["url"], limit=top_discover)
        if not d.get("ok"):
            unified.append({
                "url": it["url"], "kind": "tiktok_discover",
                "discover": d, "videos": [], "note": "discover failed"
            })
            continue
        sub_items = _safe_get(d, "data", "items", default=[]) or []
        # keep only those with url
        sub_urls = [s.get("url") for s in sub_items if isinstance(s, dict) and s.get("url")]
        # fan out to video ingestion (optionally parallel) with retries
        if parallel_videos and sub_urls:
            with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
                sub_results = list(ex.map(_ingest_with_retry, sub_urls))
        else:
            sub_results = [_ingest_with_retry(u) for u in sub_urls]

        unified.append({
            "url": it["url"],
            "kind": "tiktok_discover",
            "title": it.get("title"),
            "source": it.get("source"),
            "content": it.get("content"),  # if any text was fetched for the discover page
            "meta": it.get("meta", {}),
            "discover": d,
            "videos": sub_results
        })

    # 4) Handle the rest
    def _handle_single(it: Dict[str, Any]) -> Dict[str, Any]:
        u, k = it["url"], it["kind"]
        base = {
            "url": u,
            "kind": k if k != "article" else "article",
            "title": it.get("title"),
            "source": it.get("source"),
            "content": it.get("content"),  # include website/page text when available
            "meta": it.get("meta", {}),
        }
        if k in ("youtube_video", "tiktok_video", "generic_video"):
            r = _ingest_with_retry(u)
            base["video"] = r.get("video")
            return base
        else:
            base["note"] = "no video ingestion"
            return base

    remaining = [it for it in items_in if it["kind"] != "tiktok_discover"]
    if parallel_videos and remaining:
        with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
            unified.extend(list(ex.map(_handle_single, remaining)))
    else:
        unified.extend(_handle_single(it) for it in remaining)

    sentiment = None
    if run_sentiment:
        if sa_analyze_sentiment is None:
            sentiment = {"ok": False, "error": "sentiment_agent.analyze_sentiment not available"}
        else:
            texts, sources = _collect_text_for_sentiment(unified)
            try:
                # Expecting analyze_sentiment(text_blobs: List[str], sources: List[dict]) -> dict
                sentiment = sa_analyze_sentiment(texts, sources=sources)
            except TypeError:
                # Fallback if the agent only accepts (texts)
                sentiment = sa_analyze_sentiment(texts)
            except Exception as e:
                sentiment = {"ok": False, "error": str(e)}

    meta = {"component": "orchestrator", "version": "1.1.1"}
    if eff_topic:
        meta["topic"] = eff_topic
    if qb_meta:
        meta["query_builder"] = qb_meta
    payload = {"items": unified}
    if sentiment is not None:
        payload["sentiment"] = sentiment
    return _ok(payload, meta=meta)

# ----------------- example -----------------

if __name__ == "__main__":
    print("\n--- Example A: raw query string (no topic, no builder) ---")
    out = run_orchestrator(
        topic=None,
        query="HDB BTO July 2025 Toa Payoh 4-room reviews sentiment",
        web_max_results=8,
        top_discover=5,
        parallel_videos=True,
        max_workers=4,
        return_transcript=False,
        run_sentiment=True,
        use_query_builder=False,
    )
    import json
    print(json.dumps(out, indent=2, ensure_ascii=False))

    print("\n--- Example B: query_params -> query_builder synthesizes topic ---")
    out = run_orchestrator(
        topic=None,
        query_params={
            "age": 29,
            "flat_type": "4-room",
            "location": "Toa Payoh",
            "intent": "HDB BTO July 2025 launch sentiment",
            "focus": ["TikTok", "YouTube", "reviews", "guides", "explainers"],
            "concerns": ["MRT", "schools", "resale value"],
        },
        web_max_results=8,
        top_discover=5,
        parallel_videos=True,
        max_workers=4,
        return_transcript=False,
        run_sentiment=True,
        use_query_builder=True,
    )
    print(json.dumps(out, indent=2, ensure_ascii=False))
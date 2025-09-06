#!/usr/bin/env python3
"""
Clean and streamlined BTO web scraper using Playwright.
"""

import argparse
import asyncio
import csv
import json
from typing import Any, Dict, List, Optional, Tuple
from playwright.async_api import async_playwright

# ------------------------
# Data Normalization Helpers
# ------------------------

def normalize_payload(data: Any) -> List[Dict[str, Any]]:
    """Transform API response into a clean format with essential BTO fields."""
    items: List[Dict[str, Any]] = []
    data_list = (
        data.get("features") or data.get("data") or data.get("items") or
        data.get("results") or []
    ) if isinstance(data, dict) else data

    if not isinstance(data_list, list):
        return items

    for item in data_list:
        try:
            coords = item.get("coordinates") or item.get("geometry", {}).get("coordinates")
            if not coords:
                continue
            lon, lat = (json.loads(coords) if isinstance(coords, str) else coords[:2])[0:2][::-1]
            props = item.get("properties", {})
            desc = (props.get("description") or [{}])[0]
            town = desc.get("town") or props.get("town") or desc.get("projectName")
            if not town:
                continue
            items.append({
                "name": town,
                "town": desc.get("town") or props.get("town", town),
                "flatType": desc.get("flatType") or props.get("flatType", "N/A"),
                "region": props.get("region", ""),
                "lat": round(float(lat), 6),
                "lon": round(float(lon), 6)
            })
        except Exception:
            continue

    return items

def dedupe_sort(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicates and sort by name, lat, lon."""
    seen: set[Tuple[str, float, float]] = set()
    out: List[Dict[str, Any]] = []

    for it in items:
        key = (it.get("name"), it.get("lat"), it.get("lon"))
        if key not in seen:
            seen.add(key)
            out.append(it)

    return sorted(out, key=lambda x: (x["name"], x["lat"], x["lon"]))

def unique_by_name(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only the first entry per BTO name."""
    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    for it in items:
        name = it.get("name")
        if name and name not in seen:
            seen.add(name)
            unique.append(it)
    return unique

def extract_coords(items: List[Dict[str, Any]]) -> List[List[float]]:
    """Extract only lat/lon pairs."""
    seen: set[Tuple[float, float]] = set()
    coords: List[List[float]] = []

    for it in items:
        try:
            lat, lon = float(it["lat"]), float(it["lon"])
            pair = (lat, lon)
            if pair not in seen:
                seen.add(pair)
                coords.append([lat, lon])
        except Exception:
            continue
    return coords


async def fetch_bto_data(
    url: str,
    headless: bool = True,
    verbose: bool = False,
    pretty: bool = False,
    csv_path: Optional[str] = None,
    by_name: bool = False,
    coords_only: bool = False
) -> None:
    """Fetch BTO data and save as clean JSON or CSV."""
    results: List[Dict[str, Any]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()

        async def handle_response(resp):
            try:
                if "getCoordinatesByFilters" in resp.url or "coordinates" in resp.url:
                    try:
                        payload = await resp.json()
                        results.extend(normalize_payload(payload))
                    except Exception as e_json:
                        if verbose:
                            print(f"[warn] JSON parse failed for {resp.url}: {e_json}")
            except Exception as e:
                if verbose:
                    print(f"[warn] response handler: {e}")

        page.on("response", handle_response)
        await page.goto(url, wait_until="domcontentloaded")

        # Accept cookie banners
        for selector in ('button#onetrust-accept-btn-handler', 'button:has-text("Accept All")', 'button:has-text("I Accept")'):
            try:
                btn = await page.query_selector(selector)
                if btn:
                    await btn.click()
                    break
            except Exception:
                continue

        try:
            await page.wait_for_response(lambda r: ("getCoordinates" in r.url or "coordinates" in r.url) and r.status == 200, timeout=15000)
        except Exception:
            await asyncio.sleep(3)

        await asyncio.sleep(1)
        await browser.close()

    # Process results
    results = dedupe_sort(results)
    if by_name:
        results = unique_by_name(results)

    # Output
    if coords_only:
        coords = extract_coords(results)
        if csv_path:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["lat", "lon"])
                writer.writerows(coords)
            if verbose or pretty:
                print(f"Wrote {len(coords)} coordinates to {csv_path}")
        else:
            print(json.dumps(coords, indent=2 if pretty else None))
        return

    json_path = "bto_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2 if pretty else None)
    if verbose or pretty:
        print(f"Saved {len(results)} BTO records to {json_path}")

    if csv_path and results:
        fieldnames = ["name", "town", "flatType", "region", "lat", "lon"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        if verbose or pretty:
            print(f"Wrote {len(results)} rows to {csv_path}")

# ------------------------
# CLI Argument Parsing
# ------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch BTO coordinates and save as clean JSON")
    parser.add_argument("--url", default="https://homes.hdb.gov.sg/home/finding-a-flat", help="Target URL")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument("--verbose", action="store_true", help="Print network logs and warnings")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--csv", dest="csv_path", default="", help="Write output to CSV path instead of JSON")
    parser.add_argument("--unique-by-name", action="store_true", help="Keep only the first entry per estate/town name")
    parser.add_argument("--coords-only", action="store_true", help="Output only coordinate pairs [[lat, lon], ...]")
    return parser.parse_args()

# ------------------------
# Entry Point
# ------------------------

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(fetch_bto_data(
        url=args.url,
        headless=args.headless,
        verbose=args.verbose,
        pretty=args.pretty,
        csv_path=args.csv_path or None,
        by_name=args.unique_by_name,
        coords_only=args.coords_only
    ))

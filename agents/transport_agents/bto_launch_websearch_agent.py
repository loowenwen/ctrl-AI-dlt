import argparse
import asyncio
import csv
import json
from typing import Any, Dict, List, Optional, Tuple
from playwright.async_api import async_playwright

def normalise_coordinates_payload(data: Any) -> List[Dict[str, Any]]:
    """Transform API response into a clean format with essential BTO fields."""
    items: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        data = data.get("features") or data.get("data") or data.get("items") or data.get("results") or []
    if not isinstance(data, list):
        return items
    for item in data:
        try:
            coords = item.get("coordinates") or item.get("geometry", {}).get("coordinates")
            if not coords:
                continue
            if isinstance(coords, str):
                lat, lon = json.loads(coords)
            else:
                lon, lat = coords[0], coords[1]
            props = item.get("properties", {})
            desc = props.get("description", [{}])[0] if props.get("description") else {}
            town = desc.get("town") or props.get("town") or desc.get("projectName")
            if not town:
                continue
            bto_info = {
                "name": town,
                "town": desc.get("town") or props.get("town", town),
                "flatType": desc.get("flatType") or props.get("flatType", "N/A"),
                "region": props.get("region", ""),
                "lat": round(float(lat), 6),
                "lon": round(float(lon), 6)
            }
            if bto_info["name"]:
                items.append(bto_info)
        except Exception:
            continue
    return items

def dedupe_and_sort(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicates and sort by name, lat, lon."""
    seen: set[Tuple[str, float, float]] = set()
    out: List[Dict[str, Any]] = []
    for it in items:
        key = (it.get("name"), it.get("lat"), it.get("lon"))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    out.sort(key=lambda x: (str(x.get("name") or ""), float(x.get("lat") or 0), float(x.get("lon") or 0)))
    return out

def unique_by_name(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only the first entry per BTO name."""
    seen_names: set[str] = set()
    unique: List[Dict[str, Any]] = []
    for it in items:
        name = str(it.get("name") or "")
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        unique.append(it)
    return unique

def extract_coords_only(items: List[Dict[str, Any]]) -> List[List[float]]:
    """Extract only lat/lon pairs."""
    seen_pairs: set[Tuple[float, float]] = set()
    coords: List[List[float]] = []
    for it in items:
        try:
            lat = float(it.get("lat"))
            lon = float(it.get("lon"))
            pair = (lat, lon)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            coords.append([lat, lon])
        except Exception:
            continue
    return coords

async def run(url: str, headless: bool, verbose: bool, pretty: bool, csv_path: Optional[str], by_name: bool, coords_only: bool) -> None:
    """Fetch BTO data and save as clean JSON or CSV."""
    results: List[Dict[str, Any]] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()

        async def handle_response(response):
            try:
                u = response.url
                if verbose:
                    print(f"[XHR] {response.status} {u}")
                if "getCoordinatesByFilters" in u or "coordinates" in u:
                    try:
                        payload = await response.json()
                        results.extend(normalise_coordinates_payload(payload))
                    except Exception as e_json:
                        if verbose:
                            print(f"[warn] JSON parse failed for {u}: {e_json}")
            except Exception as e:
                if verbose:
                    print(f"[warn] response handler: {e}")

        page.on("response", handle_response)
        await page.goto(url, wait_until="domcontentloaded")

        try:
            for sel in (
                'button#onetrust-accept-btn-handler',
                'button:has-text("Accept All")',
                'button:has-text("I Accept")',
            ):
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    break
        except Exception:
            pass

        try:
            await page.wait_for_response(lambda r: ("getCoordinates" in r.url or "coordinates" in r.url) and r.status == 200, timeout=15000)
        except Exception:
            await asyncio.sleep(3)

        await asyncio.sleep(1)
        await browser.close()

    results = dedupe_and_sort(results)
    if by_name:
        results = unique_by_name(results)

    json_output_path = "bto_data.json"
    if coords_only:
        coords = extract_coords_only(results)
        if csv_path:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["lat", "lon"])
                writer.writerows(coords)
            if verbose or pretty:
                print(f"Wrote {len(coords)} coordinate pairs to {csv_path}")
        else:
            output = json.dumps(coords, indent=2 if pretty else None, separators=(",", ":") if not pretty else None)
            print(output)
        return

    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2 if pretty else None)
    if verbose or pretty:
        print(f"Saved {len(results)} BTO records to {json_output_path}")

    if csv_path:
        if results:
            fieldnames = ["name", "town", "flatType", "region", "lat", "lon"]
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in results:
                    writer.writerow(row)
            if verbose or pretty:
                print(f"Wrote {len(results)} rows to {csv_path}")
        else:
            print("No results to write.")

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    ap = argparse.ArgumentParser(description="Fetch BTO coordinates and save as clean JSON")
    ap.add_argument("--url", default="https://homes.hdb.gov.sg/home/finding-a-flat", help="Target URL")
    ap.add_argument("--headless", action="store_true", help="Run browser headless")
    ap.add_argument("--verbose", action="store_true", help="Print network logs and warnings")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    ap.add_argument("--csv", dest="csv_path", default="", help="Write output to CSV path instead of JSON")
    ap.add_argument("--unique-by-name", action="store_true", help="Keep only the first entry per estate/town name")
    ap.add_argument("--coords-only", action="store_true", help="Output only coordinate pairs [[lat, lon], ...]")
    return ap.parse_args()

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(url=args.url, headless=args.headless, verbose=args.verbose, pretty=args.pretty, csv_path=(args.csv_path or None), by_name=args.unique_by_name, coords_only=args.coords_only))
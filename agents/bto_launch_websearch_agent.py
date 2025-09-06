import argparse
import asyncio
import csv
import json
from typing import Any, Dict, List, Optional, Tuple
from playwright.async_api import async_playwright


def normalise_coordinates_payload(data: Any) -> List[Dict[str, Any]]:
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
            desc = None
            try:
                desc = (props.get("description") or [{}])[0]
            except Exception:
                desc = {}
            town = (desc or {}).get("town") or props.get("town") or (desc or {}).get("projectName")
            if not town:
                continue

            flat_types = (desc or {}).get("flatType") or props.get("flatType") or ["N/A"]
            if isinstance(flat_types, str):
                flat_types = [flat_types]

            items.append({
                "name": town,
                "lat": round(float(lat), 6),
                "lon": round(float(lon), 6),
                "flatTypes": flat_types
            })
        except Exception:
            continue
    return items


def dedupe_and_sort(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[Tuple[Any, Any]] = set()
    out: List[Dict[str, Any]] = []
    for it in items:
        key = (it.get("lat"), it.get("lon"))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    out.sort(key=lambda x: (str(x.get("name") or ""), float(x.get("lat") or 0), float(x.get("lon") or 0)))
    return out


def add_name_suffixes(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Append _A, _B, etc. to BTOs with the same name to differentiate them
    while preserving all other data.
    """
    name_counts: Dict[str, int] = {}
    out: List[Dict[str, Any]] = []

    for it in items:
        base_name = it.get("name", "Unknown")
        count = name_counts.get(base_name, 0)
        if count > 0:
            suffix = chr(64 + count + 1)  # 65='A'
            it["name"] = f"{base_name}_{suffix}"
        name_counts[base_name] = count + 1
        out.append(it)
    return out


def extract_coords_only(items: List[Dict[str, Any]]) -> List[List[float]]:
    seen_pairs: set[Tuple[float, float]] = set()
    coords: List[List[float]] = []
    for it in items:
        try:
            lat = float(it.get("lat"))
            lon = float(it.get("lon"))
        except Exception:
            continue
        pair = (lat, lon)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        coords.append([lat, lon])
    return coords


async def run(url: str, headless: bool, verbose: bool, pretty: bool, csv_path: Optional[str], coords_only: bool) -> None:
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

        # Accept cookies if present
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

        # Wait for coordinates request
        try:
            await page.wait_for_response(lambda r: ("getCoordinates" in r.url or "coordinates" in r.url) and r.status == 200, timeout=15000)
        except Exception:
            await asyncio.sleep(3)

        # grace period
        await asyncio.sleep(1)
        await browser.close()

    # Deduplicate exact coordinates and sort
    results = dedupe_and_sort(results)

    # Differentiate duplicates by name
    results = add_name_suffixes(results)

    output_json_path = "agents/bto_data.json"

    # Save JSON
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    if verbose or pretty:
        print(f"✅ Saved {len(results)} entries to {output_json_path}")

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
            print(json.dumps(coords, indent=2 if pretty else None, ensure_ascii=False))
        return

    if csv_path:
        fieldnames = ["name", "lat", "lon", "flatTypes"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in results:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
            if verbose or pretty:
                print(f"Wrote {len(results)} rows to {csv_path}")
    else:
        print(json.dumps(results, indent=2 if pretty else None, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Fetch BTO coordinates and print clean output")
    ap.add_argument("--url", default="https://homes.hdb.gov.sg/home/finding-a-flat", help="Target URL")
    ap.add_argument("--headless", action="store_true", help="Run browser headless")
    ap.add_argument("--verbose", action="store_true", help="Print network logs and warnings")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    ap.add_argument("--csv", dest="csv_path", default="", help="Write output to CSV path instead of JSON")
    ap.add_argument("--coords-only", action="store_true", help="Output only coordinate pairs [[lat, lon], ...]")
    return ap.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(
        url=args.url,
        headless=args.headless,
        verbose=args.verbose,
        pretty=args.pretty,
        csv_path=(args.csv_path or None),
        coords_only=args.coords_only
    ))
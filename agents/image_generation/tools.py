from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import os
import ssl
import urllib.request
import urllib.parse
import hashlib
import certifi
from dotenv import load_dotenv
import requests
import json
from datetime import datetime, timezone


load_dotenv()

os.environ['SSL_CERT_FILE'] = certifi.where()

BRAVE = os.getenv("BRAVE_SEARCH_API")
if not BRAVE:
    raise RuntimeError("Missing BRAVE_SEARCH_API environment variable for Brave Search API token")

def find_image(query: str):
    resp = requests.get(
        "https://api.search.brave.com/res/v1/images/search",
        headers={
            "X-Subscription-Token": BRAVE,
        },
        params={
            "q": query,
            "count": 5,
            "country": "US",
            "search_lang": "en",
            "spellcheck": 1,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _download_to_folder(url: str, dest_dir: str = "downloads/images") -> Path:
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    # Generate a stable filename from the URL (keep extension if present)
    parsed = urllib.parse.urlparse(url)
    base = os.path.basename(parsed.path) or "image"
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    if "." in base:
        stem, ext = os.path.splitext(base)
        fname = f"{stem}-{h}{ext}"
    else:
        fname = f"{base}-{h}.jpg"
    out_path = Path(dest_dir) / fname
    # Stream download
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30, stream=True)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return out_path


def download_thumbnails_from_brave_result(result: Any, dest_dir: str = "downloads/images") -> Dict[str, Any]:
    """
    Accepts either a dict (parsed Brave response) or a JSON string. Downloads all `thumbnail.src`
    images into `dest_dir` (hardcoded by default to downloads/images). Returns a summary dict
    with saved paths and any errors.
    """
    # Parse if input is a JSON string
    if isinstance(result, str):
        try:
            payload = json.loads(result)
        except Exception as e:
            return {"ok": False, "error": f"invalid JSON string: {e}"}
    else:
        payload = result

    if not isinstance(payload, dict) or "results" not in payload:
        return {"ok": False, "error": "unexpected payload format: missing 'results'"}

    saved: List[str] = []
    errors: List[Dict[str, str]] = []

    for item in payload.get("results", []):
        if not isinstance(item, dict):
            continue
        thumb = item.get("thumbnail") or {}
        url = thumb.get("src")
        if not url:
            continue
        try:
            out = _download_to_folder(url, dest_dir=dest_dir)
            saved.append(str(out))
        except Exception as e:
            errors.append({"url": url, "error": str(e)})

    return {"ok": True, "saved": saved, "errors": errors}


def search_and_download_thumbnails(query: str, dest_dir: str = "downloads/images") -> Dict[str, Any]:
    """
    Perform a Brave image search for the given query, then download all thumbnail images
    found in the search results to the specified destination folder.

    Args:
        query (str): The search query string.
        dest_dir (str): The directory path where thumbnails will be saved. Defaults to "downloads/images".

    Returns:
        Dict[str, Any]: A dictionary containing the original query, the number of results found,
        a list of saved file paths, and any errors encountered during download.
    """
    data = find_image(query)
    res = download_thumbnails_from_brave_result(data, dest_dir=dest_dir)
    res["query"] = query
    res["found"] = len(data.get("results", [])) if isinstance(data, dict) else 0
    return res

def check_downloads(
    file_substr: str = "",
    dest_dir: str = "downloads/images",
    extensions: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    List downloaded files in `dest_dir` (default: downloads/images) and filter by `file_substr`
    (case-insensitive substring match on filename). Optionally filter by `extensions` (e.g. [".jpg", ".png"])
    and cap results with `limit`.

    Args:
        file_substr: Case-insensitive substring to match in filenames. Empty string returns all.
        dest_dir: Directory to scan. Defaults to the hardcoded downloads folder used by the downloader.
        extensions: Optional list of file extensions to include (e.g., [".jpg", ".png"]). Case-insensitive.
        limit: Optional maximum number of results to return.

    Returns:
        Dict[str, Any] with:
            - ok: bool
            - dir: scanned directory
            - query: the substring used
            - count: number of files returned
            - files: list of { "path", "name", "size_bytes", "modified_iso" } sorted by newest first
            - note: optional message when folder missing or empty
    """
    p = Path(dest_dir)
    if not p.exists():
        return {"ok": True, "dir": str(p), "query": file_substr, "count": 0, "files": [], "note": "directory does not exist"}

    files: List[Path] = [fp for fp in p.rglob("*") if fp.is_file()]

    # Filter by substring
    if file_substr:
        q = file_substr.lower()
        files = [fp for fp in files if q in fp.name.lower()]

    # Filter by extensions, if provided
    if extensions:
        exts = {e.lower() for e in extensions}
        files = [fp for fp in files if fp.suffix.lower() in exts]

    # Sort by modified time (newest first)
    files.sort(key=lambda fp: fp.stat().st_mtime, reverse=True)

    # Apply limit
    if limit is not None and limit >= 0:
        files = files[:limit]

    out = []
    for fp in files:
        st = fp.stat()
        mtime_iso = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
        out.append({
            "path": str(fp),
            "name": fp.name,
            "size_bytes": st.st_size,
            "modified_iso": mtime_iso,
        })

    return {
        "ok": True,
        "dir": str(p),
        "query": file_substr,
        "count": len(out),
        "files": out,
    }
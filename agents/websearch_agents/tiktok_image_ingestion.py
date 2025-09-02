#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Send a TikTok image (or local image) to Amazon Nova Pro on Bedrock via:
  A) inline base64 (InvokeModel)  OR
  B) S3 object reference (recommended)

For TikTok photo posts (URLs), this script:
  - uses yt-dlp -J to resolve real image slide URLs,
  - streams images into memory (no local files),
  - uploads each image to S3,
  - calls Nova with multiple image S3 references,
  - deletes the uploaded S3 objects after inference.

Usage:
  python tiktok_image_ingestion.py "<tiktok_or_local_path>" --via-s3
"""

import os
from pathlib import Path
import argparse
import base64
import hashlib
import json
import shlex
import subprocess
import sys
import tempfile
from typing import Optional, Tuple, List, Dict, Any

import boto3
from botocore.config import Config
from dotenv import load_dotenv
load_dotenv(".env")

# NEW: streaming downloads for remote images
import requests

# ---- Config helpers ---------------------------------------------------------

PROJECT_CONFIG_PATH = Path.cwd() / "nova_pro.json"
USER_CONFIG_PATH = Path.home() / ".config" / "nova_pro" / "config.json"

def _load_json(path: Path) -> dict:
    try:
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def load_merged_config() -> dict:
    """
    Merge config sources with increasing priority:
    user config < project config < env vars (simple) < CLI flags (handled later).
    """
    cfg = {}
    # 1) user config
    cfg.update(_load_json(USER_CONFIG_PATH))
    # 2) project config
    cfg.update(_load_json(PROJECT_CONFIG_PATH))
    # 3) env overrides (optional)
    env_overrides = {
        "bucket": os.environ.get("NOVA_BUCKET"),
        "bucketOwner": os.environ.get("NOVA_BUCKET_OWNER"),
        "profile": os.environ.get("AWS_PROFILE"),
        "region": os.environ.get("AWS_REGION"),
    }
    # only apply non-empty
    for k, v in env_overrides.items():
        if v:
            cfg[k] = v
    return cfg

def resolve_storage(args) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Return (bucket, prefix, bucket_owner, profile, region) using:
    CLI > env > project cfg > user cfg
    """
    cfg = load_merged_config()
    bucket = args.bucket or cfg.get("bucket")
    prefix = args.prefix if args.prefix != "nova_inputs/" else (cfg.get("prefix") or "nova_inputs/")
    bucket_owner = args.bucket_owner or cfg.get("bucketOwner")
    profile = args.profile or cfg.get("profile")
    region = args.region or cfg.get("region") or "us-east-1"
    return bucket, prefix, bucket_owner, profile, region

# ---- Constants --------------------------------------------------------------

NOVA_PRO_MODEL_ID = "amazon.nova-pro-v1:0"
DEFAULT_PROMPT = (
    "You are a domain expert. Look at the image(s) and summarize what they show in 5-7 bullet points. "
    "If relevant to housing (HDB/BTO/Toa Payoh), extract practical tips, dates, locations, numbers, "
    "and any disclaimers or caveats."
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# ---- Utils ------------------------------------------------------------------

def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")

def run(cmd: str):
    print(f"[cmd] {cmd}")
    subprocess.check_call(shlex.split(cmd))

def _glob_images(folder: Path) -> List[Path]:
    imgs: List[Path] = []
    for ext in IMAGE_EXTS:
        imgs.extend(folder.glob(f"*{ext}"))
    imgs.extend(folder.glob("*.jpg"))
    imgs.extend(folder.glob("*.jpeg"))
    imgs.extend(folder.glob("*.png"))
    imgs.extend(folder.glob("*.webp"))
    # unique & existing
    imgs = [p for p in {p.resolve() for p in imgs} if p.exists()]
    return imgs

def pick_largest(paths: List[Path]) -> Optional[Path]:
    if not paths:
        return None
    return max(paths, key=lambda p: p.stat().st_size)

def ensure_jpeg_or_png(path: Path) -> Path:
    """
    Ensure the image is jpeg or png. If webp, try to convert to png.
    If Pillow not installed, keep original.
    """
    ext = path.suffix.lower()
    if ext in {".jpg", ".jpeg", ".png"}:
        return path
    try:
        from PIL import Image  # optional
        out_ext = ".png"
        out_path = path.with_suffix(out_ext)
        with Image.open(path) as im:
            im.save(out_path, format="PNG")
        return out_path
    except Exception:
        print(f"[warn] Could not convert {path.name}; proceeding with {ext}.")
        return path

def image_format_for(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        return "jpeg"
    if ext == ".png":
        return "png"
    if ext == ".webp":
        return "webp"  # fallback
    return "jpeg"

def file_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8")

# ---- TikTok JSON helpers (no local files needed) ----------------------------

def yt_dlp_json(url: str) -> Dict[str, Any]:
    """
    Ask yt-dlp for extractor JSON (single JSON regardless of playlist).
    """
    out = subprocess.check_output(
        shlex.split(f'yt-dlp -J --dump-single-json --no-warnings --no-playlist "{url}"')
    )
    return json.loads(out)

def _best_from_thumbnails(thumbnails: Any) -> Optional[str]:
    if not isinstance(thumbnails, list):
        return None
    def k(t):
        pref = (t or {}).get("preference") or 0
        w = (t or {}).get("width") or 0
        h = (t or {}).get("height") or 0
        return (pref, (w or 0) * (h or 0), w, h)
    arr = sorted(thumbnails, key=k, reverse=True)
    return (arr[0] or {}).get("url") if arr else None

def collect_tiktok_image_urls(meta: Dict[str, Any]) -> List[str]:
    """
    Consolidate image URLs from TikTok photo posts.
    Looks at: images, slides[].url, thumbnails, thumbnail (fallbacks).
    """
    items = meta.get("entries") if isinstance(meta.get("entries"), list) else [meta]
    urls: List[str] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        # direct images list
        imgs = it.get("images") or []
        for u in imgs:
            if isinstance(u, str):
                urls.append(u)
        # slides array with url/image/image_url
        slides = it.get("slides") or []
        for s in slides:
            if isinstance(s, dict):
                u = s.get("url") or s.get("image") or s.get("image_url")
                if u:
                    urls.append(u)
        # best thumbnail fallback
        if it.get("thumbnails"):
            u = _best_from_thumbnails(it["thumbnails"])
            if u:
                urls.append(u)
        # single thumbnail string
        if isinstance(it.get("thumbnail"), str):
            urls.append(it["thumbnail"])
    # de-dup preserve order
    seen = set()
    uniq = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq

def fetch_image_bytes(url: str) -> Tuple[bytes, str]:
    """
    Return (bytes, format) format in {'jpeg','png','webp'} (best-effort).
    """
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()
    ctype = (r.headers.get("Content-Type") or "").lower()
    if "png" in ctype:
        fmt = "png"
    elif "webp" in ctype:
        fmt = "webp"
    elif "jpeg" in ctype or "jpg" in ctype:
        fmt = "jpeg"
    else:
        low = url.lower()
        if low.endswith(".png"):
            fmt = "png"
        elif low.endswith(".webp"):
            fmt = "webp"
        else:
            fmt = "jpeg"
    return r.content, fmt

def convert_webp_to_png_bytes(b: bytes) -> Tuple[bytes, str]:
    """
    Try to convert WEBP bytes to PNG bytes for maximum Nova/S3 compatibility.
    If Pillow isn't present, keep as WEBP.
    """
    try:
        from PIL import Image
        from io import BytesIO
        im = Image.open(BytesIO(b))
        im = im.convert("RGBA")  # preserve alpha
        buf = BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue(), "png"
    except Exception:
        return b, "webp"

# ---- AWS helpers ------------------------------------------------------------

def upload_to_s3(region: str, profile: Optional[str], file_path: Path, bucket: str, key: str) -> str:
    session = boto3.Session(profile_name=profile, region_name=region)
    s3 = session.client("s3")
    suffix = file_path.suffix.lower()
    ct = "image/jpeg" if suffix in {".jpg", ".jpeg"} else ("image/png" if suffix == ".png" else "application/octet-stream")
    extra = {"ContentType": ct}
    print(f"[info] Uploading to s3://{bucket}/{key} ...")
    s3.upload_file(str(file_path), bucket, key, ExtraArgs=extra)
    return f"s3://{bucket}/{key}"

# NEW: upload raw BYTES to S3 (no temp files)
def upload_bytes_to_s3(region: str, profile: Optional[str], b: bytes, fmt: str, bucket: str, key: str) -> str:
    session = boto3.Session(profile_name=profile, region_name=region)
    s3 = session.client("s3")
    ct = "image/jpeg" if fmt == "jpeg" else ("image/png" if fmt == "png" else "image/webp")
    print(f"[info] Uploading (bytes) to s3://{bucket}/{key} ... ContentType={ct}")
    s3.put_object(Bucket=bucket, Key=key, Body=b, ContentType=ct)
    return f"s3://{bucket}/{key}"

def parse_s3_uri(uri: str) -> Tuple[str, str]:
    """Return (bucket, key) from an s3://bucket/key URI."""
    if not uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {uri}")
    without = uri[len("s3://"):]
    bucket, _, key = without.partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid S3 URI (missing bucket or key): {uri}")
    return bucket, key

def delete_s3_object(region: str, profile: Optional[str], s3_uri: str) -> None:
    """Delete the given S3 object. No-op if it 404s."""
    bucket, key = parse_s3_uri(s3_uri)
    session = boto3.Session(profile_name=profile, region_name=region)
    s3 = session.client("s3")
    try:
        s3.delete_object(Bucket=bucket, Key=key)
        print(f"[info] Deleted S3 object: {s3_uri}")
    except Exception as e:
        print(f"[warn] Failed to delete {s3_uri}: {e}")

# ---- Bedrock: Nova Pro ------------------------------------------------------

def invoke_nova_pro_image_inline(region: str, profile: Optional[str], img_b64: str, img_format: str, prompt: str) -> str:
    session = boto3.Session(profile_name=profile, region_name="us-east-1")
    client = session.client(
        "bedrock-runtime",
        config=Config(connect_timeout=3600, read_timeout=3600, retries={'max_attempts': 1})
    )
    body = {
        "schemaVersion": "messages-v1",
        "system": [{"text": "You are a helpful image analyst."}],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "image": {
                            "format": img_format,           # "jpeg" | "png" | "webp"
                            "source": { "bytes": img_b64 }  # Base64
                        }
                    },
                    { "text": prompt }
                ]
            }
        ],
        "inferenceConfig": { "maxTokens": 800, "temperature": 0.2, "topP": 0.9 }
    }
    resp = client.invoke_model(modelId=NOVA_PRO_MODEL_ID, body=json.dumps(body))
    result = json.loads(resp["body"].read())
    try:
        return result["output"]["message"]["content"][0]["text"]
    except Exception:
        return json.dumps(result, indent=2)

# NEW: multi-image S3 invocation
def invoke_nova_pro_images_s3(region: str, profile: Optional[str], s3_items: List[Tuple[str, str]], prompt: str) -> str:
    """
    s3_items: list of (s3_uri, img_format)
    """
    session = boto3.Session(profile_name=profile, region_name="us-east-1")
    client = session.client(
        "bedrock-runtime",
        config=Config(connect_timeout=3600, read_timeout=3600, retries={'max_attempts': 1})
    )
    content = []
    for (s3_uri, img_format) in s3_items:
        s3_loc = {"uri": s3_uri}
        content.append({
            "image": {
                "format": img_format,
                "source": {"s3Location": s3_loc}
            }
        })
    content.append({"text": prompt})
    body = {
        "schemaVersion": "messages-v1",
        "system": [{"text": "You are a helpful image analyst."}],
        "messages": [{"role": "user", "content": content}],
        "inferenceConfig": { "maxTokens": 800, "temperature": 0.2, "topP": 0.9 }
    }
    resp = client.invoke_model(modelId=NOVA_PRO_MODEL_ID, body=json.dumps(body))
    result = json.loads(resp["body"].read())
    try:
        return result["output"]["message"]["content"][0]["text"]
    except Exception:
        return json.dumps(result, indent=2)

def invoke_nova_pro_image_s3(region: str, profile: Optional[str], s3_uri: str, img_format: str, prompt: str) -> str:
    # kept for single-image parity
    return invoke_nova_pro_images_s3(region, profile, [(s3_uri, img_format)], prompt)

# ---- Main -------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Analyze an image with Amazon Nova Pro via inline or S3.")
    ap.add_argument("input", help="TikTok URL (https://...) OR local image file path (.jpg/.jpeg/.png/.webp)")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT, help="Instruction for Nova Pro")
    ap.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"),
                    help="AWS region for Bedrock Runtime (default: env AWS_REGION or us-east-1)")
    ap.add_argument("--profile", default=os.environ.get("AWS_PROFILE"),
                    help="AWS profile name to use (defaults to AWS_PROFILE env)")
    ap.add_argument("--via-s3", action="store_true", help="Upload to S3 and reference via s3Location.uri")
    ap.add_argument("--bucket", help="Target S3 bucket (required if --via-s3)")
    ap.add_argument("--prefix", default="nova_inputs/", help="Key prefix within bucket (default: nova_inputs/)")
    ap.add_argument("--bucket-owner", default=None, help="Bucket owner's AWS Account ID if cross-account (not used but kept for parity)")
    # NEW:
    ap.add_argument("--max-images", type=int, default=5, help="Max number of images to send for TikTok photo posts (default: 5)")
    args = ap.parse_args()

    # Resolve storage now (needed for S3 path)
    bucket, prefix, bucket_owner, profile, region = resolve_storage(args)

    # ---- URL path: stream images -> S3 -> Nova -> delete ----
    if is_url(args.input):
        if not args.via_s3:
            print("[warn] URL input strongly recommends --via-s3. Proceeding anyway (forcing S3).")
        if not bucket:
            print("[error] No bucket found. Set --bucket OR NOVA_BUCKET env OR add to nova_pro.json or ~/.config/nova_pro/config.json")
            sys.exit(1)

        print("[info] Resolving TikTok images via yt-dlp JSON...")
        meta = yt_dlp_json(args.input)
        urls = collect_tiktok_image_urls(meta)
        if not urls:
            print("[error] No image URLs found from TikTok. Is this a video post?")
            sys.exit(1)

        # limit how many images we send
        urls = urls[: max(1, args.max_images)]
        print(f"[info] Found {len(urls)} image URL(s). Streaming, uploading to S3, and invoking Nova...")

        uploaded_uris: List[str] = []
        s3_items: List[Tuple[str, str]] = []  # (s3_uri, img_format)
        try:
            for i, u in enumerate(urls, 1):
                b, fmt = fetch_image_bytes(u)
                # prefer converting webp -> png for compatibility if Pillow is available
                if fmt == "webp":
                    b2, fmt2 = convert_webp_to_png_bytes(b)
                    b, fmt = b2, fmt2
                sha8 = hashlib.sha1(b).hexdigest()[:8]
                # create a stable-ish key name
                name = f"tiktok_{sha8}_{i}.{ 'jpg' if fmt=='jpeg' else fmt }"
                key = f"{(prefix or 'nova_inputs/').rstrip('/')}/{name}"
                s3_uri = upload_bytes_to_s3(region, profile, b, fmt, bucket, key)
                uploaded_uris.append(s3_uri)
                s3_items.append((s3_uri, fmt))

            out_text = invoke_nova_pro_images_s3(region, profile, s3_items, args.prompt)

        finally:
            # cleanup: delete every uploaded S3 object
            for uri in uploaded_uris:
                try:
                    delete_s3_object(region=region, profile=profile, s3_uri=uri)
                except Exception:
                    pass

        print("\n===== Nova Pro Response =====\n")
        print(out_text)
        print("\n=============================\n")
        return

    # ---- Local file path (old behavior preserved) ----
    img_path = Path(args.input).expanduser().resolve()
    if not img_path.exists():
        print(f"[error] File not found: {img_path}")
        sys.exit(1)

    # Ensure a Nova-friendly format (jpeg/png preferred)
    img_path = ensure_jpeg_or_png(img_path)
    img_format = image_format_for(img_path)

    if args.via_s3:
        if not bucket:
            print("[error] No bucket found. Set --bucket OR NOVA_BUCKET env OR add to nova_pro.json or ~/.config/nova_pro/config.json")
            sys.exit(1)

        # Build unique S3 key with content hash
        sha8 = hashlib.sha1(img_path.read_bytes()).hexdigest()[:8]
        key = f"{(prefix or 'nova_inputs/').rstrip('/')}/{sha8}_{img_path.name}"
        s3_uri = upload_to_s3(region, profile, img_path, bucket, key)
        print(f"[info] Calling Nova Pro with S3 image: {s3_uri}")

        try:
            out_text = invoke_nova_pro_image_s3(region, profile, s3_uri, img_format, args.prompt)
        finally:
            delete_s3_object(region=region, profile=profile, s3_uri=s3_uri)
    else:
        # Inline/base64 path (kept for parity)
        print(f"[info] Using image: {img_path} ({img_path.stat().st_size / (1024*1024):.2f} MB)")
        b64 = file_to_base64(img_path)
        print("[info] Calling Nova Pro (inline/base64)...")
        out_text = invoke_nova_pro_image_inline(region, profile, b64, img_format, args.prompt)

    print("\n===== Nova Pro Response =====\n")
    print(out_text)
    print("\n=============================\n")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Send a local (downloaded) video to Amazon Nova Pro on Bedrock via:
  A) inline base64 (InvokeModel)  OR
  B) S3 object reference (recommended for >25MB)

Usage:
  python agents/websearch_tiktok/tiktok_video_ingestion.py "<tiktok_or_local_path>" --via-s3 
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
from typing import Optional

import boto3
from botocore.config import Config
from dotenv import load_dotenv
load_dotenv(".env")

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

def resolve_storage(args) -> tuple[str|None, str|None, str|None, str|None, str|None]:
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


NOVA_PRO_MODEL_ID = "amazon.nova-pro-v1:0"
DEFAULT_PROMPT = (
    "You are a domain expert. Watch the video and summarize in 5-7 bullet points. "
    "If relevant to housing (HDB/BTO/Toa Payoh), extract practical tips, dates, locations, and any numbers. "
    "If there are disclaimers or caveats, include them."
)

def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")

def run(cmd: str):
    print(f"[cmd] {cmd}")
    subprocess.check_call(shlex.split(cmd))

def download_tiktok(url: str) -> Path:
    """Download a TikTok MP4 using yt-dlp and return the file path."""
    out_dir = Path(tempfile.mkdtemp(prefix="nova_tt_"))
    out_tmpl = str(out_dir / "%(id)s.%(ext)s")
    cmd = (
        'yt-dlp '
        '-S vcodec:h264,acodec:aac '
        '-f "bv*[vcodec*=avc1]+ba[acodec*=mp4a]/b[ext=mp4]" '
        '--no-playlist -o "{out}" "{url}"'
    ).format(out=out_tmpl, url=url)
    run(cmd)
    vids = list(out_dir.glob("*.mp4"))
    if not vids:
        raise RuntimeError("No MP4 file found after download.")
    return vids[0]

def probe_codecs(path: Path) -> tuple[str|None, str|None]:
    """Return (vcodec, acodec) using ffprobe. None if unknown."""
    try:
        import json, subprocess, shlex
        cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of json "{path}"'
        vinfo = json.loads(subprocess.check_output(shlex.split(cmd)))
        vcodec = (vinfo.get("streams") or [{}])[0].get("codec_name")

        cmd = f'ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of json "{path}"'
        ainfo = json.loads(subprocess.check_output(shlex.split(cmd)))
        acodec = (ainfo.get("streams") or [{}])[0].get("codec_name")
        return vcodec, acodec
    except Exception:
        return None, None

def ensure_h264_aac(input_path: Path) -> Path:
    """
    If the video/audio codecs aren't (h264,aac), transcode to a Nova-friendly MP4.
    """
    vcodec, acodec = probe_codecs(input_path)
    if vcodec == "h264" and (acodec in (None, "aac")):
        return input_path  # good to go

    print(f"[info] Transcoding to H.264/AAC for Nova (was v={vcodec}, a={acodec})...")
    out = input_path.with_name(input_path.stem + "_h264.mp4")
    run(
        'ffmpeg -y -i "{inp}" '
        '-c:v libx264 -pix_fmt yuv420p -profile:v main -level 4.0 -preset veryfast -crf 23 '
        '-c:a aac -b:a 128k -movflags +faststart "{out}"'
        .format(inp=str(input_path), out=str(out))
    )
    return out

def maybe_trim_video(input_path: Path, max_mb: int = 24) -> Path:
    """
    If the file is larger than ~24 MB, trim to first 45s to keep payloads small for inline uploads.
    (Use --via-s3 to avoid inline size limits.)
    """
    size_mb = input_path.stat().st_size / (1024 * 1024)
    if size_mb <= max_mb:
        return input_path

    print(f"[info] Input is {size_mb:.1f} MB; trimming to first 45s to reduce size...")
    trimmed = input_path.with_name(input_path.stem + "_trimmed.mp4")
    try:
        run(f'ffmpeg -y -i "{input_path}" -t 45 -c copy "{trimmed}"')
        new_mb = trimmed.stat().st_size / (1024 * 1024)
        print(f"[info] Trimmed size: {new_mb:.1f} MB")
        return trimmed
    except Exception as e:
        print(f"[warn] Trimming failed ({e}); sending original (may be too large).")
        return input_path

def file_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8")

def _invoke_bedrock_messages_v1(region: str, profile: str, content_blocks: list, prompt: str) -> str:
    session = boto3.Session(profile_name=profile, region_name="us-east-1")
    client = session.client(
        "bedrock-runtime",
        config=Config(connect_timeout=3600, read_timeout=3600, retries={'max_attempts': 1})
    )
    body = {
        "schemaVersion": "messages-v1",
        "system": [{"text": "You are a helpful media analyst."}],
        "messages": [
            {
                "role": "user",
                "content": content_blocks + [{ "text": prompt }]
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

def upload_to_s3(region: str, profile: str, file_path: Path, bucket: str, key: str):
    session = boto3.Session(profile_name=profile, region_name=region)
    s3 = session.client("s3")
    extra = {"ContentType": "video/mp4"} if file_path.suffix.lower() == ".mp4" else {}
    print(f"[info] Uploading to s3://{bucket}/{key} ...")
    s3.upload_file(str(file_path), bucket, key, ExtraArgs=extra)
    return f"s3://{bucket}/{key}"

def invoke_nova_pro_video_inline(region: str, profile: str, video_b64: str, prompt: str) -> str:
    session = boto3.Session(profile_name=profile, region_name="us-east-1")
    client = session.client(
        "bedrock-runtime",
        config=Config(connect_timeout=3600, read_timeout=3600, retries={'max_attempts': 1})  # per AWS guidance
    )

    body = {
        "schemaVersion": "messages-v1",
        "system": [{"text": "You are a helpful video analyst."}],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "video": {
                            "format": "mp4",
                            "source": { "bytes": video_b64 }  # Base64 for Invoke API
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

def invoke_nova_pro_video_s3(region: str, profile: str, s3_uri: str, prompt: str) -> str:
    session = boto3.Session(profile_name=profile, region_name="us-east-1")
    client = session.client(
        "bedrock-runtime",
        config=Config(connect_timeout=3600, read_timeout=3600, retries={'max_attempts': 1})
    )

    # Build s3Location per Nova schema (uri + optional bucketOwner)
    s3_loc = {"uri": s3_uri}


    body = {
        "schemaVersion": "messages-v1",
        "system": [{"text": "You are a helpful video analyst."}],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "video": {
                            "format": "mp4",
                            "source": {
                                "s3Location": s3_loc
                            }
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



def parse_s3_uri(uri: str) -> tuple[str, str]:
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
        # we don't want deletion hiccups to crash the script
        print(f"[warn] Failed to delete {s3_uri}: {e}")

def main():
    ap = argparse.ArgumentParser(description="Analyze a video with Amazon Nova Pro via inline or S3.")
    ap.add_argument("input", help="TikTok URL (https://...) OR local video file path (.mp4/.mov/.mkv)")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT, help="Instruction for Nova Pro")
    ap.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"),
                    help="AWS region for Bedrock Runtime (default: env AWS_REGION or us-east-1)")
    ap.add_argument("--profile", default=os.environ.get("AWS_PROFILE"),
                    help="AWS profile name to use (defaults to AWS_PROFILE env)")
    ap.add_argument("--no-trim", action="store_true", help="Do not trim even if file is large (inline path only)")
    ap.add_argument("--via-s3", action="store_true", help="Upload to S3 and reference via s3Location.uri")
    ap.add_argument("--bucket", help="Target S3 bucket (required if --via-s3)")
    ap.add_argument("--prefix", default="nova_inputs/", help="Key prefix within bucket (default: nova_inputs/)")
    ap.add_argument("--bucket-owner", default=None, help="Bucket owner's AWS Account ID if cross-account")
    args = ap.parse_args()

    if is_url(args.input):
        print("[info] Downloading TikTok video with yt-dlp...")
        video_path = download_tiktok(args.input)
    else:
        video_path = Path(args.input).expanduser().resolve()
        if not video_path.exists():
            print(f"[error] File not found: {video_path}")
            sys.exit(1)

    if args.via_s3:
        # Resolve from CLI/env/config
        bucket, prefix, bucket_owner, profile, region = resolve_storage(args)
        if not bucket:
            print("[error] No bucket found. Set --bucket OR NOVA_BUCKET env OR add to nova_pro.json or ~/.config/nova_pro/config.json")
            sys.exit(1)
        video_path = ensure_h264_aac(video_path)
        # S3 path (no inline size limits)
        sha8 = hashlib.sha1(video_path.read_bytes()).hexdigest()[:8]
        key = f"{(prefix or 'nova_inputs/').rstrip('/')}/{sha8}_{video_path.name}"
        s3_uri = upload_to_s3(region, profile, video_path, bucket, key)
        print(f"[info] Calling Nova Pro with S3 video: {s3_uri}")

        try:
            out_text = invoke_nova_pro_video_s3(region, profile, s3_uri, args.prompt)
        finally:    
            delete_s3_object(region=region, profile=profile, s3_uri=s3_uri)
    else:
        # Inline path (will trim if >~24MB)
        bucket, prefix, bucket_owner, profile, region = resolve_storage(args)  # still resolve defaults
        if not args.no_trim:
            video_path = maybe_trim_video(video_path)
        video_path = ensure_h264_aac(video_path)
        print(f"[info] Using video: {video_path} ({video_path.stat().st_size / (1024*1024):.1f} MB)")
        b64 = file_to_base64(video_path)
        print("[info] Calling Nova Pro (inline/base64)...")
        out_text = invoke_nova_pro_video_inline(region, profile, b64, args.prompt)
    print("\n===== Nova Pro Response =====\n")
    print(out_text)
    print("\n=============================\n")

if __name__ == "__main__":
    main()
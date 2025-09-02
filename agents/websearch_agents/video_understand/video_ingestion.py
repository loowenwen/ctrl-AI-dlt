#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reusable library for:
- Downloading/normalizing videos (yt-dlp, ffmpeg)
- (Optional) Trimming large videos
- Extracting audio for ASR
- Transcribing with Groq Whisper
- Invoking Amazon Nova Pro (Bedrock) with TEXT or VIDEO (inline/S3)

Env (override defaults):
  AWS_REGION                (default: us-east-1)
  NOVA_BUCKET               (optional; for --via-s3)
  NOVA_BUCKET_OWNER         (optional; cross-account)
  GROQ_API_KEY              (required for transcription path)
"""

from __future__ import annotations
import base64
import hashlib
import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

import boto3
from botocore.config import Config

# ---- Optional Groq (only needed for transcription path) ----
try:
    from groq import Groq    # pip install groq
except Exception:
    Groq = None  # handled at runtime

# ---------------- Config helpers ----------------

NOVA_PRO_MODEL_ID = "amazon.nova-pro-v1:0"
DEFAULT_PROMPT = (
    "Determine the sentiment of the following transcription in terms of the pros and cons "
    "and whether it's positive or negative on a scale of 1-10."
)

def _run(cmd: str):
    print(f"[cmd] {cmd}")
    subprocess.check_call(shlex.split(cmd))

def _boto3_client(service: str, region: Optional[str] = None, profile: Optional[str] = None):
    region = region or os.environ.get("AWS_REGION", "us-east-1")
    if profile:
        session = boto3.Session(profile_name=profile, region_name=region)
    else:
        session = boto3.Session(region_name=region)
    return session.client(service, config=Config(connect_timeout=3600, read_timeout=3600, retries={'max_attempts': 1}))

# ---------------- URL/file helpers ----------------

def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")

def download_web_video(url: str) -> Path:
    """
    Download web video (YouTube/TikTok/…) as MP4 using yt-dlp.
    Return the downloaded file Path.
    """
    out_dir = Path(tempfile.mkdtemp(prefix="nova_dl_"))
    out_tmpl = str(out_dir / "%(id)s.%(ext)s")
    cmd = (
        'yt-dlp -N 8 --merge-output-format mp4 '
        '-S vcodec:h264,acodec:aac '
        '-f "bv*[vcodec*=avc1][ext=mp4]+ba[acodec*=mp4a]/'
              'bv*[vcodec*=avc1]+ba[acodec*=mp4a]/'
              'b[ext=mp4]/b" '
        '--no-playlist -o "{out}" "{url}"'
    ).format(out=out_tmpl, url=url)
    _run(cmd)
    vids = sorted(out_dir.glob("*.mp4"))
    if vids:
        return vids[0]
    others = sorted(out_dir.glob("*.*"))
    if not others:
        raise RuntimeError("No file found after yt-dlp download.")
    return others[0]

def _probe_codecs(path: Path) -> Tuple[Optional[str], Optional[str]]:
    try:
        vinfo = json.loads(subprocess.check_output(shlex.split(
            f'ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of json "{path}"'
        )))
        vcodec = (vinfo.get("streams") or [{}])[0].get("codec_name")

        ainfo = json.loads(subprocess.check_output(shlex.split(
            f'ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of json "{path}"'
        )))
        acodec = (ainfo.get("streams") or [{}])[0].get("codec_name")
        return vcodec, acodec
    except Exception:
        return None, None

def ensure_h264_aac(input_path: Path) -> Path:
    """
    Ensure (h264, aac). If not, transcode to a Nova-friendly MP4.
    """
    vcodec, acodec = _probe_codecs(input_path)
    if vcodec == "h264" and (acodec in (None, "aac")):
        return input_path
    print(f"[info] Transcoding to H.264/AAC (was v={vcodec}, a={acodec})...")
    out = input_path.with_name(input_path.stem + "_h264.mp4")
    _run(
        f'ffmpeg -y -i "{input_path}" '
        f'-c:v libx264 -pix_fmt yuv420p -profile:v main -level 4.0 -preset veryfast -crf 23 '
        f'-c:a aac -b:a 128k -movflags +faststart "{out}"'
    )
    return out

def maybe_trim_video(input_path: Path, max_mb: int = 24, max_seconds: int = 45) -> Path:
    """
    If file > max_mb, trim to first max_seconds (for inline/base64 path).
    """
    size_mb = input_path.stat().st_size / (1024 * 1024)
    if size_mb <= max_mb:
        return input_path
    print(f"[info] Input {size_mb:.1f} MB > {max_mb} MB; trimming to {max_seconds}s...")
    trimmed = input_path.with_name(input_path.stem + "_trimmed.mp4")
    try:
        _run(f'ffmpeg -y -i "{input_path}" -t {max_seconds} -c copy "{trimmed}"')
        return trimmed
    except Exception as e:
        print(f"[warn] Trimming failed: {e}; using original.")
        return input_path

def file_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")

# ---------------- Audio/ASR ----------------

def extract_audio_m4a(video_path: Path) -> Path:
    out = video_path.with_suffix(".m4a")
    _run(f'ffmpeg -y -i "{video_path}" -vn -ac 1 -ar 16000 -c:a aac -b:a 160k "{out}"')
    return out

def transcribe_with_groq(audio_path: Path, api_key: Optional[str] = None) -> str:
    """
    Transcribe with Groq Whisper large-v3-turbo.
    Requires GROQ_API_KEY env or api_key.
    """
    api_key = api_key or os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set.")
    if Groq is None:
        raise RuntimeError("groq package not installed.")
    client = Groq(api_key=api_key)
    with open(audio_path, "rb") as f:
        resp = client.audio.transcriptions.create(
            file=(str(audio_path), f.read()),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
        )
    text = getattr(resp, "text", None)
    return text or json.dumps(resp, indent=2, default=str)

# ---------------- S3 helpers ----------------

def upload_to_s3(file_path: Path, bucket: str, key: str, *, region: Optional[str] = None,
                 profile: Optional[str] = None) -> str:
    s3 = _boto3_client("s3", region, profile)
    extra = {"ContentType": "video/mp4"} if file_path.suffix.lower() == ".mp4" else {}
    print(f"[info] Uploading to s3://{bucket}/{key} ...")
    s3.upload_file(str(file_path), bucket, key, ExtraArgs=extra)
    return f"s3://{bucket}/{key}"

def parse_s3_uri(uri: str) -> Tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {uri}")
    without = uri[len("s3://"):]
    bucket, _, key = without.partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid S3 URI (missing bucket or key): {uri}")
    return bucket, key

def delete_s3_object(s3_uri: str, *, region: Optional[str] = None, profile: Optional[str] = None) -> None:
    bucket, key = parse_s3_uri(s3_uri)
    s3 = _boto3_client("s3", region, profile)
    try:
        s3.delete_object(Bucket=bucket, Key=key)
        print(f"[info] Deleted S3 object: {s3_uri}")
    except Exception as e:
        print(f"[warn] Failed to delete {s3_uri}: {e}")

# ---------------- Bedrock (Nova Pro) ----------------

def _invoke_bedrock_messages(body: Dict[str, Any], *, region: Optional[str] = None,
                             profile: Optional[str] = None) -> Dict[str, Any]:
    client = _boto3_client("bedrock-runtime", region, profile)
    resp = client.invoke_model(modelId=NOVA_PRO_MODEL_ID, body=json.dumps(body))
    return json.loads(resp["body"].read())

def nova_with_text(transcript_text: str, prompt: str = DEFAULT_PROMPT, *,
                   region: Optional[str] = None, profile: Optional[str] = None,
                   chunk_chars: int = 6000, max_tokens: int = 1000) -> str:
    # Simple chunking if transcript is long
    chunks = [transcript_text[i:i+chunk_chars] for i in range(0, len(transcript_text), chunk_chars)] or [""]
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    for i, ch in enumerate(chunks, 1):
        messages.append({"role": "user", "content": [{"text": f"(Transcript part {i}/{len(chunks)})\n{ch}"}]})
    body = {
        "schemaVersion": "messages-v1",
        "system": [{"text": "You are a helpful analyst."}],
        "messages": messages,
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.0, "topP": 0.1}
    }
    result = _invoke_bedrock_messages(body, region=region, profile=profile)
    try:
        return result["output"]["message"]["content"][0]["text"]
    except Exception:
        return json.dumps(result, indent=2)

def nova_with_video_inline(video_b64: str, prompt: str, *,
                           region: Optional[str] = None, profile: Optional[str] = None,
                           max_tokens: int = 800, temperature: float = 0.2, top_p: float = 0.9) -> str:
    body = {
        "schemaVersion": "messages-v1",
        "system": [{"text": "You are a helpful video analyst."}],
        "messages": [{
            "role": "user",
            "content": [
                {"video": {"format": "mp4", "source": {"bytes": video_b64}}},
                {"text": prompt}
            ]
        }],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature, "topP": top_p}
    }
    result = _invoke_bedrock_messages(body, region=region, profile=profile)
    try:
        return result["output"]["message"]["content"][0]["text"]
    except Exception:
        return json.dumps(result, indent=2)

def nova_with_video_s3(s3_uri: str, prompt: str, *,
                       region: Optional[str] = None, profile: Optional[str] = None,
                       max_tokens: int = 800, temperature: float = 0.2, top_p: float = 0.9) -> str:
    body = {
        "schemaVersion": "messages-v1",
        "system": [{"text": "You are a helpful video analyst."}],
        "messages": [{
            "role": "user",
            "content": [
                {"video": {"format": "mp4", "source": {"s3Location": {"uri": s3_uri}}}},
                {"text": prompt}
            ]
        }],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature, "topP": top_p}
    }
    result = _invoke_bedrock_messages(body, region=region, profile=profile)
    try:
        return result["output"]["message"]["content"][0]["text"]
    except Exception:
        return json.dumps(result, indent=2)
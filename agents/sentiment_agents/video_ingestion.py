#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Lambda entry + local CLI for Nova Pro video ingestion.

EVENT SHAPES:

A) Default path (ASR + TEXT → Nova)
{
  "mode": "transcribe_to_text",        // default if omitted
  "input": "https://youtu.be/...." | "/tmp/local.mp4",
  "prompt": "custom instruction",      // optional
  "region": "us-east-1",               // optional
  "profile": null,                     // optional (ignored on Lambda)
  "return_transcript": false           // optional: include transcript in response
}

B) Raw video (INLINE)
{
  "mode": "raw_video_inline",
  "input": "https://... | /path/file.mp4",
  "prompt": "analyze this video",
  "no_trim": false                     // if true, skip trimming
}

C) Raw video (S3 reference)
{
  "mode": "raw_video_s3",
  "input": "https://... | /path/file.mp4",
  "prompt": "analyze this video",
  "bucket": "my-bucket",               // optional; else env NOVA_BUCKET
  "prefix": "nova_inputs/",            // optional
  "delete_after": true                 // delete S3 object after invoke
}

RETURNS:
{ "ok": true, "data": { "nova": "...", "transcript": "..."? } } or { "ok": false, "error": "..." }

Local CLI usage:
  python video_ingestion_lambda.py --input "<urlOrPath>" --mode transcribe_to_text
  python video_ingestion_lambda.py --input "<urlOrPath>" --mode raw_video_inline
  python video_ingestion_lambda.py --input "<urlOrPath>" --mode raw_video_s3 --bucket my-bucket
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
#Comment this out before zip to lambda
from dotenv import load_dotenv
load_dotenv()
#comment above out before zip to lambda
from video_ingestion_functions import (
    is_url, download_web_video, ensure_h264_aac, maybe_trim_video, file_to_base64,
    extract_audio_m4a, transcribe_with_groq, upload_to_s3, delete_s3_object,
    nova_with_text, nova_with_video_inline, nova_with_video_s3, DEFAULT_PROMPT
)

# ---------------- Lambda handler ----------------

def lambda_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    try:
        if not isinstance(event, dict):
            raise ValueError("Event must be a JSON object")

        mode = (event.get("mode") or "transcribe_to_text").lower()
        inp = event.get("input")
        if not inp or not isinstance(inp, str):
            raise ValueError("Missing 'input' (URL or local file path)")

        prompt = event.get("prompt") or DEFAULT_PROMPT
        region = event.get("region") or os.environ.get("AWS_REGION") or "us-east-1"
        profile = event.get("profile")  # typically None on Lambda

        # 1) Get a local video path (download if URL)
        if is_url(inp):
            print(f"[info] Downloading web video: {inp}")
            video_path = download_web_video(inp)
        else:
            video_path = Path(inp).expanduser().resolve()
            if not video_path.exists():
                raise FileNotFoundError(f"File not found: {video_path}")

        if mode == "raw_video_inline":
            no_trim = bool(event.get("no_trim", False))
            if not no_trim:
                video_path = maybe_trim_video(video_path)
            video_path = ensure_h264_aac(video_path)
            b64 = file_to_base64(video_path)
            out_text = nova_with_video_inline(b64, prompt, region=region, profile=profile)
            return {"ok": True, "data": {"nova": out_text}}

        if mode == "raw_video_s3":
            bucket = event.get("bucket") or os.environ.get("NOVA_BUCKET")
            if not bucket:
                raise ValueError("In raw_video_s3 mode, provide 'bucket' or set NOVA_BUCKET env.")
            prefix = event.get("prefix") or "nova_inputs/"
            video_path = ensure_h264_aac(video_path)
            sha8 = hashlib.sha1(video_path.read_bytes()).hexdigest()[:8]
            key = f"{prefix.rstrip('/')}/{sha8}_{video_path.name}"
            s3_uri = upload_to_s3(video_path, bucket, key, region=region, profile=profile)
            try:
                out_text = nova_with_video_s3(s3_uri, prompt, region=region, profile=profile)
            finally:
                if bool(event.get("delete_after", True)):
                    delete_s3_object(s3_uri, region=region, profile=profile)
            return {"ok": True, "data": {"nova": out_text}}

        # Default: transcribe_to_text
        audio_path = extract_audio_m4a(video_path)
        transcript = transcribe_with_groq(audio_path, api_key=event.get("groq_api_key"))
        out_text = nova_with_text(transcript, prompt, region=region, profile=profile)
        payload = {"nova": out_text}
        if bool(event.get("return_transcript", False)):
            payload["transcript"] = transcript
        return {"ok": True, "data": payload}

    except Exception as e:
        return {"ok": False, "error": str(e)}

def process_video(
    input_path: str,
    mode: str = "transcribe_to_text",
    prompt: str = DEFAULT_PROMPT,
    region: str = os.environ.get("AWS_REGION", "us-east-1"),
    profile: Optional[str] = os.environ.get("AWS_PROFILE"),
    no_trim: bool = False,
    bucket: Optional[str] = None,
    prefix: str = "nova_inputs/",
    delete_after: bool = True,
    return_transcript: bool = False,
    groq_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process video through Nova Pro with specified parameters.
    
    Args:
        input_path: YouTube/TikTok URL or local video path
        mode: Processing mode ('transcribe_to_text', 'raw_video_inline', 'raw_video_s3')
        prompt: Custom instruction for processing
        region: AWS region
        profile: AWS profile name
        no_trim: Skip trimming in inline mode
        bucket: Target bucket for S3 mode
        prefix: Key prefix for S3 mode
        delete_after: Delete S3 object after processing
        return_transcript: Include transcript in output
        groq_api_key: Override GROQ_API_KEY env
    
    Returns:
        Dict containing processing results
    """
    event: Dict[str, Any] = {
        "mode": mode,
        "input": input_path,
        "prompt": prompt,
        "region": region,
        "profile": profile,
        "return_transcript": return_transcript,
    }

    if mode == "raw_video_inline":
        event["no_trim"] = no_trim
    elif mode == "raw_video_s3":
        if bucket:
            event["bucket"] = bucket
        if prefix:
            event["prefix"] = prefix
        event["delete_after"] = delete_after
    else:  # transcribe_to_text
        if groq_api_key:
            event["groq_api_key"] = groq_api_key

    return lambda_handler(event, None)

# Example usage:
if __name__ == "__main__":
    # Example: Process a TikTok video
    result = process_video(
        input_path="https://www.tiktok.com/@propertyfunfacts/video/7408904554282028295",
        mode="transcribe_to_text",
        return_transcript=True
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
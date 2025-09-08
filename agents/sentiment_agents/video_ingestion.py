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
import logging
from groq import Groq  
from strands import Agent, tool
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel
import boto3
from botocore.config import Config
from dotenv import load_dotenv
load_dotenv(".env")

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

NOVA_PRO_MODEL_ID = os.environ.get("CLAUDE_35")
WS_DEFAULT_REGION = "us-east-1"


logger.info("Bedrock region=%s model_id=%s", WS_DEFAULT_REGION, NOVA_PRO_MODEL_ID)

session = boto3.Session(region_name=WS_DEFAULT_REGION)

# Some BedrockModel versions accept inference_profile_arn; if not, it will be ignored safely
model = BedrockModel(
    model_id=NOVA_PRO_MODEL_ID,
    max_tokens=1024,
    boto_client_config=Config(
        read_timeout=120,
        connect_timeout=120,
        retries=dict(max_attempts=3, mode="adaptive"),
    ),
    boto_session=session
)

SYSTEM_PROMPT = (
    "Use the tool [download_video_transcribe] to get the video transcript for the given urls. Dont download more than 10."
    "Then, based on the transcript, provide a concise summary of the video content, focusing on key points and overall sentiment. Include video url in your output."
)

def _run(cmd: str):
    print(f"[cmd] {cmd}")
    subprocess.check_call(shlex.split(cmd))

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

@tool
def download_video_transcribe(url: str) -> Dict[str, Any]:
    """
    Download a video and return a JSON payload with the transcript (and optional sentiment).
    Returns:
      {"ok": True, "transcript": "...", "meta": {...}}
      or {"ok": False, "error": "...", "retryable": false}
    """
    try:
        if not is_url(url):
            return {"ok": False, "error": "Invalid URL", "retryable": False}

        video_path = download_web_video(url)
        audio_path = extract_audio_m4a(video_path)
        transcript = transcribe_with_groq(audio_path, api_key=os.getenv("GROQ_API_KEY"))

        return {
            "ok": True,
            "transcript": transcript,
            "meta": {"video_path": str(video_path), "audio_path": str(audio_path)}
        }
    except Exception as e:
        # If you detect rate limit / 429, set retryable=False so the agent won’t loop
        msg = str(e)
        retryable = not any(x in msg for x in ("rate limit", "Rate limit", "429"))
        return {"ok": False, "error": msg, "retryable": retryable}

transcript_understanding=Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[download_video_transcribe],
    callback_handler=PrintingCallbackHandler(),
)

# if __name__ == "__main__":
#     transcript_understanding("https://www.tiktok.com/@happynesshomessg/video/7539758751616650503")
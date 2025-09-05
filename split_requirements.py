#!/usr/bin/env python3
"""
Split a monolithic requirements.txt into multiple Lambda layer requirement files.

Default buckets:
- layer-app/requirements.txt   -> general web/app libs
- layer-aws/requirements.txt   -> boto3/botocore stack
- layer-data/requirements.txt  -> numpy/pandas (heavy native)
- layer-otel/requirements.txt  -> OpenTelemetry family (optional)

Excludes (by default): playwright, uvicorn, watchdog, pyee, bs4 (prefer beautifulsoup4)

Usage:
  python split_requirements.py requirements.txt
"""

import re
import sys
from pathlib import Path
from collections import defaultdict

# ---- Configuration -----------------------------------------------------------

# Exact-name or prefix rules; all comparisons done in lowercase
AWS_EXACT = {"boto3", "botocore", "s3transfer", "jmespath"}
DATA_EXACT = {"numpy", "pandas"}
OTEL_PREFIX = ("opentelemetry-",)  # any pkg starting with these goes to layer-otel

# Packages to skip entirely (not suitable for classic layers, or dev-only)
EXCLUDE_EXACT = {
    "playwright", "uvicorn", "watchdog", "pyee", "bs4"  # prefer beautifulsoup4 instead of bs4
}

# If both appear, prefer keeping this one:
REPLACE_DUPES = {
    "bs4": "beautifulsoup4",
}

# Optional: keep these in app even if they match other rules
APP_FORCE = {
    # e.g., "requests"
}

# Output directories (each gets a requirements.txt)
BUCKET_DIRS = {
    "app": Path("layer-app"),
    "aws": Path("layer-aws"),
    "data": Path("layer-data"),
    "otel": Path("layer-otel"),
}

# -----------------------------------------------------------------------------

NAME_RE = re.compile(r"^\s*([A-Za-z0-9_\-\.]+)")

def normalize_name(line: str) -> str:
    """
    Extract best-effort package key for routing, ignoring version specifiers/extras.
    Examples:
      'requests==2.31.0' -> 'requests'
      'pandas[perf]==2.3.2' -> 'pandas'
      'opentelemetry-sdk>=1.0' -> 'opentelemetry-sdk'
    """
    # Strip inline comments (preserve them later by writing original line)
    no_comment = line.split("#", 1)[0].strip()
    if not no_comment:
        return ""
    # Split on version/comparators
    front = re.split(r"\s*(?:==|>=|<=|~=|!=|>|<)\s*", no_comment, maxsplit=1)[0].strip()
    # Handle extras: pkg[extra]
    front = front.split("[", 1)[0].strip()
    m = NAME_RE.match(front)
    return m.group(1).lower() if m else ""

def bucket_for(name: str, line: str) -> str | None:
    """Return one of {'aws','data','otel','app'} or None (excluded)."""
    if not name:
        return "app"  # comments/blank handled elsewhere; keep safe default
    if name in EXCLUDE_EXACT:
        return None
    # prefer app if explicitly forced
    if name in APP_FORCE:
        return "app"
    # buckets
    if name in AWS_EXACT:
        return "aws"
    if name in DATA_EXACT:
        return "data"
    if any(name.startswith(pref) for pref in OTEL_PREFIX):
        return "otel"
    # default bucket
    return "app"

def main(req_path: Path):
    if not req_path.exists():
        print(f"requirements file not found: {req_path}", file=sys.stderr)
        sys.exit(1)

    # Read all lines, keep originals
    lines = req_path.read_text().splitlines()

    # Track chosen package -> canonical name to avoid both bs4 & beautifulsoup4
    seen_names: set[str] = set()
    # Bucket -> list of lines (preserve original pins/comments)
    buckets: dict[str, list[str]] = defaultdict(list)

    for raw in lines:
        stripped = raw.strip()
        # Preserve comments and blanks in app layer header for traceability
        if not stripped or stripped.startswith("#"):
            buckets["app"].append(raw)
            continue

        name = normalize_name(raw)

        # Replace duplicates (e.g., prefer beautifulsoup4 over bs4)
        if name in REPLACE_DUPES and REPLACE_DUPES[name] in (normalize_name(l) for b in buckets.values() for l in b):
            # skip the inferior/duplicate
            continue

        # Basic dedupe across all buckets by package name (not line)
        if name in seen_names:
            continue

        target = bucket_for(name, raw)
        if target is None:
            # Excluded entirely
            print(f"[-] Excluding: {raw}")
            continue

        # Mark seen and append
        seen_names.add(name)
        buckets[target].append(raw)

    # Ensure output directories & write requirement files
    for key, outdir in BUCKET_DIRS.items():
        outdir.mkdir(parents=True, exist_ok=True)
        out_file = outdir / "requirements.txt"
        lines_out = buckets.get(key, [])
        # Add header banner
        banner = [
            f"# Auto-generated from {req_path.name}",
            f"# Bucket: {key}",
            "# Edit the root requirements.txt and re-run the splitter.\n",
        ]
        out_file.write_text("\n".join(banner + lines_out) + "\n")
        print(f"[+] Wrote {out_file} ({len(lines_out)} lines)")

    # Also generate a minimal build script users can tweak
    build_sh = Path("build_layers.sh")
    build_sh.write_text("""#!/usr/bin/env bash
set -euo pipefail

# Pick the correct base for your Lambda Python runtime:
# - Python 3.12 -> Amazon Linux 2023
# - Python 3.11 -> Amazon Linux 2 (change image and package names accordingly)

IMG="public.ecr.aws/amazonlinux/amazonlinux:2023"
PYBIN="python3.12"

docker run --rm -it -v "$PWD":/opt -w /opt "$IMG" bash -lc '
  dnf install -y """ + " ".join([
      "python3.12", "python3.12-pip", "zip", "findutils", "binutils"
  ]) + r"""
  $PYBIN -m pip install --upgrade pip

  for L in layer-app layer-aws layer-data layer-otel; do
    if [[ -f "$L/requirements.txt" ]]; then
      rm -rf "$L/python" && mkdir -p "$L/python"
      $PYBIN -m pip install --no-cache-dir -r "$L/requirements.txt" -t "$L/python"
      find "$L/python" -type d -name "__pycache__" -prune -exec rm -rf {} +
      find "$L/python" -type d -name "tests" -prune -exec rm -rf {} +
      # Optional: remove metadata to shrink (safe at runtime)
      find "$L/python" -type d -name "*.dist-info" -prune -exec rm -rf {} +
      # Optional: strip native .so in data layer
      if [[ "$L" == "layer-data" ]]; then
        find "$L/python" -type f -name "*.so" -exec strip {} + || true
      fi
      (cd "$L" && zip -r9 "../$L.zip" python)
      echo "Built $L.zip"
    fi
  done
'
echo "Done. Publish each *zip as a Lambda layer."
""")
    build_sh.chmod(0o755)
    print(f"[+] Wrote {build_sh}")

if __name__ == "__main__":
    req = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("requirements.txt")
    main(req)
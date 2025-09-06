#!/usr/bin/env bash
set -euo pipefail

# Pick the correct base for your Lambda Python runtime:
# - Python 3.12 -> Amazon Linux 2023
# - Python 3.11 -> Amazon Linux 2 (change image and package names accordingly)

IMG="public.ecr.aws/amazonlinux/amazonlinux:2023"
PYBIN="python3.12"

docker run --rm -it -v "$PWD":/opt -w /opt "$IMG" bash -lc '
  dnf install -y python3.12 python3.12-pip zip findutils binutils
  PYBIN=python3.12
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

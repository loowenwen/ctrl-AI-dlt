#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

build_zip () {
  MODPATH="$1"        # directory containing code
  OUTNAME="$2"        # output zip name
  shift 2
  FILES=("$@")        # files to include

  pushd "$ROOT/$MODPATH" >/dev/null
  rm -rf dist build && mkdir -p dist build

  # If there's a requirements.txt, vendor deps into build/
  if [[ -f requirements.txt && -s requirements.txt ]]; then
    pip install --upgrade -r requirements.txt -t build
  fi

  # copy files
  for f in "${FILES[@]}"; do cp "$f" build/; done

  (cd build && zip -qr "../dist/$OUTNAME" .)
  echo "Built $ROOT/$MODPATH/dist/$OUTNAME"
  popd >/dev/null
}

# 1) Web aggregator (light zip)
build_zip "search" "websearch_lambda.zip" "websearch_lambda.py" 

# 2) Router (light zip) - router_lambda.py is in current folder
build_zip "." "router_lambda.zip" "router_lambda.py" 
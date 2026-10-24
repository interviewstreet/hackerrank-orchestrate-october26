#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
rm -f code.zip
find code -type d -name __pycache__ -prune -exec rm -rf {} +
rm -f code/cache.json
zip -r code.zip README.md code \
  -x "*/__pycache__/*" "*/.venv/*" "*/venv/*" "*/node_modules/*" \
     "*/.git/*" "*/.DS_Store" "code/cache.json" "*.pyc"
unzip -t code.zip >/dev/null
printf 'Created %s/code.zip\n' "$ROOT"

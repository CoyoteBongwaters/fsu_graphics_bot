#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

SRC="$SCRIPT_DIR/ps_apply_plan_export.applescript"
OUT="$SCRIPT_DIR/ps_apply_plan_export.scpt"

if [[ ! -f "$SRC" ]]; then
  echo "Missing source: $SRC" >&2
  exit 1
fi

# Compile AppleScript source to .scpt
osacompile -o "$OUT" "$SRC"

echo "Built: $OUT"
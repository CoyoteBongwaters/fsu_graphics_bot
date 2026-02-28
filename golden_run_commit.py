#!/usr/bin/env python3
"""
golden_run.py

Golden-path smoke test for the deterministic chain:
event json -> run_photoshop.py -> plan json -> asserts critical ops -> confirms PNG

It does NOT change core logic. It wraps what already exists and verifies outputs.

Hard-fails if:
- run_photoshop fails
- plan file can't be located
- PLAYER_CUTOUT op missing or not smart_object
- HAS_PLAYER_CUTOUT toggle missing / not enabled
- output PNG missing / zero bytes
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


RE_RUNNING = re.compile(r"^Running:\s+osascript\s+(.+)$")


def _die(msg: str, code: int = 1) -> None:
    print(f"[GOLDEN FAIL] {msg}")
    sys.exit(code)


def _parse_running_line(all_output: str) -> tuple[Path, Path, Path] | None:
    """
    Extracts the psd_path, plan_path, png_path from the:
      Running: osascript <scpt> <psd> <plan> <png>
    line emitted by run_photoshop.py.
    """
    for line in all_output.splitlines():
        m = RE_RUNNING.match(line.strip())
        if not m:
            continue
        tail = m.group(1).strip()
        # Expect: "<scpt> <psd> <plan> <png>"
        parts = tail.split()
        if len(parts) < 4:
            continue
        psd_path = Path(parts[-3])
        plan_path = Path(parts[-2])
        png_path = Path(parts[-1])
        return psd_path, plan_path, png_path
    return None


def _load_plan(plan_path: Path) -> list[dict]:
    try:
        with plan_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        _die(f"Could not read plan JSON at {plan_path}: {e}")

    if not isinstance(data, list):
        _die(f"Plan JSON root must be a list (ops). Got: {type(data)}")

    for i, op in enumerate(data):
        if not isinstance(op, dict):
            _die(f"Plan op #{i} must be dict. Got: {type(op)}")

    return data


def _find_op(ops: list[dict], *, layer: str) -> dict | None:
    for op in ops:
        if op.get("layer") == layer:
            return op
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter to run run_photoshop.py (default: current interpreter).",
    )
    parser.add_argument(
        "--repo",
        default=str(Path(__file__).resolve().parent),
        help="Repo root (default: directory containing this file).",
    )
    parser.add_argument(
        "--event-json",
        default="",
        help="Optional: explicit path to an out/json/*.json event file. If omitted, uses run_photoshop.py default.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    run_photoshop = repo_root / "run_photoshop.py"
    if not run_photoshop.exists():
        _die(f"Missing {run_photoshop}")

    # Run existing runner (source of truth).
    cmd = [args.python, str(run_photoshop)]
    if args.event_json:
        cmd += ["--event-json", args.event_json]

    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )

    combined = (proc.stdout or "") + (proc.stderr or "")
    print(combined.rstrip())

    if proc.returncode != 0:
        _die(f"run_photoshop.py exited non-zero ({proc.returncode}). See output above.")

    parsed = _parse_running_line(combined)
    if not parsed:
        _die("Could not find/parse the 'Running: osascript ...' line to locate plan/png paths.")

    psd_path, plan_path, png_path = parsed

    if not psd_path.exists():
        _die(f"PSD path reported but missing: {psd_path}")

    if not plan_path.exists():
        _die(f"Plan path reported but missing: {plan_path}")

    if not png_path.exists():
        _die(f"PNG path reported but missing: {png_path}")

    if png_path.stat().st_size == 0:
        _die(f"PNG exists but is 0 bytes: {png_path}")

    ops = _load_plan(plan_path)

        # --- Commit template assertions ---

    photo_op = _find_op(ops, layer="PLAYER_PHOTO")
    if not photo_op:
        _die("Plan missing required op for layer PLAYER_PHOTO (expected set_image smart_object).")

    if photo_op.get("op") != "set_image":
        _die(f"PLAYER_PHOTO op must be set_image. Got: {photo_op.get('op')}")

    meta = photo_op.get("meta") or {}
    if meta.get("image_type") != "smart_object":
        _die(f"PLAYER_PHOTO meta.image_type must be smart_object. Got: {meta.get('image_type')}")

    photo_value = photo_op.get("value")
    if not isinstance(photo_value, str) or not photo_value:
        _die("PLAYER_PHOTO value must be a non-empty string path.")

    # Resolve relative asset paths against repo root.
    photo_path = (repo_root / photo_value).resolve() if not os.path.isabs(photo_value) else Path(photo_value)
    if not photo_path.exists():
        _die(f"Photo asset referenced in plan does not exist: {photo_path}")

    toggle_headshot = _find_op(ops, layer="HAS_HEADSHOT")
    if not toggle_headshot:
        _die("Plan missing required toggle for HAS_HEADSHOT.")
    if toggle_headshot.get("op") != "toggle":
        _die(f"HAS_HEADSHOT op must be toggle. Got: {toggle_headshot.get('op')}")
    if toggle_headshot.get("value") is not True:
        _die(f"HAS_HEADSHOT value must be true. Got: {toggle_headshot.get('value')!r}")

    toggle_cutout = _find_op(ops, layer="HAS_PLAYER_CUTOUT")
    if not toggle_cutout:
        _die("Plan missing required toggle for HAS_PLAYER_CUTOUT.")
    if toggle_cutout.get("op") != "toggle":
        _die(f"HAS_PLAYER_CUTOUT op must be toggle. Got: {toggle_cutout.get('op')}")
    if toggle_cutout.get("value") is not False:
        _die(f"HAS_PLAYER_CUTOUT value must be false for commit (headshot mode). Got: {toggle_cutout.get('value')!r}")

    required_text_layers = ["PLAYER_NAME", "HEADLINE"]
    for layer in required_text_layers:
        op = _find_op(ops, layer=layer)
        if not op:
            _die(f"Plan missing required text op for layer {layer}.")
        if op.get("op") != "set_text":
            _die(f"{layer} op must be set_text. Got: {op.get('op')}")
        if not isinstance(op.get("value"), str) or op.get("value") == "":
            _die(f"{layer} value must be a non-empty string.")

    print("\n[GOLDEN PASS]")
    print(f"PSD:  {psd_path}")
    print(f"PLAN: {plan_path}")
    print(f"PNG:  {png_path} ({png_path.stat().st_size} bytes)")
    print(f"PHOTO: {photo_path}")
    print("Verified: PLAYER_PHOTO=set_image smart_object + HAS_HEADSHOT=true + HAS_PLAYER_CUTOUT=false + PLAYER_NAME/HEADLINE set_text")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
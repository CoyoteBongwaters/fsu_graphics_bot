#!/usr/bin/env python3
"""
golden_run_fallback.py

Golden-path fallback smoke test:
Ensures that when no player cutout exists, the plan:
- does NOT include PLAYER_CUTOUT set_image
- sets HAS_PLAYER_CUTOUT=false
- sets HEADSHOT image (pixel)
- sets HAS_HEADSHOT=true
- exports a non-empty PNG
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RE_RUNNING = re.compile(r"^Running:\s+osascript\s+(.+)$")


def _die(msg: str, code: int = 1) -> None:
    print(f"[GOLDEN FAIL] {msg}")
    sys.exit(code)


def _parse_running_line(all_output: str) -> tuple[Path, Path, Path] | None:
    for line in all_output.splitlines():
        m = RE_RUNNING.match(line.strip())
        if not m:
            continue
        tail = m.group(1).strip()
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
        _die(f"Plan JSON root must be list. Got: {type(data)}")
    for i, op in enumerate(data):
        if not isinstance(op, dict):
            _die(f"Plan op #{i} must be dict. Got: {type(op)}")
    return data


def _find_op(ops: list[dict], layer: str) -> dict | None:
    for op in ops:
        if op.get("layer") == layer:
            return op
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parent))
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

    cmd = [args.python, str(run_photoshop)]
    if args.event_json:
        cmd += ["--event-json", args.event_json]

    proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
    combined = (proc.stdout or "") + (proc.stderr or "")
    print(combined.rstrip())

    if proc.returncode != 0:
        _die(f"run_photoshop.py exited non-zero ({proc.returncode}). See output above.")

    parsed = _parse_running_line(combined)
    if not parsed:
        _die("Could not parse 'Running: osascript ...' line to locate plan/png paths.")

    psd_path, plan_path, png_path = parsed

    if not psd_path.exists():
        _die(f"PSD missing: {psd_path}")
    if not plan_path.exists():
        _die(f"Plan missing: {plan_path}")
    if not png_path.exists():
        _die(f"PNG missing: {png_path}")
    if png_path.stat().st_size == 0:
        _die(f"PNG is 0 bytes: {png_path}")

    ops = _load_plan(plan_path)

    if _find_op(ops, "PLAYER_CUTOUT") is not None:
        _die("Fallback mode must NOT include PLAYER_CUTOUT set_image op.")

    has_cutout = _find_op(ops, "HAS_PLAYER_CUTOUT")
    if not has_cutout or has_cutout.get("op") != "toggle" or has_cutout.get("value") is not False:
        _die(f"Expected HAS_PLAYER_CUTOUT toggle false. Got: {has_cutout}")

    headshot = _find_op(ops, "HEADSHOT")
    if not headshot or headshot.get("op") != "set_image":
        _die(f"Expected HEADSHOT set_image. Got: {headshot}")
    meta = headshot.get("meta") or {}
    if meta.get("image_type") != "pixel":
        _die(f"HEADSHOT meta.image_type must be pixel. Got: {meta.get('image_type')}")
    if not isinstance(headshot.get("value"), str) or headshot.get("value") == "":
        _die("HEADSHOT value must be a non-empty path string.")

    has_headshot = _find_op(ops, "HAS_HEADSHOT")
    if not has_headshot or has_headshot.get("op") != "toggle" or has_headshot.get("value") is not True:
        _die(f"Expected HAS_HEADSHOT toggle true. Got: {has_headshot}")

    print("\n[GOLDEN PASS]")
    print(f"PSD:  {psd_path}")
    print(f"PLAN: {plan_path}")
    print(f"PNG:  {png_path} ({png_path.stat().st_size} bytes)")
    print("Verified: fallback mode (no cutout) => HAS_PLAYER_CUTOUT=false + HEADSHOT pixel + HAS_HEADSHOT=true")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

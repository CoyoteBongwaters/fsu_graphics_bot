#!/usr/bin/env python3
"""
golden_run_breaking_news.py

Golden-path smoke test for breaking_news template.
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


def _assert_set_text(ops: list[dict], layer: str) -> None:
    op = _find_op(ops, layer=layer)
    if not op:
        _die(f"Plan missing required text op for layer {layer}.")
    if op.get("op") != "set_text":
        _die(f"{layer} op must be set_text. Got: {op.get('op')}")
    if not isinstance(op.get("value"), str) or op.get("value") == "":
        _die(f"{layer} value must be a non-empty string.")


def _assert_toggle_true(ops: list[dict], layer: str) -> None:
    op = _find_op(ops, layer=layer)
    if not op:
        _die(f"Plan missing required toggle for {layer}.")
    if op.get("op") != "toggle":
        _die(f"{layer} op must be toggle. Got: {op.get('op')}")
    if op.get("value") is not True:
        _die(f"{layer} value must be true. Got: {op.get('value')!r}")


def _assert_set_image_exists(ops: list[dict], *, repo_root: Path, layer: str, expect_image_type: str | None) -> Path:
    op = _find_op(ops, layer=layer)
    if not op:
        _die(f"Plan missing required image op for layer {layer}.")
    if op.get("op") != "set_image":
        _die(f"{layer} op must be set_image. Got: {op.get('op')}")

    if expect_image_type is not None:
        meta = op.get("meta") or {}
        if meta.get("image_type") != expect_image_type:
            _die(f"{layer} meta.image_type must be {expect_image_type}. Got: {meta.get('image_type')}")

    value = op.get("value")
    if not isinstance(value, str) or not value:
        _die(f"{layer} value must be a non-empty string path.")

    path = (repo_root / value).resolve() if not os.path.isabs(value) else Path(value)
    if not path.exists():
        _die(f"{layer} asset referenced in plan does not exist: {path}")

    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    run_photoshop = repo_root / "run_photoshop.py"
    if not run_photoshop.exists():
        _die(f"Missing {run_photoshop}")

    event_json = repo_root / "out" / "json" / "breaking_news_test.json"
    if not event_json.exists():
        _die(f"Missing fixture JSON: {event_json}")

    cmd = [args.python, str(run_photoshop), "--event-json", str(event_json)]
    proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)

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

    _assert_set_text(ops, "PLAYER_NAME")
    _assert_set_text(ops, "HEADLINE")

    player_photo_path = _assert_set_image_exists(
        ops, repo_root=repo_root, layer="PLAYER_PHOTO", expect_image_type="smart_object"
    )
    headshot_path = _assert_set_image_exists(
        ops, repo_root=repo_root, layer="HEADSHOT", expect_image_type=None
    )

    _assert_toggle_true(ops, "HAS_PLAYER_CUTOUT")
    _assert_toggle_true(ops, "HAS_HEADSHOT")

    norm = str(png_path).replace("\\", "/")
    if "/out/render/fsu/" not in norm:
        _die(f"Unexpected routing (expected out/render/fsu): {png_path}")

    print("\n[GOLDEN PASS]")
    print(f"PSD:  {psd_path}")
    print(f"PLAN: {plan_path}")
    print(f"PNG:  {png_path} ({png_path.stat().st_size} bytes)")
    print(f"PLAYER_PHOTO: {player_photo_path}")
    print(f"HEADSHOT: {headshot_path}")
    print("Verified: breaking_news minimal contract ops + routing")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
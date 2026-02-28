from __future__ import annotations

import json
import sys
from pathlib import Path

from models import AssetPaths, Event
from render_plan_engine import build_render_plan


def _die(msg: str, code: int = 1) -> None:
    print(f"[NEGATIVE GOLDEN FAIL] {msg}")
    sys.exit(code)


def main() -> int:
    """
    Negative golden: unknown template_key must hard-fail at plan build.
    This protects the invariant: no fallback routing for unknown keys.
    """

    payload_path = Path("out/json/commit_golden.json")
    if not payload_path.exists():
        _die("Missing out/json/commit_golden.json (run commit golden creation first).")

    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    # Force the contract violation: unknown template_key
    payload["template_key"] = "fsu.__does_not_exist__"

    assets_data = payload.get("assets") or {}
    assets = AssetPaths(
        logo_primary=assets_data.get("logo_primary"),
        logo_secondary=assets_data.get("logo_secondary"),
        headshot=assets_data.get("headshot"),
        player_cutout=assets_data.get("player_cutout"),
        background=assets_data.get("background"),
    )

    event = Event(
        source=payload["source"],
        headline=payload["headline"],
        event_type=payload["event_type"],
        template_key=payload.get("template_key", payload["event_type"]),
        teams=payload["teams"],
        players=payload["players"],
        created_at_utc=payload["created_at_utc"],
        meta=payload.get("meta"),
        assets=assets,
        style_profile=payload.get("style_profile"),
    )

    try:
        _plan = build_render_plan(event)
    except Exception as e:
        print("[NEGATIVE GOLDEN PASS] plan build failed as expected")
        print(f"{type(e).__name__}: {e}")
        return 0

    _die("plan build unexpectedly succeeded (expected failure for unknown template_key).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

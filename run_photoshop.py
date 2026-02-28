from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
from models import Event
from template_engine import select_template
from render_plan_engine import build_render_plan


REPO_ROOT = Path(__file__).resolve().parent
PS_APPLESCRIPT = REPO_ROOT / "executors" / "ps_apply_plan_export.scpt"


def _latest_json() -> Path:
    jdir = REPO_ROOT / "out" / "json"
    files = sorted(jdir.glob("*.json"), reverse=True)
    if not files:
        raise SystemExit("No out/json/*.json found. Run practice.py first.")
    return files[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-json", required=True, help="Path to event JSON.")
    args = parser.parse_args()

    event_path = Path(args.event_json)
    if not event_path.exists():
        raise SystemExit(f"Event JSON not found: {event_path}")

    payload = json.loads(event_path.read_text(encoding="utf-8"))

    # Build minimal Event from payload for deterministic template selection
    from models import AssetPaths

    assets_data = payload.get("assets") or {}
    assets = AssetPaths(
        logo_primary=assets_data.get("logo_primary"),
        logo_secondary=assets_data.get("logo_secondary"),
        headshot=assets_data.get("headshot"),
        player_cutout=assets_data.get("player_cutout"),
        background=assets_data.get("background"),
    )
    # --- universal validation ---
    required_fields = [
        "schema_version",
        "source",
        "headline",
        "event_type",
        "template_key",
        "teams",
        "players",
        "created_at_utc",
    ]

    for field in required_fields:
        if field not in payload:
            raise ValueError(f"Missing required field: {field}")
        if isinstance(payload[field], str) and not payload[field].strip():
            raise ValueError(f"Required field '{field}' is empty")

    template_key = payload.get("template_key")
    if not template_key or not str(template_key).strip():
        raise ValueError("template_key is required and cannot be empty")
    event = Event(
        source=payload["source"],
        headline=payload["headline"],
        event_type=payload["event_type"],
        template_key=payload["template_key"],
        teams=payload["teams"],
        players=payload["players"],
        created_at_utc=payload["created_at_utc"],
        meta=payload.get("meta"),
        assets=assets,
        style_profile=payload.get("style_profile"),
    )

    tmpl = select_template(event)
    psd_path = REPO_ROOT / tmpl.template_path
    if not psd_path.exists():
        raise SystemExit(f"Missing PSD: {psd_path}")

    template_key = (payload.get("template_key") or "").strip()
    namespace = template_key.split(".", 1)[0] if "." in template_key else ""
    out_dir = REPO_ROOT / "out" / "render" / namespace if namespace else REPO_ROOT / "out" / "render"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / (event_path.stem + ".png")
    # Write plan to a temp json file (executor reads it)
    plan_path = REPO_ROOT / "out" / "psd" / (event_path.stem + "_plan.json")
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan = build_render_plan(event)
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    cmd = [
        "osascript",
        str(PS_APPLESCRIPT),
        str(psd_path),
        str(plan_path),
        str(out_png),
    ]

    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr)
        return res.returncode

    print(res.stdout.strip())
    print("Wrote:", out_png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
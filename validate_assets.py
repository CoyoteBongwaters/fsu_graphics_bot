from __future__ import annotations

import json
import sys
from pathlib import Path


def _exists(p: str) -> bool:
    # Allow absolute or relative paths; validate existence on disk.
    return Path(p).expanduser().exists()


def main() -> int:
    json_dir = Path("out/json")
    if not json_dir.exists():
        print("No out/json folder found yet.")
        return 1

    files = sorted(json_dir.glob("*.json"), reverse=True)
    if not files:
        print("No JSON files found in out/json.")
        return 1

    latest = files[0]
    data = json.loads(latest.read_text(encoding="utf-8"))

    errors: list[str] = []

    assets = data.get("assets")
    if not isinstance(assets, dict):
        errors.append("assets missing or invalid (expected object).")
    else:
        # Required deterministic assets (these should always resolve to something valid)
        required = ["logo_primary", "background"]
        for k in required:
            v = assets.get(k)
            if not isinstance(v, str) or not v.strip():
                errors.append(f"assets.{k} missing/invalid (required).")
            elif not _exists(v):
                errors.append(f"assets.{k} path does not exist: {v}")

        # Optional assets
        optional = ["logo_secondary", "headshot", "player_cutout"]
        for k in optional:
            v = assets.get(k)
            if v is None:
                continue
            if not isinstance(v, str) or not v.strip():
                errors.append(f"assets.{k} invalid (expected non-empty string or null).")
                continue
            if not _exists(v):
                errors.append(f"assets.{k} path does not exist: {v}")

        # Precedence invariant: never allow both visuals to be present
        hs = assets.get("headshot")
        pc = assets.get("player_cutout")
        if hs and pc:
            errors.append(
                "asset precedence violated: both assets.headshot and assets.player_cutout are set "
                "(player_cutout must suppress headshot)."
            )

    # Also validate render_plan set_image values (execution-level reality check)
    rp = data.get("render_plan")
    if isinstance(rp, list):
        for i, op in enumerate(rp):
            if not isinstance(op, dict):
                continue
            if op.get("op") != "set_image":
                continue
            v = op.get("value")
            if not isinstance(v, str) or not v.strip():
                errors.append(f"render_plan[{i}].value invalid for set_image.")
                continue
            if not _exists(v):
                errors.append(f"render_plan[{i}] set_image path does not exist: {v}")
    else:
        errors.append("render_plan missing or invalid (expected list).")

    if errors:
        print(f"ASSET VALIDATION: FAILED ({latest.name})\n")
        for e in errors:
            print(" -", e)
        return 1

    print(f"ASSET VALIDATION: OK ({latest.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
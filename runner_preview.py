from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    json_dir = Path("out/json")
    files = sorted(json_dir.glob("*.json"), reverse=True)
    if not files:
        print("No JSON files found in out/json.")
        return 1

    latest = files[0]
    data = json.loads(latest.read_text(encoding="utf-8"))

    template = data.get("template", {})
    template_path = template.get("template_path", "")

    print(f"TEMPLATE: {template_path}")
    print(f"EVENT_TYPE: {data.get('event_type')}")
    print("")

    rp = data.get("render_plan", [])
    if not rp:
        print("No render_plan found.")
        return 1

    print("RENDER PLAN PREVIEW:")
    for op in rp:
        o = op["op"]
        layer = op["layer"]
        value = op["value"]

        if o == "set_text":
            print(f' - SET_TEXT   layer="{layer}" value="{value}"')
        elif o == "set_image":
            print(f' - SET_IMAGE  layer="{layer}" path="{value}"')
        elif o == "toggle":
            print(f' - TOGGLE     layer="{layer}" visible={value}')
        else:
            print(f" - UNKNOWN    {op}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
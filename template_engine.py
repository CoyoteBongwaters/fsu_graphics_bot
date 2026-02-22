from pathlib import Path
import json

def load_template_map() -> dict:
    """Load mapping of event_type → template metadata file."""
    path = Path("template_map.json")
    if not path.exists():
        print("⚠️  template_map.json not found.")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def get_template_info(event_type: str) -> dict:
    """Return the metadata info for a given event_type."""
    templates = load_template_map()
    info = templates.get(event_type, templates.get("unknown", {}))

    if not info:
        print(f"⚠️  No template found for event_type: {event_type}")
        return {}

    template_path = Path(info["template_path"])
    if not template_path.exists():
        print(f"⚠️  PSD template file missing: {template_path}")
        info["assets_found"] = False
    else:
        info["assets_found"] = True

    info["event_type"] = event_type
    info["template_file"] = template_path.name
    return info

from pathlib import Path
import json
from models import Event, TemplateInfo

def load_template_map() -> dict:
    """Load mapping of event_type → template metadata file."""
    path = Path("template_map.json")
    if not path.exists():
        print("⚠️  template_map.json not found.")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def select_template(event: Event) -> TemplateInfo:
    """Return template metadata for this event."""
    templates = load_template_map()
    info = templates.get(event.event_type, templates.get("unknown", {}))

    if not info:
        print(f"⚠️  No template found for event_type: {event.event_type}")
        return TemplateInfo(template_path="")

    template_path = Path(info["template_path"])
    template_found = template_path.exists()

    if not template_found:
        if bool(info.get("require_psd_file", False)):
            raise FileNotFoundError(f"PSD template file missing: {template_path}")

    return TemplateInfo(
        template_path=str(template_path),
        notes=info.get("notes", ""),
        template_found=template_found,
        event_type=event.event_type,
        template_file=template_path.name,
    )

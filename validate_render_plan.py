from __future__ import annotations

import json
import sys
from pathlib import Path
from template_engine import load_template_map

ALLOWED_OPS = {"set_text", "set_image", "toggle"}


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
    # If template_map.json specifies an image type for a given image layer binding,
    # enforce that the generated render_plan carries matching meta.image_type.
    expected_image_types: dict[str, str] = {}
    # Validate render_plan layer targets against PSD layer manifest for this event_type
    allowed_layers: set[str] | None = None

    event_type = data.get("event_type")
    if not isinstance(event_type, str) or not event_type.strip():
        errors.append("event_type missing or invalid (needed for manifest validation).")
    else:
        templates = load_template_map()
        spec = templates.get(event_type)
        if not isinstance(spec, dict):
            errors.append(f"event_type {event_type!r} not found in template_map.json (needed for manifest validation).")
        else:
            render_spec = spec.get("render_spec") or {}
            images_spec = (render_spec.get("images") or {}) if isinstance(render_spec, dict) else {}
            if isinstance(images_spec, dict):
                for layer_name, image_bind in images_spec.items():
                    if not isinstance(layer_name, str) or not layer_name.strip():
                        continue
                    if isinstance(image_bind, dict):
                        t = image_bind.get("type")
                        if t in {"smart_object", "pixel"}:
                            expected_image_types[layer_name] = t
            template_path = spec.get("template_path")
            if not isinstance(template_path, str) or not template_path.strip():
                errors.append(f"{event_type}: template_path missing/invalid (needed for manifest validation).")
            else:
                manifest_path = Path(template_path).with_suffix(".layer_manifest.json")
                if not manifest_path.exists():
                    errors.append(f"{event_type}: missing PSD layer manifest at {manifest_path.resolve().as_posix()}")
                else:
                    m = json.loads(manifest_path.read_text(encoding="utf-8"))
                    layers = m.get("layers")
                    if not isinstance(layers, list) or not all(isinstance(x, str) and x.strip() for x in layers):
                        errors.append(f"{event_type}: manifest {manifest_path.as_posix()} has invalid 'layers' list.")
                    else:
                        allowed_layers = set(layers)
    rp = data.get("render_plan")
    if not isinstance(rp, list) or not rp:
        errors.append("render_plan missing or empty.")
    else:
        for i, op in enumerate(rp):
            if not isinstance(op, dict):
                errors.append(f"render_plan[{i}] must be an object.")
                continue

            o = op.get("op")
            layer = op.get("layer")

            if o not in ALLOWED_OPS:
                errors.append(f"render_plan[{i}].op invalid: {o!r}")
            if not isinstance(layer, str) or not layer.strip():
                errors.append(f"render_plan[{i}].layer invalid: {layer!r}")
            if allowed_layers is not None and isinstance(layer, str) and layer.strip():
                if layer not in allowed_layers:
                    errors.append(f"render_plan[{i}].layer {layer!r} not present in PSD manifest for event_type={event_type!r}.")
            # value checks by op type
            if o in {"set_text", "set_image"}:
                v = op.get("value")
                if not isinstance(v, str) or not v.strip():
                    errors.append(f"render_plan[{i}].value must be a non-empty string for op={o}.")
            elif o == "toggle":
                v = op.get("value")
                if not isinstance(v, bool):
                    errors.append(f"render_plan[{i}].value must be boolean for op=toggle.")
            if o == "set_image" and isinstance(layer, str) and layer.strip():
                expected = expected_image_types.get(layer)
                if expected is not None:
                    meta = op.get("meta")
                    image_type = meta.get("image_type") if isinstance(meta, dict) else None
                    if image_type != expected:
                        errors.append(
                            f"render_plan[{i}] set_image meta.image_type mismatch for layer {layer!r}: "
                            f"expected {expected!r}, got {image_type!r}"
                        )
    if errors:
        print(f"RENDER PLAN VALIDATION: FAILED ({latest.name})\n")
        for e in errors:
            print(" -", e)
        return 1

    print(f"RENDER PLAN VALIDATION: OK ({latest.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
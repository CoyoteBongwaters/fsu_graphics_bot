from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models import Event
from template_engine import load_template_map


@dataclass(frozen=True, slots=True)
class RenderOp:
    """
    Render operation for downstream Photoshop automation.

    op:
      - set_text: set a text layer's contents
      - set_image: replace a smart object layer's contents with an image path
      - toggle: show/hide a layer or group
    """
    op: str
    layer: str
    value: Any
    meta: dict[str, Any] | None = None


def _get_path(d: dict[str, Any], path: str) -> Any:
    """Resolve dotted paths like 'meta.winner_score' from a dict."""
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def build_render_plan(event: Event) -> list[dict[str, Any]]:
    """
    Build an automation-ready plan for filling a PSD based on template_map.json.
    Output is a list of dicts for JSON stability.
    """
    templates = load_template_map()
    info = templates.get(event.event_type, templates.get("unknown", {}))
    render_spec = info.get("render_spec", {}) or {}
    style_spec = info.get("style_spec", {}) or {}

    binding = event.to_dict()

    ops: list[RenderOp] = []

    # --- text layers ---
    for layer, bind_path in (render_spec.get("text", {}) or {}).items():
        val = _get_path(binding, bind_path)
        if val is None:
            continue
        ops.append(RenderOp(op="set_text", layer=layer, value=str(val)))

    # --- image / smart object layers ---
    for layer, image_spec in (render_spec.get("images", {}) or {}).items():
        # image_spec can be:
        # 1) "assets.logo_primary"
        # 2) {"binding": "assets.logo_primary", "type": "smart_object"|"pixel"}

        if isinstance(image_spec, str):
            bind_path = image_spec
            image_type = "pixel"
        elif isinstance(image_spec, dict):
            bind_path = image_spec.get("binding")
            image_type = image_spec.get("type")
        else:
            continue

        val = _get_path(binding, bind_path)
        if val is None:
            continue
        if isinstance(val, str) and not val.strip():
            continue

        # For now we emit the same op shape.
        # image_type is future execution-layer metadata.
        meta = None
        if image_type in {"smart_object", "pixel"}:
            meta = {"image_type": image_type}

        ops.append(RenderOp(op="set_image", layer=layer, value=str(val), meta=meta))
    # --- toggles ---
    # Convention: if binding resolves to None/""/[] -> False, else True
    for layer, bind_path in (render_spec.get("toggles", {}) or {}).items():
        val = _get_path(binding, bind_path)
        ops.append(RenderOp(op="toggle", layer=layer, value=bool(val)))
    # --- style toggles ---
    style_profile = event.style_profile
    if style_profile and style_profile in style_spec:
        style_conf = style_spec[style_profile]
        for layer, value in (style_conf.get("toggles", {}) or {}).items():
            ops.append(RenderOp(op="toggle", layer=layer, value=bool(value)))
    out: list[dict[str, Any]] = []
    for r in ops:
        d: dict[str, Any] = {"op": r.op, "layer": r.layer, "value": r.value}
        if r.meta:
            d["meta"] = r.meta
        out.append(d)
    return out
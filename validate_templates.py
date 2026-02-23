from __future__ import annotations

import sys
from pathlib import Path

from template_engine import load_template_map
from psd_contract_validator import validate_psd_contracts


ALLOWED_OP_GROUPS = {"text", "images", "toggles"}


def main() -> int:
    templates = load_template_map()

    errors: list[str] = []

    if not isinstance(templates, dict) or not templates:
        errors.append("template_map.json must be a non-empty JSON object at the top level.")
    else:
        for event_type, spec in templates.items():
            if not isinstance(spec, dict):
                errors.append(f"{event_type}: spec must be an object.")
                continue

            template_path = spec.get("template_path")
            if not isinstance(template_path, str) or not template_path.strip():
                errors.append(f"{event_type}: missing/invalid template_path.")

            render_spec = spec.get("render_spec")
            if render_spec is None:
                # Not required for every type yet
                continue

            if not isinstance(render_spec, dict):
                errors.append(f"{event_type}: render_spec must be an object.")
                continue

            # Unknown groups check
            for k in render_spec.keys():
                if k not in ALLOWED_OP_GROUPS:
                    errors.append(f"{event_type}: render_spec has unknown group '{k}' (allowed: {sorted(ALLOWED_OP_GROUPS)}).")

            # Each group must be a dict of layer -> bind_path
            for group in ALLOWED_OP_GROUPS:
                group_map = render_spec.get(group)
                if group_map is None:
                    continue
                if not isinstance(group_map, dict):
                    errors.append(f"{event_type}: render_spec.{group} must be an object mapping layer->binding_path.")
                    continue

                for layer, bind_path in group_map.items():
                    if not isinstance(layer, str) or not layer.strip():
                        errors.append(f"{event_type}: render_spec.{group} has invalid layer name: {layer!r}")
                    if group == "images":
                        # images can be either:
                        # 1) "assets.logo_primary"
                        # 2) {"binding": "assets.logo_primary", "type": "smart_object"|"pixel"}
                        if isinstance(bind_path, str):
                            if not bind_path.strip():
                                errors.append(f"{event_type}: render_spec.images.{layer}: binding_path must be a non-empty string.")
                        elif isinstance(bind_path, dict):
                            binding = bind_path.get("binding")
                            img_type = bind_path.get("type")
                            if not isinstance(binding, str) or not binding.strip():
                                errors.append(f"{event_type}: render_spec.images.{layer}.binding must be a non-empty string.")
                            if img_type not in {"smart_object", "pixel"}:
                                errors.append(f"{event_type}: render_spec.images.{layer}.type must be 'smart_object' or 'pixel'.")
                        else:
                            errors.append(f"{event_type}: render_spec.images.{layer} must be a string or object.")
                    else:
                        if not isinstance(bind_path, str) or not bind_path.strip():
                            errors.append(f"{event_type}: render_spec.{group}.{layer}: binding_path must be a non-empty string.")
    # --- PSD layer contract enforcement (static manifest) ---
    psd_issues = validate_psd_contracts(Path(__file__).resolve().parent)
    for issue in psd_issues:
        if issue.missing_layers == ["<missing manifest>"]:
            errors.append(f"{issue.event_type}: missing PSD layer manifest at {issue.manifest_path.as_posix()}")
            continue
        for m in issue.missing_layers:
            errors.append(f"{issue.event_type}: PSD manifest missing layer '{m}' ({issue.manifest_path.as_posix()})")
        for d in issue.duplicated_layers:
            errors.append(f"{issue.event_type}: layer '{d}' is defined multiple times across render/style specs")
    if errors:
        print("TEMPLATE SPEC VALIDATION: FAILED\n")
        for e in errors:
            print(" -", e)
        return 1

    print("TEMPLATE SPEC VALIDATION: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
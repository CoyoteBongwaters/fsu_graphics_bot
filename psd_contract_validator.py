from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from template_engine import load_template_map


@dataclass(frozen=True, slots=True)
class PsdContractIssue:
    event_type: str
    manifest_path: Path
    missing_layers: list[str]
    duplicated_layers: list[str]


def _load_manifest_layers(manifest_path: Path) -> list[str]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    layers = data.get("layers")
    if not isinstance(layers, list) or not all(isinstance(x, str) and x.strip() for x in layers):
        raise ValueError("Manifest must define 'layers' as a list of non-empty strings.")
    return layers


def _expected_layers(spec: dict[str, Any]) -> tuple[set[str], list[str]]:
    expected: set[str] = set()
    seen: dict[str, int] = {}

    render_spec = spec.get("render_spec", {}) or {}

    for group in ("text", "images", "toggles"):
        group_map = render_spec.get(group, {}) or {}
        if not isinstance(group_map, dict):
            continue
        for layer in group_map.keys():
            expected.add(layer)
            seen[layer] = seen.get(layer, 0) + 1

    style_spec = spec.get("style_spec", {}) or {}
    for profile in style_spec.values():
        if not isinstance(profile, dict):
            continue
        toggles = profile.get("toggles", {}) or {}
        for layer in toggles.keys():
            expected.add(layer)
            seen[layer] = seen.get(layer, 0) + 1

    duplicated = sorted([k for k, v in seen.items() if v > 1])
    return expected, duplicated


def validate_psd_contracts(repo_root: Path) -> list[PsdContractIssue]:
    templates = load_template_map()
    issues: list[PsdContractIssue] = []

    for event_type, spec in templates.items():
        if not isinstance(spec, dict):
            continue

        if spec.get("render_spec") is None:
            continue

        template_path = spec.get("template_path")
        if not isinstance(template_path, str):
            continue

        manifest_path = (repo_root / template_path).with_suffix(".layer_manifest.json")

        if not manifest_path.exists():
            issues.append(
                PsdContractIssue(
                    event_type=event_type,
                    manifest_path=manifest_path,
                    missing_layers=["<missing manifest>"],
                    duplicated_layers=[],
                )
            )
            continue

        try:
            manifest_layers = set(_load_manifest_layers(manifest_path))
        except Exception as e:
            issues.append(
                PsdContractIssue(
                    event_type=event_type,
                    manifest_path=manifest_path,
                    missing_layers=[f"<invalid manifest: {e}>"],
                    duplicated_layers=[],
                )
            )
            continue

        expected, duplicated = _expected_layers(spec)
        missing = sorted([layer for layer in expected if layer not in manifest_layers])
        extra = sorted([layer for layer in manifest_layers if layer not in expected])

        if missing or extra or duplicated:
            if extra:
                missing.append(f"<manifest has extra layers not referenced by template spec: {', '.join(extra)}>")

            issues.append(
                PsdContractIssue(
                    event_type=event_type,
                    manifest_path=manifest_path,
                    missing_layers=missing,
                    duplicated_layers=duplicated,
                )
            )
            issues.append(
                PsdContractIssue(
                    event_type=event_type,
                    manifest_path=manifest_path,
                    missing_layers=missing,
                    duplicated_layers=duplicated,
                )
            )

    return issues
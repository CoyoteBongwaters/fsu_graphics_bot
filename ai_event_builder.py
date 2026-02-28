from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from template_engine import load_template_map

PROMPT_VERSION = 1


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _run_ollama(model: str, prompt: str) -> str:
    cmd = ["ollama", "run", model, prompt]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            "Ollama failed.\n"
            f"cmd: {' '.join(cmd)}\n"
            f"stdout:\n{res.stdout}\n"
            f"stderr:\n{res.stderr}\n"
        )
    return res.stdout.strip()


def _parse_ai_json(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI output was not valid JSON: {e}\nRaw:\n{text}") from e
    if not isinstance(data, dict):
        raise ValueError("AI output JSON must be an object/dict at the top level.")
    return data


def _enforce_allowlist(payload: dict[str, Any]) -> None:
    allowed = {
        "schema_version",
        "source",
        "headline",
        "event_type",
        "template_key",
        "teams",
        "players",
        "created_at_utc",
        "meta",
        "assets",
        "style_profile",
    }
    extra = sorted(set(payload.keys()) - allowed)
    if extra:
        raise ValueError(f"AI output contained disallowed top-level keys: {extra}")


def _sanitize_meta(payload: dict[str, Any]) -> None:
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return

    allowed_meta_keys = {"ai", "image_query"}
    for k in list(meta.keys()):
        if k not in allowed_meta_keys:
            del meta[k]


def _validate_meta(payload: dict[str, Any]) -> None:
    meta = payload.get("meta")
    if meta is None:
        return
    if not isinstance(meta, dict):
        raise ValueError("meta must be an object/dict")

    allowed_meta_keys = {"ai", "image_query"}
    extra = sorted(set(meta.keys()) - allowed_meta_keys)
    if extra:
        raise ValueError(f"Disallowed meta keys: {extra}")

    if "image_query" in meta:
        if not isinstance(meta["image_query"], str):
            raise ValueError("meta.image_query must be a string")
        if not meta["image_query"].strip():
            raise ValueError("meta.image_query cannot be empty")


def _ensure_breaking_news_image_query(payload: dict[str, Any]) -> None:
    if payload.get("event_type") != "breaking_news":
        return

    meta = payload.get("meta")
    if meta is None:
        meta = {}
        payload["meta"] = meta

    if isinstance(meta.get("image_query"), str) and meta["image_query"].strip():
        return

    meta["image_query"] = payload["headline"].strip()


def _validate_event_payload(payload: dict[str, Any]) -> None:
    required = [
        "schema_version",
        "source",
        "headline",
        "event_type",
        "template_key",
        "teams",
        "players",
        "created_at_utc",
    ]
    for k in required:
        if k not in payload:
            raise ValueError(f"Missing required field: {k}")
        if isinstance(payload[k], str) and not payload[k].strip():
            raise ValueError(f"Required field '{k}' is empty")

    if payload["schema_version"] != 1:
        raise ValueError("schema_version must be 1")

    if not isinstance(payload["teams"], list) or not all(isinstance(x, str) for x in payload["teams"]):
        raise ValueError("teams must be a list[str]")
    if not isinstance(payload["players"], list) or not all(isinstance(x, str) for x in payload["players"]):
        raise ValueError("players must be a list[str]")

    templates = load_template_map()
    key = str(payload["template_key"]).strip()
    if key not in templates:
        raise ValueError(f"Unknown template_key: {key!r} (not in template_map.json)")

    try:
        datetime.fromisoformat(payload["created_at_utc"])
    except Exception as e:
        raise ValueError(f"created_at_utc must be ISO-8601 parseable: {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--headline", required=True, help="Raw headline text.")
    ap.add_argument("--template-key", required=True, help="Must exist in template_map.json.")
    ap.add_argument("--event-type", required=True, help="e.g. result, breaking_news, transfer, commit")
    ap.add_argument("--model", default="qwen2.5:7b", help="Ollama model name (must be installed).")
    ap.add_argument("--out", default="out/json/ai", help="Output directory for generated event JSON.")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    base_payload = {
        "schema_version": 1,
        "source": "ai",
        "headline": args.headline,
        "event_type": args.event_type,
        "template_key": args.template_key,
        "teams": [],
        "players": [],
        "created_at_utc": _utc_now_iso(),
        "meta": {
            "ai": {
                "provider": "ollama",
                "model": args.model,
                "prompt_version": PROMPT_VERSION,
            }
        },
    }

    prompt = (
        "You are producing ONLY a JSON object for an Event.\n"
        "Hard rules:\n"
        "- Output MUST be valid JSON, nothing else.\n"
        "- Do NOT include render_plan or any operations.\n"
        "- Do NOT change template_key.\n"
        "- Keep schema_version as 1.\n"
        "- If teams/players are unknown, use empty arrays.\n"
        "- For breaking_news you may optionally add meta.image_query (string) describing the image to find later.\n"
        "\n"
        "Given this base event object, fill in teams and players if confidently inferable from the headline.\n"
        "Otherwise leave them empty.\n"
        "\n"
        f"BASE_EVENT_JSON:\n{json.dumps(base_payload, indent=2)}\n"
    )

    raw = _run_ollama(args.model, prompt)
    payload = _parse_ai_json(raw)

    _enforce_allowlist(payload)
    _sanitize_meta(payload)
    _validate_meta(payload)
    _ensure_breaking_news_image_query(payload)

    # enforce authority (never let model override these)
    payload["template_key"] = args.template_key
    payload["event_type"] = args.event_type
    payload["schema_version"] = 1
    payload["source"] = payload.get("source") or "ai"
    payload["created_at_utc"] = payload.get("created_at_utc") or base_payload["created_at_utc"]

    _validate_event_payload(payload)

    ts = datetime.fromisoformat(payload["created_at_utc"]).strftime("%Y%m%d_%H%M%S")
    safe_key = args.template_key.replace("/", "_")
    out_path = out_dir / f"{ts}_{safe_key}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
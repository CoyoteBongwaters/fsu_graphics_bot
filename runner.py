from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json

from models import Event


@dataclass(slots=True)
class RunResult:
    ok: bool
    psd_path: str | None = None
    png_path: str | None = None
    log_path: str | None = None
    error: str | None = None


class Runner:
    """Execution boundary for applying render_plan to a PSD and exporting outputs."""

    def run(self, event: Event) -> RunResult:  # pragma: no cover
        raise NotImplementedError


class PreviewRunner(Runner):
    """
    No-op runner that writes a log describing what would happen.
    Useful until Photoshop automation is implemented.
    """

    def __init__(self, out_dir: Path | None = None) -> None:
        self.out_dir = out_dir or Path("out") / "psd"

    def run(self, event: Event) -> RunResult:
        self.out_dir.mkdir(parents=True, exist_ok=True)

        # Use a filesystem-safe timestamp (matches out/json naming style)
        from datetime import datetime

        dt = datetime.fromisoformat(event.created_at_utc)
        ts = dt.strftime("%Y%m%d_%H%M%S")
        log_path = self.out_dir / f"{ts}_{event.event_type}_runner_preview.json"

        payload = {
            "template_path": (event.template.template_path if event.template else ""),
            "render_plan": event.render_plan or [],
            "assets": (asdict(event.assets) if event.assets else None),
            "meta": event.meta,
            "style_profile": event.style_profile,
        }

        log_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return RunResult(ok=True, log_path=str(log_path))
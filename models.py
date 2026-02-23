from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class TemplateInfo:
    template_path: str
    notes: str = ""
    template_found: bool = False
    event_type: str = ""
    template_file: str = ""


@dataclass(slots=True)
class AssetPaths:
    logo_primary: str
    logo_secondary: str | None
    headshot: str | None
    player_cutout: str | None
    background: str


@dataclass(slots=True)
class Event:
    source: str
    headline: str
    event_type: str
    teams: list[str]
    players: list[str]
    created_at_utc: str
    template: TemplateInfo | None = None
    assets: AssetPaths | None = None
    meta: dict[str, Any] | None = None
    render_plan: list[dict[str, Any]] | None = None
    style_profile: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "schema_version": 1,
            "source": self.source,
            "headline": self.headline,
            "event_type": self.event_type,
            "teams": self.teams,
            "players": self.players,
            "created_at_utc": self.created_at_utc,
        }
        if self.meta is not None:
            out["meta"] = self.meta
        if self.render_plan is not None:
            out["render_plan"] = self.render_plan
        if self.style_profile is not None:
            out["style_profile"] = self.style_profile        
        if self.template is not None:
            out["template"] = {
                "template_path": self.template.template_path,
                "notes": self.template.notes,
                "template_found": self.template.template_found,
                "event_type": self.template.event_type,
                "template_file": self.template.template_file,
            }

        if self.assets is not None:
            out["assets"] = {
            # New keys (preferred)
            "logo_primary": self.assets.logo_primary,
            "logo_secondary": self.assets.logo_secondary,

            # Backward-compatible alias (old key)
            "logo": self.assets.logo_primary,

            "headshot": self.assets.headshot,
            "player_cutout": self.assets.player_cutout,
            "background": self.assets.background,
        }

        return out
    
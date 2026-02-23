from pathlib import Path

from models import AssetPaths, Event


def resolve_assets(event: Event) -> AssetPaths:
    """Resolve logos/headshots/backgrounds for this event."""
    base = Path("assets")

    # --- Logo selection ---
    teams = event.teams or ["FSU"]
    team_primary = teams[0]
    team_secondary = teams[1] if len(teams) > 1 else None

    logo_primary = base / "logos" / f"{team_primary.lower()}.png"
    if not logo_primary.exists():
        logo_primary = base / "logos" / "default.png"

    logo_secondary = None
    if team_secondary is not None:
        candidate = base / "logos" / f"{team_secondary.lower()}.png"
        logo_secondary = str(candidate) if candidate.exists() else str(base / "logos" / "default.png")

    # --- Headshot selection (fallback) ---
    headshot_path: str | None = None
    if event.players:
        name = event.players[0].replace(" ", "_").lower() + ".jpg"
        candidate = base / "headshots" / name
        if candidate.exists():
            headshot_path = str(candidate)
        else:
            default = base / "headshots" / "default.jpg"
            headshot_path = str(default) if default.exists() else None

    # --- Player cutout selection (preferred modern asset) ---
    # Deterministic lookup:
    # assets/player_cutouts/<team_primary>/<player_slug>.png  (fallback .webp)
    player_cutout_path: str | None = None
    if event.players:
        player_slug = event.players[0].replace(" ", "_").lower()
        team_slug = team_primary.lower()

        png_candidate = base / "player_cutouts" / team_slug / f"{player_slug}.png"
        webp_candidate = base / "player_cutouts" / team_slug / f"{player_slug}.webp"

        if png_candidate.exists():
            player_cutout_path = str(png_candidate)
        elif webp_candidate.exists():
            player_cutout_path = str(webp_candidate)

    # Precedence: if a cutout exists, suppress headshot so we don't emit both.
    if player_cutout_path is not None:
        headshot_path = None

    # --- Background selection ---
    bg_path = base / "backgrounds" / f"{event.event_type}.jpg"
    if not bg_path.exists():
        bg_path = base / "backgrounds" / "generic.jpg"

    return AssetPaths(
        logo_primary=str(logo_primary),
        logo_secondary=logo_secondary,
        headshot=headshot_path,
        player_cutout=player_cutout_path,
        background=str(bg_path),
    )
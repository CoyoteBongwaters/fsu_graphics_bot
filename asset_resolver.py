from pathlib import Path

def resolve_assets(event: dict) -> dict:
    """Find logos, headshots, and backgrounds for this event."""
    base = Path("assets")

    # --- Logo selection ---
    team_id = event["teams"][0]
    logo_path = base / "logos" / f"{team_id.lower()}.png"
    if not logo_path.exists():
        logo_path = base / "logos" / "default.png"

    # --- Headshot selection ---
    players = event.get("players", [])
    if players:
        name = players[0].replace(" ", "_").lower() + ".jpg"
        headshot_path = base / "headshots" / name
    else:
        headshot_path = base / "headshots" / "default.jpg"

    if not headshot_path.exists():
        headshot_path = base / "headshots" / "default.jpg"

    # --- Background selection ---
    bg_path = base / "backgrounds" / f"{event['event_type']}.jpg"
    if not bg_path.exists():
        bg_path = base / "backgrounds" / "generic.jpg"

    event["assets"] = {
        "logo": str(logo_path),
        "headshot": str(headshot_path),
        "background": str(bg_path),
    }

    return event

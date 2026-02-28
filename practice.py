import json  # (json = structured data format)
from datetime import datetime, UTC  # (UTC = timezone constant)
from pathlib import Path  # (Path = safe file paths)
from team_data import TEAM_ALIASES
import re  # add near the top if not already imported
from template_engine import select_template
from asset_resolver import resolve_assets
from models import Event
from typing import Any
from render_plan_engine import build_render_plan
from runner import PreviewRunner

def classify_event(headline: str) -> str:
    h = headline.lower()
    h = h.replace("\u202f", " ")  # normalize weird spaces
    commit_words = ("commit", "commits", "committed", "lands", "pledge", "signs")
    transfer_words = ("transfer portal", "enters the portal", "enters portal",
                      "transfer", "transfers", "joining", "leaves for")
    injury_words = ("out for season", "ruled out", "injury", "injured",
                    "torn acl", "broken", "sidelined")
    result_words = (
    "defeats", "defeat", "beats", "beat", "wins", "win", "final",
    "upsets", "upset", "edges", "edge", "tops", "top",
    "falls to", "loses to", "loss to", "victory", "victorious", "routs", "routed", "dominates", "dominated"
)
    award_words = ("award", "wins award", "named", "player of the year",
                   "earns honor", "receives")
    
    # If the headline contains a score like "45-0" or "45 – 0", it's a result.
    if re.search(r"\b\d{1,3}\s*[-–]\s*\d{1,3}\b", h):
        return "result"
    
    def has_keyword(words: tuple[str, ...]) -> bool:
        """Match either whole words (single tokens) or phrases (substring)."""
        for w in words:
            w = w.lower()
            if " " in w:
                # phrase match (e.g. "falls to", "transfer portal")
                if w in h:
                    return True
            else:
                # whole-word match
                if re.search(rf"\b{re.escape(w)}\b", h):
                    return True
        return False
    
    if has_keyword(commit_words):
        return "commit"
    if has_keyword(transfer_words):
        return "transfer"
    if has_keyword(injury_words):
        return "injury"
    if has_keyword(award_words):
        return "award"
    if has_keyword(result_words):
        return "result"
    return "unknown"
def extract_players(headline: str) -> list[str]:
    """(heuristic = rule-based guess at player names)"""
    raw_words = headline.replace("/", " ").replace("-", " ").split()
    words = [w.strip(".,:;!?()[]{}\"'") for w in raw_words]

    stopwords = {
        "FSU", "Florida", "State", "Seminoles", "Noles",
        "QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB",
        "to", "from", "vs", "at", "in", "of", "the", "a", "an",
        "commit", "commits", "committed",
        "transfer", "transfers", "portal", "enters",
        "out", "ruled", "injury", "injured",
        "wins", "beats", "defeats", "final",
    }

    def is_name_word(w: str) -> bool:
        return w[:1].isupper() and w[1:].islower()

    found: list[str] = []
    i = 0
    while i < len(words) - 1:
        w1, w2 = words[i], words[i + 1]
        if is_name_word(w1) and is_name_word(w2):
            if w1 not in stopwords and w2 not in stopwords:
                found.append(f"{w1} {w2}")
                i += 2
                continue
        i += 1

    # (dedupe = remove duplicates)
    unique = []
    seen = set()
    for name in found:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    # Filter out team names mistakenly caught as players
    from team_data import TEAM_ALIASES  # safe to import here
    team_words = {alias.title() for aliases in TEAM_ALIASES.values() for alias in aliases}

    filtered = []
    for name in unique:
        # Keep the name only if neither word appears in team aliases
        if not any(part in team_words for part in name.split()):
            filtered.append(name)

    return filtered

# (alias = another name for the same thing)


def detect_teams(headline: str) -> list[str]:
    """
    Return a list of team IDs detected in the headline.
    (heuristic = rule-based guess)
    """
    h = headline.lower()

    scores: dict[str, int] = {}  # (score = how strongly a team matched)

    for team_id, aliases in TEAM_ALIASES.items():
        team_score = 0
        for a in aliases:
            if a in h:
                # Longer alias gets more weight (e.g., "florida state" > "fsu")
                team_score += max(1, len(a) // 4)
        if team_score > 0:
            scores[team_id] = team_score

    # Sort teams by score (highest first)
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [team_id for team_id, _score in ordered]

def extract_score(headline: str) -> tuple[int, int] | None:
    """
    Extract a score like '24-7' or '12–0' from the headline.
    Returns (a, b) or None if not found.
    """
    h = headline.replace("\u2013", "-").replace("\u2014", "-")  # normalize en/em dash
    m = re.search(r"\b(\d{1,3})\s*-\s*(\d{1,3})\b", h)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))

def main():
    headline = input("Paste headline: ").strip()
    print("DEBUG practice.py path:", __file__)
    print("DEBUG python:", __import__("sys").executable)
    print("DEBUG result_words contains victory? (manual check)")

    if not headline:
        print("No headline entered. Exiting.")
        return

    event_type = classify_event(headline)
    teams = detect_teams(headline) or ["FSU"]

    meta: dict[str, int | str] = {}

    if event_type == "result":
        score = extract_score(headline)
        if score is not None:
            a, b = score
            meta["score_a"] = a
            meta["score_b"] = b

            team_a = teams[0]
            team_b = teams[1] if len(teams) > 1 else "UNKNOWN"

            meta["team_a"] = team_a
            meta["team_b"] = team_b

            if a > b:
                meta["winner"] = team_a
                meta["loser"] = team_b
                meta["winner_score"] = a
                meta["loser_score"] = b
            elif b > a:
                meta["winner"] = team_b
                meta["loser"] = team_a
                meta["winner_score"] = b
                meta["loser_score"] = a
            else:
                meta["winner"] = "TIE"
                meta["loser"] = "TIE"
                meta["winner_score"] = a
                meta["loser_score"] = b

    style_profile = "default"

    event = Event(
        source="manual",
        headline=headline,
        event_type=event_type,
        template_key=f"fsu.{event_type}",
        teams=teams,
        players=extract_players(headline),
        created_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        meta=meta or None,
        style_profile=style_profile,
    )

    event.template = select_template(event)
    event.assets = resolve_assets(event)
    event.render_plan = build_render_plan(event)
    runner = PreviewRunner()
    run_result = runner.run(event)
    if run_result.log_path:
        print(f"Runner log: {run_result.log_path}")

    base_out = Path("out")
    json_dir = base_out / "json"
    png_dir = base_out / "png"
    psd_dir = base_out / "psd"

    for d in (json_dir, png_dir, psd_dir):
        d.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_path = json_dir / f"{timestamp}_{event_type}.json"

    out_path.write_text(
        json.dumps(event.to_dict(), indent=2),
        encoding="utf-8",
    )

    print(f"Saved: {out_path}")
    data = event.to_dict()
    print(
        f"Summary: event_type={data.get('event_type')} "
        f"teams={data.get('teams')} "
        f"players={data.get('players')}"
    )
def menu():
    """Simple text-based menu loop."""
    while True:
        print("\n" + "-" * 33)
        print("FSU Graphics Bot")
        print("-" * 33)
        print("1) Create new event JSON")
        print("2) List recent JSON files")
        print("3) Exit")
        print("-" * 33)

        choice = input("Select an option (1-3): ").strip()

        if choice == "1":
            main()
        elif choice == "2":
            list_recent_json()
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

def list_recent_json():
    """Display the most recent JSON files."""
    json_dir = Path("out/json")
    if not json_dir.exists():
        print("No output folder found yet.")
        return

    files = sorted(json_dir.glob("*.json"), reverse=True)
    if not files:
        print("No JSON files found.")
        return

    print("\nRecent saved events:")
    for f in files[:5]:  # show only 5 most recent
        print(" -", f.name)
if __name__ == "__main__":
    menu()

import json
from pathlib import Path
from src.scraper import Position

STATE_FILE = Path(__file__).parent.parent / "data" / "state.json"


def load_state() -> dict[str, Position]:
    if not STATE_FILE.exists() or STATE_FILE.stat().st_size == 0:
        return {}
    with open(STATE_FILE, encoding="utf-8-sig") as f:
        data = json.load(f)
    return {k: Position.from_dict(v) for k, v in data.items()}


def save_state(positions: dict[str, Position]) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {k: v.to_dict() for k, v in positions.items()},
            f,
            indent=2,
            ensure_ascii=False,
        )

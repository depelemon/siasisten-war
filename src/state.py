import json
from pathlib import Path
from src.scraper import Position

STATE_FILE = Path(__file__).parent.parent / "data" / "state.json"
COUNTER_FILE = Path(__file__).parent.parent / "data" / "counter.json"
LAST_NOTIF_FILE = Path(__file__).parent.parent / "data" / "last_notification.json"


def load_state() -> dict[str, Position]:
    if not STATE_FILE.exists():
        return {}
    raw = STATE_FILE.read_bytes().strip()
    if not raw:
        return {}
    # Try encodings in order: handles UTF-8 BOM, UTF-16 LE/BE (with or without BOM)
    for enc in ("utf-8-sig", "utf-16", "utf-16-le", "utf-8"):
        try:
            text = raw.decode(enc).strip()
            data = json.loads(text)
            return {k: Position.from_dict(v) for k, v in data.items()}
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise RuntimeError(f"Could not decode {STATE_FILE} — unrecognised encoding or malformed JSON.")


def load_counter() -> int:
    if not COUNTER_FILE.exists():
        return 0
    try:
        return json.loads(COUNTER_FILE.read_text(encoding="utf-8")).get("check_count", 0)
    except Exception:
        return 0


def save_counter(count: int) -> None:
    COUNTER_FILE.parent.mkdir(exist_ok=True)
    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        json.dump({"check_count": count}, f)


def save_state(positions: dict[str, Position]) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {k: v.to_dict() for k, v in positions.items()},
            f,
            indent=2,
            ensure_ascii=False,
        )


def load_last_notification() -> dict | None:
    if not LAST_NOTIF_FILE.exists():
        return None
    try:
        text = LAST_NOTIF_FILE.read_text(encoding="utf-8").strip()
        return json.loads(text) if text else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def save_last_notification(data: dict | None) -> None:
    LAST_NOTIF_FILE.parent.mkdir(exist_ok=True)
    if data is None:
        if LAST_NOTIF_FILE.exists():
            LAST_NOTIF_FILE.unlink()
        return
    with open(LAST_NOTIF_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

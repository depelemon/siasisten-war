import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.scraper import BASE_URL, Position

_EMBED_FIELD_LIMIT = 25
_THUMBNAIL = Path(__file__).parent.parent / "13.png"


def _post(webhook_url: str, payload: dict) -> None:
    if _THUMBNAIL.exists():
        with open(_THUMBNAIL, "rb") as f:
            r = requests.post(
                webhook_url,
                data={"payload_json": json.dumps(payload)},
                files={"files[0]": ("13.png", f, "image/png")},
                timeout=10,
            )
    else:
        r = requests.post(webhook_url, json=payload, timeout=10)
    r.raise_for_status()


def _position_field(p: Position) -> dict:
    link = f"{BASE_URL}{p.apply_url}" if p.apply_url else f"{BASE_URL}/lowongan/listLowongan/"
    value = (
        f"**Dosen:** {p.dosen}\n"
        f"**Slots:** {p.slots}\n"
        f"**Pelamar:** {p.applicants}\n"
        f"[Daftar sekarang]({link})"
    )
    return {"name": p.course[:256], "value": value[:1024], "inline": False}


def send_new_positions(positions: list[Position], webhook_url: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    total = len(positions)

    for batch_start in range(0, total, _EMBED_FIELD_LIMIT):
        batch = positions[batch_start : batch_start + _EMBED_FIELD_LIMIT]
        title = (
            f"🍋 {total} lowongan baru dibuka!"
            if batch_start == 0
            else f"🍋 Lowongan baru (lanjutan {batch_start + 1}–{batch_start + len(batch)})"
        )
        payload = {
            "content": "@everyone",
            "embeds": [
                {
                    "title": title,
                    "thumbnail": {"url": "attachment://13.png"},
                    "color": 0xE74C3C,
                    "fields": [_position_field(p) for p in batch],
                    "footer": {"text": "siasisten.cs.ui.ac.id"},
                    "timestamp": now,
                }
            ]
        }
        _post(webhook_url, payload)


def send_no_changes(total_tracked: int, webhook_url: str) -> None:
    payload = {
        "embeds": [
            {
                "title": "🍋 Tidak ada lowongan baru.",
                "thumbnail": {"url": "attachment://13.png"},
                "description": f"Tidak ada perubahan. {total_tracked} posisi sedang dipantau.",
                "color": 0x2ECC71,
                "footer": {"text": "siasisten.cs.ui.ac.id"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }
    _post(webhook_url, payload)


def send_error(webhook_url: str, message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    try:
        payload = {
            "embeds": [
                {
                    "title": "⚠️ SiasistenWar — Error",
                    "description": message[:2048],
                    "color": 0xFF8C00,
                    "footer": {"text": "siasisten.cs.ui.ac.id"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception:
        pass

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.scraper import BASE_URL, Position

_EMBED_FIELD_LIMIT = 25
_THUMBNAILS_DIR = Path(__file__).parent.parent / "thumbnails"
_ROSSI_IMAGE = Path(__file__).parent.parent / "images" / "rossi2.jpeg"


def _pick_thumbnail() -> Path | None:
    images = list(_THUMBNAILS_DIR.glob("*.png"))
    return random.choice(images) if images else None


def _post(webhook_url: str, payload: dict, image: Path | None = None) -> None:
    thumb = _pick_thumbnail()
    use_image = image is not None and image.exists()

    if thumb:
        for embed in payload.get("embeds", []):
            embed["thumbnail"] = {"url": f"attachment://{thumb.name}"}
    if use_image:
        for embed in payload.get("embeds", []):
            embed["image"] = {"url": f"attachment://{image.name}"}

    if not thumb and not use_image:
        r = requests.post(webhook_url, json=payload, timeout=10)
    else:
        opens = []
        try:
            files = {}
            if thumb:
                f = open(thumb, "rb")
                opens.append(f)
                files["files[0]"] = (thumb.name, f, "image/png")
            if use_image:
                img = open(image, "rb")
                opens.append(img)
                idx = len(files)
                files[f"files[{idx}]"] = (image.name, img, "image/jpeg")
            r = requests.post(
                webhook_url,
                data={"payload_json": json.dumps(payload)},
                files=files,
                timeout=10,
            )
        finally:
            for fh in opens:
                fh.close()

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


def send_new_positions(positions: list[Position], webhook_url: str, check_count: int = 0) -> None:
    now = datetime.now(timezone.utc).isoformat()
    total = len(positions)

    for batch_start in range(0, total, _EMBED_FIELD_LIMIT):
        batch = positions[batch_start : batch_start + _EMBED_FIELD_LIMIT]
        title = (
            f"<:rossi:1518863461994725386> {total} lowongan baru dibuka, Endministrator!"
            if batch_start == 0
            else f"<:rossi:1518863461994725386> Lowongan baru (lanjutan {batch_start + 1}–{batch_start + len(batch)})"
        )
        payload = {
            "content": "@everyone",
            "embeds": [
                {
                    "title": title,
                    "color": 0xE74C3C,
                    "fields": [_position_field(p) for p in batch],
                    "footer": {"text": f"siasisten.cs.ui.ac.id • Check #{check_count}"},
                    "timestamp": now,
                }
            ]
        }
        _post(webhook_url, payload, image=_ROSSI_IMAGE)


def send_no_changes(total_tracked: int, webhook_url: str, check_count: int = 0) -> None:
    payload = {
        "embeds": [
            {
                "title": "<:rossi:1518863461994725386> Tidak ada lowongan baru, Endministrator!",
                "description": f"{total_tracked} posisi tercatat.",
                "color": 0x2ECC71,
                "footer": {"text": f"siasisten.cs.ui.ac.id • Check #{check_count}"},
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
        _post(webhook_url, payload)
    except Exception:
        pass

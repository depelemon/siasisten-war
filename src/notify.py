import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from src.scraper import BASE_URL, Position

_EMBED_FIELD_LIMIT = 25
_THUMBNAILS_DIR = Path(__file__).parent.parent / "thumbnails"
_ROSSI_IMAGE = Path(__file__).parent.parent / "images" / "rossi2.png"


def _pick_thumbnail() -> Path | None:
    images = list(_THUMBNAILS_DIR.glob("*.png"))
    return random.choice(images) if images else None


def _post(webhook_url: str, payload: dict, image: Path | None = None) -> dict | None:
    thumb = _pick_thumbnail()
    use_image = image is not None and image.exists()

    if thumb:
        for embed in payload.get("embeds", []):
            embed["thumbnail"] = {"url": f"attachment://{thumb.name}"}
    if use_image:
        for embed in payload.get("embeds", []):
            embed["image"] = {"url": f"attachment://{image.name}"}

    params = {"wait": "true"}
    if not thumb and not use_image:
        r = requests.post(webhook_url, params=params, json=payload, timeout=10)
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
                params=params,
                data={"payload_json": json.dumps(payload)},
                files=files,
                timeout=10,
            )
        finally:
            for fh in opens:
                fh.close()

    r.raise_for_status()
    return r.json() if r.content else None


def _edit(webhook_url: str, message_id: str, payload: dict) -> None:
    r = requests.patch(f"{webhook_url}/messages/{message_id}", json=payload, timeout=10)
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


def send_new_positions(
    positions: list[Position],
    webhook_url: str,
    check_count: int = 0,
    last_notif: dict | None = None,
) -> dict | None:
    """
    Sends a Discord notification for newly opened positions.

    Checks run every 5 minutes, so two courses that open a few minutes apart
    land in separate checks. If the immediately preceding check (check_count - 1)
    already posted a notification with room left, this edits that same message
    to add the new courses instead of posting a fresh one — so a burst of
    openings across consecutive checks still reads as a single notification.

    Returns metadata to persist and pass back in on the next call (or None if
    the message can no longer be extended, e.g. it's already full).
    """
    now = datetime.now(timezone.utc).isoformat()

    can_extend = (
        last_notif is not None
        and last_notif.get("check_count") == check_count - 1
        and len(last_notif.get("positions", [])) + len(positions) <= _EMBED_FIELD_LIMIT
    )

    if can_extend:
        combined = [Position.from_dict(d) for d in last_notif["positions"]] + positions
        payload = {
            "embeds": [
                {
                    "title": f"<:rossi:1518863461994725386> {len(combined)} lowongan baru dibuka, Endministrator!",
                    "color": 0xE74C3C,
                    "fields": [_position_field(p) for p in combined],
                    "footer": {"text": f"siasisten.cs.ui.ac.id • Check #{check_count}"},
                    "timestamp": now,
                }
            ]
        }
        _edit(webhook_url, last_notif["message_id"], payload)
        return {
            "message_id": last_notif["message_id"],
            "check_count": check_count,
            "positions": [p.to_dict() for p in combined],
        }

    total = len(positions)
    first_batch_result: dict | None = None
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
        resp = _post(webhook_url, payload, image=_ROSSI_IMAGE)
        if batch_start == 0 and resp:
            first_batch_result = {
                "message_id": resp["id"],
                "check_count": check_count,
                "positions": [p.to_dict() for p in batch],
            }

    # Only track the first message for future edits; if there were more than
    # one batch (>25 new positions in a single check), don't try to extend it.
    return first_batch_result if total <= _EMBED_FIELD_LIMIT else None


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

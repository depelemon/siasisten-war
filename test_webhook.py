import json
import random
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from src.scraper import BASE_URL, Position

load_dotenv()

_THUMBNAILS_DIR = Path("thumbnails")
_ROSSI_IMAGE = Path("images") / "rossi2.png"

DUMMY_POSITION = Position(
    id="test-001",
    term="Ganjil 2026/2027",
    course="CSGE676767 - 01.00.12.01-2020 - Ilmu AIC",
    dosen="Dr. Endministrator",
    status="Dibuka",
    can_apply=True,
    slots="3",
    applicants="7",
    accepted="0",
    apply_url="/lowongan/daftarLowongan/9999/",
)


def _pick_thumbnail() -> Path | None:
    images = list(_THUMBNAILS_DIR.glob("*.png"))
    return random.choice(images) if images else None


def _position_field(p: Position) -> dict:
    link = f"{BASE_URL}{p.apply_url}" if p.apply_url else f"{BASE_URL}/lowongan/listLowongan/"
    value = (
        f"**Dosen:** {p.dosen}\n"
        f"**Slots:** {p.slots}\n"
        f"**Pelamar:** {p.applicants}\n"
        f"[Daftar sekarang]({link})"
    )
    return {"name": p.course[:256], "value": value[:1024], "inline": False}


positions = [DUMMY_POSITION]
total = len(positions)
now = datetime.now(timezone.utc).isoformat()

payload = {
    "content": "<@541947066172178432>",
    "embeds": [
        {
            "title": f"<:rossi:1518863461994725386> {total} lowongan baru dibuka, Endministrator!",
            "color": 0xE74C3C,
            "fields": [_position_field(p) for p in positions],
            "footer": {"text": "siasisten.cs.ui.ac.id • Check #000"},
            "timestamp": now,
        }
    ],
}

thumb = _pick_thumbnail()
use_image = _ROSSI_IMAGE.exists()

if thumb:
    for embed in payload["embeds"]:
        embed["thumbnail"] = {"url": f"attachment://{thumb.name}"}
if use_image:
    for embed in payload["embeds"]:
        embed["image"] = {"url": f"attachment://{_ROSSI_IMAGE.name}"}

opens = []
try:
    files = {}
    if thumb:
        f = open(thumb, "rb")
        opens.append(f)
        files["files[0]"] = (thumb.name, f, "image/png")
    if use_image:
        img = open(_ROSSI_IMAGE, "rb")
        opens.append(img)
        idx = len(files)
        files[f"files[{idx}]"] = (_ROSSI_IMAGE.name, img, "image/jpeg")

    if files:
        r = requests.post(
            os.environ["DISCORD_WEBHOOK_URL"],
            data={"payload_json": json.dumps(payload)},
            files=files,
            timeout=10,
        )
    else:
        r = requests.post(os.environ["DISCORD_WEBHOOK_URL"], json=payload, timeout=10)
finally:
    for fh in opens:
        fh.close()

r.raise_for_status()
print(f"sent! (thumbnail: {thumb.name if thumb else 'none'})")

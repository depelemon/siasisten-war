import json
import random
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

thumb = random.choice(list(Path("thumbnails").glob("*.png")))

payload = {
    "content": "<@541947066172178432>",
    "embeds": [
        {
            "title": "🍋 Test.",
            "thumbnail": {"url": f"attachment://{thumb.name}"},
            "color": 0x2ECC71,
            "footer": {"text": "siasisten.cs.ui.ac.id • Check #42"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "description": "Test description. <@541947066172178432>",
        }
    ],
}

with open(thumb, "rb") as f:
    r = requests.post(
        os.environ["DISCORD_WEBHOOK_URL"],
        data={"payload_json": json.dumps(payload)},
        files={"files[0]": (thumb.name, f, "image/png")},
        timeout=10,
    )

r.raise_for_status()
print(f"sent! (thumbnail: {thumb.name})")

import requests, os, json
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

payload = {
    "content": "<@541947066172178432>",
    "embeds": [
        {
            "title": "🍋 Test.",
            "thumbnail": {"url": "attachment://13.png"},
            "color": 0x2ECC71,
            "footer": {"text": "siasisten.cs.ui.ac.id"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "description": "Test description. <@541947066172178432>",
        }
    ]
}

with open("13.png", "rb") as f:
    r = requests.post(
        os.environ["DISCORD_WEBHOOK_URL"],
        data={"payload_json": json.dumps(payload)},
        files={"files[0]": ("13.png", f, "image/png")},
        timeout=10,
    )

r.raise_for_status()
print("sent!")

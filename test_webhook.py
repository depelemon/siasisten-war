import requests, os
from dotenv import load_dotenv
load_dotenv()

requests.post(os.environ["DISCORD_WEBHOOK_URL"], json={
    "content": "test emote: <:rossi:1518863461994725386>"
}).raise_for_status()
print("sent!")

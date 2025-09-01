import os
import re
import threading

# ---- LILLE WEBSERVER (holder Render "awake") ----
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Wow Tuning Bot is running ✅"

def run_web():
    # Render stiller en PORT-miljøvariabel til rådighed
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Start Flask i en baggrundstråd, så Discord-klienten kan køre samtidig
threading.Thread(target=run_web, daemon=True).start()


# ---- DISCORD BOT ----
import discord

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN mangler som environment variable.")

# === UDFYLD DISSE ===
SOURCE_CHANNEL_IDS = [
    1411990677046427679,  # <- ID for #wowhead-blue-tracker
    1411990706402365440,  # <- ID for #wowhead-news-tracker
]
ALERT_CHANNEL_ID = 1411985043898765436  # <- ID for #class-tuning-alerts
USER_ID = 444444444444444444  # <- (valgfri) dit user ID for DM (0 = slået fra)

KEYWORDS = ["tuning", "class tuning", "class changes"]

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

# simpel dupe-guard pr. proceskørsel
seen_ids = set()


def matches(text: str) -> bool:
    """Returner True hvis en af KEYWORDS forekommer i teksten (case-insensitive)."""
    t = (text or "").lower()
    return any(k in t for k in KEYWORDS)


def sanitize(text: str) -> str:
    """Neutraliser @everyone/@here så vi ikke pinger utilsigtet."""
    return text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")


@client.event
async def on_ready():
    print(f"{client.user} er online og lytter!")


@client.event
async def on_message(message: discord.Message):
    # ignorér egne beskeder og alt uden for kildekanaler
    if message.author == client.user:
        return
    if message.channel.id not in SOURCE_CHANNEL_IDS:
        return
    if message.id in seen_ids:
        return
    seen_ids.add(message.id)

    # tekst + evt. første link
    raw = message.content or ""
    first_link = None
    m = re.search(r"(https?://\S+)", raw)
    if m:
        first_link = m.group(1)

    # embed-titel/URL (Wowhead plejer at sende embeds)
    title = None
    url = None
    if message.embeds:
        e = message.embeds[0]
        title = e.title
        url = e.url

    # tjek keywords på kombi af tekst + embed-titel
    if not matches(raw + " " + (title or "")):
        return

    parts = ["🔔 **Class tuning-nyhed fundet**"]
    if title:
        parts.append(f"**{title}**")
    if url:
        parts.append(url)
    elif first_link:
        parts.append(first_link)

    parts.append(f"🔗 Kilde: {message.jump_url}")

    out = sanitize("\n\n".join(p for p in parts if p))

    # post i alert-kanalen
    alert_ch = client.get_channel(ALERT_CHANNEL_ID)
    if alert_ch:
        await alert_ch.send(out)

    # valgfri DM til dig
    if USER_ID:
        try:
            user = await client.fetch_user(USER_ID)
            await user.send(out)
        except Exception:
            # DM kan fejle hvis du ikke kan modtage beskeder fra bots/denne server
            pass


if __name__ == "__main__":
    client.run(TOKEN)

from fastmcp import FastMCP
import os
import requests
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

mcp = FastMCP("discord")

@mcp.tool()
def send_message(message: str, username: str = "MCP Test Bot"):
    """Send a message to a Discord channel via webhook"""
    if not DISCORD_WEBHOOK_URL:
        return "DISCORD_WEBHOOK_URL not set in .env"
    payload = {"content": message, "username": username}
    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if resp.status_code == 204:
        return f"Message sent to Discord: {message}"
    else:
        return f"Failed to send message. Status: {resp.status_code}, Body: {resp.text}"

@mcp.tool()
def send_embed(title: str, description: str):
    """Send an embedded message to a Discord channel"""
    if not DISCORD_WEBHOOK_URL:
        return "DISCORD_WEBHOOK_URL not set in .env"
    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": 5814783
        }]
    }
    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if resp.status_code == 204:
        return f"Embed sent to Discord: {title}"
    else:
        return f"Failed to send embed. Status: {resp.status_code}, Body: {resp.text}"

@mcp.tool()
def get_recent_messages(limit: int = 5):
    """Fetch recent messages from the Discord channel"""
    if not DISCORD_BOT_TOKEN:
        return "DISCORD_BOT_TOKEN not set in .env"

    DISCORD_CHANNEL_ID = "1421576822478340106"
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages?limit={limit}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        return f"Failed to fetch messages. Status: {resp.status_code}, Body: {resp.text}"


if __name__ == "__main__":
    mcp.run(transport="stdio")

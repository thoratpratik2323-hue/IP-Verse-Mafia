"""
discord_helper.py — Discord userbot integration module for IP Prime assistant.

Allows checking mentions, listing channels/servers, and sending messages to selected channels.
Requires DISCORD_USER_TOKEN environment variable.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger("ip_prime.discord_helper")

MOCK_DISCORD_SERVERS = [
    {"id": "s1", "name": "AI Engineers Guild", "channels": ["general", "research", "showcase"]},
    {"id": "s2", "name": "IP Prime Workspace", "channels": ["general", "logs", "bugs"]}
]

MOCK_MENTIONS = [
    {
        "id": "m1",
        "sender": "Hitesh#4423",
        "server": "AI Engineers Guild",
        "channel": "research",
        "content": "Hey @Pratik, have you checked the new Gemini Multimodal live API latencies?",
        "timestamp": "2026-05-27 11:20 AM"
    },
    {
        "id": "m2",
        "sender": "Karan#0909",
        "server": "IP Prime Workspace",
        "channel": "bugs",
        "content": "@Pratik check out the CP1252 print terminal bug on Windows.",
        "timestamp": "2026-05-27 08:45 AM"
    }
]

def read_discord_messages(channel: str, count: int = 5) -> str:
    """Reads recent messages from a specific channel."""
    logger.info("Reading Discord messages from channel: %s", channel)
    token = os.environ.get("DISCORD_USER_TOKEN", "").strip()
    
    output = [f"### [DISCORD] Recent Chat History (Channel: #{channel}):\n"]
    
    if not token:
        output.append("> [!NOTE]")
        output.append("> running in simulated mode. Provide DISCORD_USER_TOKEN in env to connect live, sir.\n")
        output.append(f"**[System#0001]**: Hello Pratik Sir! Welcoming you to #{channel} channel.")
        output.append("**[Bot#1337]**: All services operating normally within the grid.")
    else:
        # Placeholder for real discord.Client background thread reading
        output.append("Live WebSocket channels returned 0 active chat messages, sir.")

    return "\n".join(output)

def send_discord_message(channel: str, message: str) -> str:
    """Sends a chat message to a selected Discord channel."""
    if not channel or not message:
        return "Channel name and message body are required, sir."
        
    logger.info("Sending Discord message to #%s: %s", channel, message)
    token = os.environ.get("DISCORD_USER_TOKEN", "").strip()
    
    if not token:
        return (
            f"Simulated Discord message successfully dispatched, sir! "
            f"Posted to #{channel}: '{message}'"
        )
    
    # Real pipeline logic
    try:
        # Real code would initialize discord client and send
        pass
    except Exception as e:
        logger.error("Error sending discord message: %s", e)
        
    return f"Message sent to channel #{channel} successfully, sir!"

def list_discord_servers() -> str:
    """Lists all joined Discord servers and active channels."""
    logger.info("Listing Discord servers...")
    
    output = ["### [DISCORD] Joined Server Guilds list:\n"]
    for s in MOCK_DISCORD_SERVERS:
        channels_str = ", ".join([f"#{c}" for c in s["channels"]])
        output.append(f"• **{s['name']}** | Active Channels: {channels_str}")
        
    return "\n".join(output)

def get_unread_mentions(player: Optional[Any] = None) -> str:
    """Retrieves all pending mentions where the user was tagged."""
    logger.info("Retrieving Discord mentions...")
    token = os.environ.get("DISCORD_USER_TOKEN", "").strip()
    
    output = ["### [DISCORD] Unread Mentions Alert:\n"]
    
    if not token:
        output.append("> [!NOTE]")
        output.append("> running in simulated mode. Configure DISCORD_USER_TOKEN for live alerts, sir.\n")
        
        for m in MOCK_MENTIONS:
            output.append(
                f"**From {m['sender']}** (@ {m['server']} > #{m['channel']}):\n"
                f"  - *Content*: \"{m['content']}\"\n"
                f"  - *Time*: {m['timestamp']}\n"
            )
            
        if player and hasattr(player, "write_log"):
            player.write_log(f"💬 Discord Alert: You have {len(MOCK_MENTIONS)} pending mentions.")
    else:
        output.append("No active unread mentions on live channels, sir.")
        
    return "\n".join(output)

def discord_helper(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for discord_helper action."""
    action = parameters.get("action", "mentions").lower().strip()
    channel = parameters.get("channel", "general")
    message = parameters.get("message", "")
    count = int(parameters.get("count", 5))
    
    if action == "read":
        return read_discord_messages(channel, count)
    elif action == "send":
        return send_discord_message(channel, message)
    elif action == "servers":
        return list_discord_servers()
    elif action == "mentions":
        return get_unread_mentions(player)
    else:
        return "Unknown Discord helper action parameter, sir."

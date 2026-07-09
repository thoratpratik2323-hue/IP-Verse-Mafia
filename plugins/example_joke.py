"""
plugins/example_joke.py — Example IP Prime Plugin.
Demonstrates the plugin format. Drop any .py file in plugins/ folder
and IP Prime will auto-load it — no restart needed.

Required attributes:
  TOOL_NAME        : str   — Unique tool name (used in AI function calls)
  TOOL_DESCRIPTION : str   — What this tool does
  TOOL_SCHEMA      : dict  — JSON schema for the tool's parameters
  execute(args)    : func  — Called with args dict, returns str result
"""

TOOL_NAME = "tell_joke"
TOOL_DESCRIPTION = "Tell a random programmer joke in Hinglish to make Pratik laugh."
TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "description": "Joke category: programming | life | ai",
            "enum": ["programming", "life", "ai"]
        }
    },
    "required": []
}

import random

_JOKES = {
    "programming": [
        "Bhai, ek programmer apni girlfriend ko bola — 'Jaa market se ek litre doodh le aao, agar anday mile toh 6 le aana.' Woh 6 litre doodh le aayi. 😂",
        "Why do programmers prefer dark mode? Bhai, kyunki light attracts bugs! 🐛",
        "Ek junior developer ne senior se pucha — 'Bhai recursion kya hai?' Senior ne bola — 'Pehle recursion samjho, fir poochna.' 🤣",
    ],
    "life": [
        "Pratik bhai, deadline aane se pehle sab code kaam karta hai. Deadline ke baad... code bhi ro deta hai. 😭",
        "Sleep deprivation aur coffee — programmers ki official diet hai. 💀☕",
    ],
    "ai": [
        "ChatGPT: 'Main galat ho sakta hoon.' // Bhai, yeh toh main bhi bol sakta hoon, lekin phir bhi Google mujhe trust karta hai. 😎",
        "AI researcher: 'Maine ek sentient AI banaya!' Boss: 'Kya woh meetings attend kar sakta hai?' AI: '...please mujhe off karo.' 🤖",
    ]
}


def execute(args: dict) -> str:
    category = args.get("category", "programming")
    jokes = _JOKES.get(category, _JOKES["programming"])
    return f"😄 {random.choice(jokes)}"

"""Random family-friendly welcome lines for IP Prime (Hinglish)."""
from __future__ import annotations

import random

WELCOMES: list[str] = [
    "Namaste Pratik Sir! Main IP Prime hoon — aapki family ke liye bhi ready hoon. Aaj kya plan hai?",
    "Pratik Sir, welcome! Main IP Prime — ghar walon ke saamne bhi kaam aata hoon. Boliye, kya help chahiye?",
    "Hello Pratik Sir! IP Prime online hai — seedha, simple, aur family-friendly. Main sun raha hoon.",
    "Pratik Sir, namaste! Aaj main aapke saath hoon — recipes se lekar reminders tak, sab ho jayega.",
    "Welcome back Pratik Sir! IP Prime ready hai — thoda smart, thoda warm, bilkul aapke style mein.",
    "Pratik Sir, main IP Prime! Ghar par sab comfortable rahein — main quietly help karunga.",
    "Namaste! IP Prime yahan hai Pratik Sir — aaj ka din smooth banate hain, ek saath.",
    "Pratik Sir, good to see you! Main IP Prime — Hindi-English dono mein comfortable hoon. Command dijiye.",
    "Hello Sir! IP Prime activate — family ke liye bhi polite aur helpful mode on hai.",
    "Pratik Sir, welcome! Chahe homework help ho ya daily tasks — main tayyar hoon.",
    "Namaste Pratik Sir! IP Prime reporting — aaj koi bhi kaam ho, step-by-step solve karenge.",
    "Pratik Sir, main hoon IP Prime — warm welcome! Boliye, aaj kis cheez mein haath batana hai?",
    "Welcome Pratik Sir! IP Prime sun raha hai — simple language, clear answers, no drama.",
    "Pratik Sir, namaste! Ghar wale bhi sun sakte hain — main respectful aur helpful rahunga.",
    "Hello Pratik Sir! IP Prime online — aaj thoda productive, thoda relaxed, jaisa aap bolein.",
    "Pratik Sir, welcome back! Main IP Prime — calendar, messages, search, sab ek jagah.",
    "Namaste Sir! IP Prime yahan hai — family-friendly assistant, seedha jawab, pyara tone.",
    "Pratik Sir, good day! IP Prime ready — koi bhi sawaal ho, calmly solve karte hain.",
    "Welcome Pratik Sir! Main IP Prime hoon — aapki personal help, har din thodi better.",
    "Pratik Sir, namaste! IP Prime activate — suniye, main aapke instructions follow karunga.",
]


def pick_welcome() -> str:
    return random.choice(WELCOMES)

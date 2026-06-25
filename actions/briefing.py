import datetime
import requests
from actions.search import web_search

def get_morning_briefing(city: str = "Malegaon") -> str:
    """
    Assembles a morning briefing containing date, time, weather, and top news headlines.
    """
    now = datetime.datetime.now()
    day = now.strftime("%A, %d %B %Y")
    time_str = now.strftime("%I:%M %p")

    # Weather (free API - no key needed)
    try:
        # wttr.in format=3 returns: "Malegaon: 🌤️ +32°C"
        weather_url = f"https://wttr.in/{city}?format=3"
        weather = requests.get(weather_url, timeout=5).text.strip()
    except Exception as e:
        print(f"[Briefing] Weather error: {e}")
        weather = "Weather unavailable"

    # News headlines
    try:
        news = web_search("India top news today", max_results=2)
    except Exception as e:
        print(f"[Briefing] News error: {e}")
        news = "News unavailable"

    briefing = f"""
Good morning! Aaj {day} hai, time hai {time_str}.

🌤️ Weather: {weather}

📰 Aaj ki khabar:
{news}

SATURDAY ready hai — bolo kya karna hai aaj!
"""
    return briefing.strip()

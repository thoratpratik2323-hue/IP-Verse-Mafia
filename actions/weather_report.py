"""
weather_report.py — Fetches current weather logs from direct wttr.in endpoints.

This is a standard action module for the IP Prime personal assistant suite.
"""

import webbrowser
import urllib.request
from urllib.parse import quote_plus


def weather_action(
    parameters: dict,
    player=None,
    session_memory=None,
) -> str:
    city     = parameters.get("city")
    when     = parameters.get("time", "today")  
    open_browser = parameters.get("open_browser", False)

    if not city or not isinstance(city, str) or not city.strip():
        city = "Ukkalgaon"

    city = city.strip()
    when = (when or "today").strip()

    if open_browser:
        search_query  = f"weather in {city} {when}"
        url           = f"https://www.google.com/search?q={quote_plus(search_query)}"

        try:
            opened = webbrowser.open(url)
            if not opened:
                raise RuntimeError("webbrowser.open returned False")
        except Exception as e:
            msg = f"Sir, I couldn't open the browser for the weather report: {e}"
            _log(msg, player)
            return msg

        msg = f"Showing the weather for {city}, {when}, sir."
        _log(msg, player)

        if session_memory:
            try:
                session_memory.set_last_search(query=search_query, response=msg)
            except Exception:
                pass

        return msg
    else:
        # Silent text-based forecast from wttr.in
        try:
            url = f"http://wttr.in/{quote_plus(city)}?format=3"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                weather_info = response.read().decode("utf-8").strip()
            msg = f"Weather Update for {city}: {weather_info}"
            _log(msg, player)
            return msg
        except Exception as e:
            msg = f"Could not fetch weather data for {city} from wttr.in: {e}"
            _log(msg, player)
            return msg


def _log(message: str, player=None) -> None:
    print(f"[Weather] {message}")
    if player:
        try:
            player.write_log(f"IP PRIME: {message}")
        except Exception:
            pass
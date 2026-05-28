import asyncio
import os
import traceback

def _get_api_key():
    import json
    with open("config/api_keys.json") as f:
        return json.load(f).get("gemini_api_key")

async def test():
    from google import genai
    print("Testing connection...")
    try:
        client = genai.Client(api_key=_get_api_key(), http_options={"api_version": "v1beta"})
        # Using the same LIVE_MODEL from main.py if possible, let's just use the hardcoded one
        LIVE_MODEL = "gemini-2.5-flash-native-audio-latest"
        config = {}
        async with client.aio.live.connect(model=LIVE_MODEL, config=config) as session:
            print("Connected successfully!")
    except Exception as e:
        print(f"Exception: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())

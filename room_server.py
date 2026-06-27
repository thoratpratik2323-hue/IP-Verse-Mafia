"""
room_server.py — Saturday AI Room Token Server
Generates LiveKit access tokens and serves the mobile-friendly voice room UI.
Run: python room_server.py
Then open http://YOUR_PC_IP:8765 on your phone (same WiFi).
"""
import os
import uuid
import socket
import logging
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

load_dotenv()

# Try importing LiveKit token generation
try:
    from livekit.api import AccessToken, VideoGrants
    LIVEKIT_SDK = True
except ImportError:
    try:
        from livekit import AccessToken, VideoGrants
        LIVEKIT_SDK = True
    except ImportError:
        LIVEKIT_SDK = False

# Fallback: manual JWT generation if SDK not available
import jwt as pyjwt
import time

app = Flask(__name__, static_folder=".")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("saturday.room_server")

LIVEKIT_URL    = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY    = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
ROOM_NAME = "saturday-ai-room"


def generate_token_manual(identity: str, room: str) -> str:
    """Generate a LiveKit JWT token manually using PyJWT."""
    now = int(time.time())
    payload = {
        "iss": LIVEKIT_API_KEY,
        "sub": identity,
        "iat": now,
        "exp": now + 3600,  # 1 hour
        "nbf": now,
        "jti": str(uuid.uuid4()),
        "video": {
            "room": room,
            "roomJoin": True,
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True,
        }
    }
    token = pyjwt.encode(payload, LIVEKIT_API_SECRET, algorithm="HS256")
    return token if isinstance(token, str) else token.decode("utf-8")


def generate_token(identity: str, room: str) -> str:
    """Generate LiveKit access token using SDK or manual JWT fallback."""
    if LIVEKIT_SDK:
        try:
            token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            token.with_identity(identity)
            token.with_name(identity)
            token.with_grants(VideoGrants(
                room_join=True,
                room=room,
                can_publish=True,
                can_subscribe=True,
            ))
            return token.to_jwt()
        except Exception as e:
            logger.warning(f"SDK token generation failed, using manual: {e}")
    return generate_token_manual(identity, room)


@app.route("/token")
def get_token():
    """Generate and return a LiveKit access token."""
    identity = request.args.get("identity", f"user-{uuid.uuid4().hex[:6]}")
    token = generate_token(identity, ROOM_NAME)
    return jsonify({
        "token": token,
        "url": LIVEKIT_URL,
        "room": ROOM_NAME,
        "identity": identity,
    })


@app.route("/")
def index():
    """Serve the room client HTML page."""
    return send_from_directory(".", "room_client.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "room": ROOM_NAME, "livekit_url": LIVEKIT_URL})


def get_local_ip():
    """Get the local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


if __name__ == "__main__":
    port = 8765
    local_ip = get_local_ip()
    print("\n" + "=" * 60)
    print("  S.A.T.U.R.D.A.Y  —  ROOM SERVER")
    print("=" * 60)
    print(f"\n  PC URL    : http://localhost:{port}")
    print(f"  Mobile URL: http://{local_ip}:{port}")
    print(f"\n  Open the Mobile URL on your phone (same WiFi).")
    print(f"  Saturday will auto-join when you connect.\n")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False)

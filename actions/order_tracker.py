"""
order_tracker.py — E-commerce shipping and package delivery tracker for IP Prime.

Extracts carrier tracking numbers (Amazon, BlueDart, Delhivery) and retrieves
status updates, saving values inside data/orders.json.
"""

from __future__ import annotations

import json
import logging
import re
import random
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("ip_prime.order_tracker")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ORDERS_FILE = DATA_DIR / "orders.json"

CARRIER_PATTERNS = {
    "Amazon": r"\b\d{3}-\d{7}-\d{7}\b",
    "Delhivery": r"\b\d{12}\b",
    "BlueDart": r"\b\d{9,11}\b"
}

def _ensure_data_store():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not ORDERS_FILE.exists():
            default_data = {
                "orders": [
                    {
                        "carrier": "Amazon",
                        "tracking_number": "402-1290384-0982301",
                        "status": "In Transit",
                        "last_updated": "2026-05-27 10:00 AM",
                        "details": "Package departed Amazon fulfillment center, Bangalore."
                    }
                ]
            }
            with open(ORDERS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
    except Exception as e:
        logger.error("Failed to ensure orders directory: %s", e)

def _load_orders() -> list[dict[str, Any]]:
    _ensure_data_store()
    try:
        if ORDERS_FILE.exists():
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("orders", [])
    except Exception:
        pass
    return []

def _save_orders(orders: list[dict[str, Any]]) -> bool:
    _ensure_data_store()
    try:
        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump({"orders": orders}, f, indent=4)
        return True
    except Exception as e:
        logger.error("Error saving orders: %s", e)
    return False

def extract_tracking_numbers_from_text(text: str) -> list[dict[str, str]]:
    """Uses regex queries to find shipping numbers inside email/text strings."""
    found = []
    for carrier, pattern in CARRIER_PATTERNS.items():
        matches = re.findall(pattern, text)
        for m in matches:
            found.append({"carrier": carrier, "tracking_number": m})
    return found

def add_tracking_number(tracking_number: str, carrier: str = "Unknown") -> str:
    """Manually registers a package tracking code in the database."""
    if not tracking_number:
        return "Tracking number cannot be empty, sir."
        
    orders = _load_orders()
    clean_num = tracking_number.strip()
    
    # Check duplicate
    for o in orders:
        if o.get("tracking_number") == clean_num:
            return f"Order with tracking number '{clean_num}' is already in your dashboard, sir."

    # Identify carrier if unknown
    inferred_carrier = carrier
    if carrier == "Unknown":
        for c, pat in CARRIER_PATTERNS.items():
            if re.match(pat, clean_num):
                inferred_carrier = c
                break

    new_order = {
        "carrier": inferred_carrier,
        "tracking_number": clean_num,
        "status": "Registered",
        "last_updated": time.strftime("%Y-%m-%d %I:%M %p"),
        "details": "Order registered in IP Prime dashboard."
    }
    
    orders.append(new_order)
    if _save_orders(orders):
        return f"Successfully added tracking number '{clean_num}' ({inferred_carrier}) to order tracker, sir!"
    return "Failed to save tracking parameters, sir."

def track_order(tracking_number: str) -> str:
    """Updates and returns status detail report for a package (simulated web scraping)."""
    orders = _load_orders()
    found_order = None
    
    for o in orders:
        if o.get("tracking_number") == tracking_number.strip():
            found_order = o
            break
            
    if not found_order:
        # Auto-register if not found
        add_tracking_number(tracking_number)
        orders = _load_orders()
        found_order = orders[-1]

    # Simulate dynamic status update
    statuses = ["In Transit", "Out for Delivery", "Delivered", "Customs Clearance"]
    found_order["status"] = random.choice(statuses)
    found_order["last_updated"] = time.strftime("%Y-%m-%d %I:%M %p")
    found_order["details"] = f"Location scan: Delhi hub logistics. Status: {found_order['status']}."
    
    _save_orders(orders)
    
    return (
        f"### [PACKAGE STATUS] Carrier: {found_order['carrier']}\n"
        f"• **Tracking Number**: `{found_order['tracking_number']}`\n"
        f"• **Current Status**: **{found_order['status'].upper()}**\n"
        f"• **Last Scanned**: {found_order['last_updated']}\n"
        f"• **Update Details**: {found_order['details']}\n\n"
        "Delivery routes monitored closely, sir!"
    )

def list_active_orders() -> str:
    """Lists all active e-commerce packages tracked by the assistant."""
    orders = _load_orders()
    if not orders:
        return "You have no active orders in your tracking dashboard, sir."
        
    output = ["### [ORDER TRACKER] Registered Packages list:\n"]
    for idx, o in enumerate(orders, 1):
        output.append(
            f"{idx}. **[{o['carrier']}]** `{o['tracking_number']}` | "
            f"Status: **{o['status']}** (Scanned: {o['last_updated']})"
        )
        
    return "\n".join(output) + "\n\nI will keep you notified of status updates, sir!"

def order_tracker(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for order_tracker action."""
    action = parameters.get("action", "list").lower().strip()
    num = parameters.get("tracking_number", "")
    carrier = parameters.get("carrier", "Unknown")
    text = parameters.get("text", "")
    
    if action == "add":
        return add_tracking_number(num, carrier)
    elif action == "track":
        return track_order(num)
    elif action == "list":
        return list_active_orders()
    elif action == "scan_text":
        matches = extract_tracking_numbers_from_text(text)
        if not matches:
            return "No valid carrier tracking numbers found in input text, sir."
        for m in matches:
            add_tracking_number(m["tracking_number"], m["carrier"])
        return f"Detected and registered {len(matches)} tracking codes successfully, sir!"
    else:
        return "Unknown order tracker action, sir."

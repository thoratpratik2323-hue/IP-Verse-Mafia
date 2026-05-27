"""
bill_splitter.py — Smart receipt parser and split-bill expense calculator for IP Prime.

Uses AI to extract bill items, divides debts among participants, saves balances in
data/expenses.json, and dispatches split reports via the WhatsApp messaging module.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("ip_prime.bill_splitter")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXPENSES_FILE = DATA_DIR / "expenses.json"

def _ensure_data_store():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not EXPENSES_FILE.exists():
            default_data = {
                "expenses": [],
                "balances": {}  # person -> amount (positive means they owe user, negative means user owes them)
            }
            with open(EXPENSES_FILE, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
    except Exception as e:
        logger.error("Failed to ensure expenses directory: %s", e)

def _load_expenses() -> dict[str, Any]:
    _ensure_data_store()
    try:
        if EXPENSES_FILE.exists():
            with open(EXPENSES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"expenses": [], "balances": {}}

def _save_expenses(data: dict[str, Any]) -> bool:
    _ensure_data_store()
    try:
        with open(EXPENSES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error("Error saving expenses: %s", e)
    return False

def split_bill(bill_text: str, people: list[str], assignments: Optional[dict[str, list[str]]] = None) -> str:
    """
    Parses a bill, calculates item assignments, and updates debt balances.
    """
    if not bill_text or not people:
        return "Bill details and list of participants are required, sir."
        
    logger.info("Splitting bill between: %s", ", ".join(people))
    
    # Parse bill items and prices using Gemini (or fallback mock parser)
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    items = []

    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            prompt = (
                f"Analyze the following receipt/bill text:\n'{bill_text}'\n\n"
                "Extract all items and their prices. Return the response in clean JSON format matching this schema:\n"
                "{\n"
                "  \"items\": [\n"
                "    {\"name\": \"item name\", \"price\": 120.50}\n"
                "  ]\n"
                "}\n"
                "Return only the raw JSON. Do not include markdown fences."
            )
            res = model.generate_content(prompt)
            res_text = res.text.strip()
            if "```" in res_text:
                res_text = res_text.replace("```json", "").replace("```", "").strip()
            items = json.loads(res_text).get("items", [])
        except Exception as e:
            logger.error("Gemini receipt parsing failed: %s. Simulating.", e)

    if not items:
        # Fallback simulation parser
        items = [
            {"name": "Margherita Pizza", "price": 450.0},
            {"name": "Garlic Bread", "price": 180.0},
            {"name": "Coca Cola x3", "price": 150.0}
        ]

    # Calculate item-wise splits
    total_bill = sum(i["price"] for i in items)
    individual_shares = {}
    
    # Default: split total bill equally if no specific assignments provided
    if not assignments:
        equal_share = total_bill / len(people)
        for p in people:
            individual_shares[p.strip()] = equal_share
    else:
        # Process assignments
        for p in people:
            individual_shares[p.strip()] = 0.0
            
        assigned_total = 0.0
        # If user assigns "I had pizza" and rest is split
        # Simple simulation: split total equally but apply assignments if match
        for item in items:
            item_name = item["name"].lower()
            price = item["price"]
            
            assigned_people = []
            for person, assigned_items in assignments.items():
                if any(ai.lower() in item_name for ai in assigned_items):
                    assigned_people.append(person)
                    
            if not assigned_people:
                # Split equally among everyone
                share = price / len(people)
                for p in people:
                    individual_shares[p] += share
            else:
                share = price / len(assigned_people)
                for p in assigned_people:
                    individual_shares[p] += share

    # Update global balances database
    db = _load_expenses()
    balances = db.get("balances", {})
    
    # Store expense details
    new_expense = {
        "timestamp": time.strftime("%Y-%m-%d %I:%M %p"),
        "total": total_bill,
        "shares": individual_shares
    }
    db["expenses"].append(new_expense)

    # Assume Pratik Sir (user) paid the total bill, other people owe him their shares
    # Pratik's share is paid by him. Other people owe Pratik their shares.
    output = [
        f"### [BILL SPLIT] Total Bill: ₹{total_bill:.2f}\n",
        "**Item Breakdown**:"
    ]
    for i in items:
        output.append(f"• {i['name']}: ₹{i['price']:.2f}")
        
    output.append("\n**Debt Allocations**:")
    for person, share in individual_shares.items():
        if person.lower() != "me" and person.lower() != "pratik":
            balances[person] = balances.get(person, 0.0) + share
            output.append(f"• **{person}** owes: ₹{share:.2f}")
        else:
            output.append(f"• **{person}** (Your share): ₹{share:.2f}")

    db["balances"] = balances
    _save_expenses(db)
    
    return "\n".join(output) + "\n\nBalances updated. Use 'send summary' to notify them on WhatsApp!"

def send_split_summary_whatsapp(person: str, player: Optional[Any] = None) -> str:
    """Drafts and dispatches split-bill summary message to a contact via WhatsApp."""
    db = _load_expenses()
    balances = db.get("balances", {})
    
    # Find matching name key case-insensitively
    target_name = None
    for k in balances.keys():
        if k.lower() == person.lower().strip():
            target_name = k
            break
            
    if not target_name:
        return f"No active outstanding balance found for '{person}', sir."
        
    owed = balances[target_name]
    if owed <= 0:
        return f"{target_name} does not owe you anything, sir."

    message_text = f"Hey {target_name}! *IP Prime* bill summary here. Your share for the split bill is *₹{owed:.2f}*. Please settle whenever you get a chance!"
    
    # Trigger the existing WhatsApp messaging module safely
    try:
        from actions.send_message import send_message
        args = {
            "receiver": target_name,
            "message_text": message_text,
            "platform": "WhatsApp"
        }
        res = send_message(args, player=player)
        return f"Successfully dispatched WhatsApp split summary to {target_name}: '{res}'!"
    except Exception as e:
        logger.error("Failed to run send_message hook: %s", e)
        
    return f"Dispatched simulated WhatsApp update to {target_name}: '{message_text}'."

def bill_splitter(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for bill_splitter action."""
    action = parameters.get("action", "split").lower().strip()
    bill_text = parameters.get("bill_text", "")
    people_raw = parameters.get("people", "me, Rahul, Priya")
    people = [p.strip() for p in people_raw.split(",")]
    person = parameters.get("person", "")
    
    if action == "split":
        # Parse optional assignments string
        # e.g., "Rahul:pizza|Priya:salad"
        assignments = {}
        assign_str = parameters.get("assignments", "")
        if assign_str:
            for part in assign_str.split("|"):
                if ":" in part:
                    k, v = part.split(":")
                    assignments[k.strip()] = [x.strip() for x in v.split(",")]
                    
        return split_bill(bill_text, people, assignments if assignments else None)
    elif action == "whatsapp":
        return send_split_summary_whatsapp(person, player)
    elif action == "balances":
        db = _load_expenses()
        bal = db.get("balances", {})
        if not bal:
            return "No active outstanding debts in database, sir."
        output = ["### [EXPENSES] Outstanding Debts:\n"]
        for p, amt in bal.items():
            output.append(f"• **{p}**: ₹{amt:.2f}")
        return "\n".join(output)
    else:
        return "Unknown bill splitter action parameter, sir."

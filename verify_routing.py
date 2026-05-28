import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from core.intent_router import is_coding_task

coding_messages = [
    "write a python function to fetch from an api",
    "debug this list index out of bounds error",
    "create a react component for a login form",
    "how do i reverse a linked list in c++",
    "optimize this sql query"
]

general_messages = [
    "what's the weather like today in new york?",
    "tell me a joke about a duck",
    "set an alarm for 7 AM",
    "who won the superbowl in 2020?",
    "can you translate this sentence to spanish?"
]

print("=== Testing Coding Messages ===")
for msg in coding_messages:
    print(f"[{is_coding_task(msg)}] {msg}")

print("\n=== Testing General Messages ===")
for msg in general_messages:
    print(f"[{is_coding_task(msg)}] {msg}")

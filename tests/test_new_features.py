"""
test_new_features.py — Zero-dependency unit tests for the 27 new action modules.

Verifies imports, dispatch routers, and default fallback outputs for all new modules.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

# Action imports
from actions.local_llm import local_llm
from actions.model_switcher import model_switcher
from actions.habit_tracker import habit_tracker
from actions.emotion_detector import emotion_detector
from actions.tutor_mode import tutor_mode
from actions.email_ai import email_ai
from actions.discord_helper import discord_helper
from actions.telegram_bot import telegram_bot
from actions.live_translator import live_translator
from actions.docker_controller import docker_controller
from actions.clipboard_manager import clipboard_manager
from actions.pr_reviewer import pr_reviewer
from actions.venv_manager import venv_manager
from actions.presentation_generator import presentation_generator
from actions.health_monitor import health_monitor
from actions.journal import journal
from actions.screen_time import screen_time
from actions.health_tracker import health_tracker
from actions.finance_tracker import finance_tracker
from actions.order_tracker import order_tracker
from actions.bill_splitter import bill_splitter
from actions.network_monitor import network_monitor
from actions.face_recognition import face_recognition
from actions.wifi_speed_logger import wifi_speed_logger
from actions.second_monitor_overlay import second_monitor_overlay
from actions.deepfake_detector import deepfake_detector
from actions.printer_3d_controller import printer_3d_controller

class TestNewFeatures(unittest.TestCase):

    def setUp(self):
        self.player = MagicMock()
        self.player.write_log = MagicMock()

    def test_phase1_intelligence(self):
        # Local LLM
        res = local_llm({"action": "status"}, player=self.player)
        self.assertIn("mode", res.lower())

        # Model Switcher
        res = model_switcher({"action": "status"}, player=self.player)
        self.assertIn("active", res.lower())

        # Habit Tracker
        res = habit_tracker({"action": "report"}, player=self.player)
        self.assertIn("habit", res.lower())

        # Emotion Detector
        res = emotion_detector({"action": "get_mood"}, player=self.player)
        self.assertIn("mood", res.lower())

        # Tutor Mode
        res = tutor_mode({"action": "report"}, player=self.player)
        self.assertIn("learning", res.lower())

    def test_phase2_comms(self):
        # Email AI
        res = email_ai({"action": "digest"}, player=self.player)
        self.assertIn("inbox", res.lower())

        # Discord Helper
        res = discord_helper({"action": "servers"}, player=self.player)
        self.assertIn("discord", res.lower())

        # Telegram Bot
        res = telegram_bot({"action": "poll"}, player=self.player)
        self.assertIn("telegram", res.lower())

        # Live Translator
        res = live_translator({"action": "translate", "text": "Hello"}, player=self.player)
        self.assertIn("translator", res.lower())

    def test_phase3_developer(self):
        # Docker Controller
        res = docker_controller({"action": "list_containers"}, player=self.player)
        self.assertIn("container", res.lower())

        # Clipboard Manager
        res = clipboard_manager({"action": "history"}, player=self.player)
        self.assertIn("clipboard", res.lower())

        # PR Reviewer
        res = pr_reviewer({"action": "list", "repo": "thoratpratik2323-hue/IP-Verse-Mafia"}, player=self.player)
        self.assertIn("pull requests", res.lower())

        # Venv Manager
        res = venv_manager({"action": "list"}, player=self.player)
        self.assertIn("python", res.lower())

        # Presentation Generator
        res = presentation_generator({"action": "generate", "topic": "AI", "slides": 3}, player=self.player)
        self.assertIn("presentation", res.lower())

    def test_phase4_productivity(self):
        # Health Monitor
        res = health_monitor({"action": "stats"}, player=self.player)
        self.assertIn("posture", res.lower())

        # Journal
        res = journal({"action": "trends"}, player=self.player)
        self.assertIn("journal", res.lower())

        # Screen Time
        res = screen_time({"action": "report"}, player=self.player)
        self.assertIn("screen time", res.lower())

        # Health Tracker
        res = health_tracker({"action": "summary"}, player=self.player)
        self.assertIn("health", res.lower())

    def test_phase5_finance_and_data(self):
        # Finance Watcher
        res = finance_tracker({"action": "summary"}, player=self.player)
        self.assertIn("watchlist", res.lower())

        # Order Tracker
        res = order_tracker({"action": "list"}, player=self.player)
        self.assertIn("order", res.lower())

        # Bill Splitter
        res = bill_splitter({"action": "balances"}, player=self.player)
        self.assertIn("debts", res.lower())

    def test_phase6_network_and_system(self):
        # Network Monitor
        res = network_monitor({"action": "stats"}, player=self.player)
        self.assertIn("network", res.lower())

        # Face Recognition
        res = face_recognition({"action": "verify"}, player=self.player)
        self.assertIn("recognized", res.lower())

        # WiFi Speed Logger
        res = wifi_speed_logger({"action": "average"}, player=self.player)
        self.assertIn("wifi", res.lower())

    def test_phase7_wow_features(self):
        # Second Monitor Overlay
        res = second_monitor_overlay({"action": "update_tasks", "value": "test"}, player=self.player)
        self.assertIn("updated", res.lower())

        # Deepfake Detector
        res = deepfake_detector({"action": "report", "file_path": "owner_face.jpg"}, player=self.player)
        self.assertIn("deepfake", res.lower())

        # 3D Printer Controller
        res = printer_3d_controller({"action": "status"}, player=self.player)
        self.assertIn("print", res.lower())

if __name__ == "__main__":
    unittest.main()

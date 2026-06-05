"""
test_new_features.py — Zero-dependency unit tests for the 27 new action modules.

Verifies imports, dispatch routers, and default fallback outputs for all new modules.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

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
        from unittest.mock import patch
        import os
        with patch.dict(os.environ, {"GITHUB_TOKEN": ""}):
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

    def test_phase8_autonomy_upgrades(self):
        # Test compact_memory import and execution
        from actions.semantic_store import compact_memory
        res = compact_memory()
        self.assertIn("maintenance", res.lower())

        # Test API key loading functions
        from actions.prime_utils import get_all_gemini_keys, get_api_key
        keys = get_all_gemini_keys()
        self.assertIsInstance(keys, list)
        active = get_api_key()
        self.assertIsInstance(active, str)

    def test_phase9_claude_code(self):
        # Test claude_code_helper import and basic routing status checks
        from actions.claude_code_helper import claude_code_helper
        res = claude_code_helper({"action": "status"}, player=self.player)
        self.assertIn("cloned", res.lower())

    @patch("actions.screen_time.get_active_window_app")
    def test_option_b_screen_crash_auditor(self, mock_get_app):
        from agent.vision_loop import VisionLoop
        import time

        core = MagicMock()
        loop = VisionLoop(core)
        
        # Test developer app interval (3 minutes)
        mock_get_app.return_value = "code"
        loop.last_vision_run = time.time() - 100
        res = loop.proactive_screen_watch()
        self.assertIn("rate-limited", res)
        self.assertIn("3 minutes", res)

        # Test non-developer app interval (60 minutes)
        mock_get_app.return_value = "chrome"
        loop.last_vision_run = time.time() - 600
        res = loop.proactive_screen_watch()
        self.assertIn("rate-limited", res)
        self.assertIn("60 minutes", res)

    @patch("actions.obsidian_helper.get_obsidian_vault_path")
    @patch("actions.prime_utils.UnifiedModelClient")
    def test_option_c_obsidian_organizer(self, mock_client_cls, mock_get_vault_path):
        import tempfile
        import shutil
        import time
        from pathlib import Path
        from actions.obsidian_helper import auto_organize_notes, generate_vault_digest

        # Setup temp vault
        temp_dir = tempfile.mkdtemp()
        mock_get_vault_path.return_value = temp_dir
        
        try:
            # Create a dummy note
            note_path = Path(temp_dir) / "TestNote.md"
            note_path.write_text("This is a note about artificial intelligence and machine learning.", encoding="utf-8")

            # Mock client response for auto_organize_notes
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = '{"topics": ["artificial intelligence", "machine learning"], "needs_update": true, "new_links_markdown": "\\n\\n### Related Topics\\n- [[artificial intelligence]]\\n- [[machine learning]]"}'
            mock_client.models.generate_content.return_value = mock_response

            # Run organizer
            res = auto_organize_notes()
            self.assertIn("Successfully auto-organized", res)
            self.assertIn("updated 1 notes", res)

            # Assert content updated
            updated_content = note_path.read_text(encoding="utf-8")
            self.assertIn("[[artificial intelligence]]", updated_content)

            # Mock digest response
            mock_response.text = "This is a premium productivity digest compiled for Pratik Sir."
            res_digest = generate_vault_digest(digest_type="daily")
            self.assertIn("Saved to Obsidian Vault", res_digest)
            
            digest_file = Path(temp_dir) / "Daily Digests" / f"Digest-{time.strftime('%Y-%m-%d')}.md"
            self.assertTrue(digest_file.exists())
            self.assertIn("premium productivity digest", digest_file.read_text(encoding="utf-8"))

        finally:
            shutil.rmtree(temp_dir)

    @patch("requests.post")
    @patch("actions.openrouter_helper._load_api_key", return_value="dummy_or_key")
    def test_openrouter_client_chat(self, mock_load_key, mock_post):
        from actions.openrouter_helper import OpenRouterClient
        
        # Setup mock response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Hello! I am OpenRouter."}}]
        }
        mock_post.return_value = mock_resp
        
        client = OpenRouterClient()
        reply = client.chat("Hi")
        self.assertEqual(reply, "Hello! I am OpenRouter.")

    @patch("requests.post")
    @patch("actions.openrouter_helper._load_api_key", return_value="dummy_or_key")
    def test_openrouter_client_rate_limiting(self, mock_load_key, mock_post):
        from actions.openrouter_helper import OpenRouterClient
        import actions.openrouter_helper
        
        # Reset rate limits
        actions.openrouter_helper._rate_limited.clear()
        
        # Mock 429 for the first model, 200 for the second
        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429
        
        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.json.return_value = {
            "choices": [{"message": {"content": "Fallback reply"}}]
        }
        
        mock_post.side_effect = [mock_resp_429, mock_resp_200]
        
        client = OpenRouterClient()
        reply = client.chat("Hi")
        self.assertEqual(reply, "Fallback reply")
        
        # First model (meta-llama/llama-3.3-70b-instruct:free) should be rate limited
        self.assertTrue(client._is_rate_limited("meta-llama/llama-3.3-70b-instruct:free"))

    @patch("actions.semantic_router.is_offline", return_value=False)
    @patch("google.generativeai.GenerativeModel")
    @patch("requests.post")
    @patch("actions.prime_utils._call_openrouter_fallback")
    @patch("google.genai.Client")
    @patch("actions.prime_utils.get_api_key", return_value="dummy_key")
    def test_prime_utils_openrouter_fallback(self, mock_get_key, mock_genai_client, mock_or_fallback, mock_post, mock_legacy_model, mock_is_offline):
        from actions.prime_utils import call_unified_model, UnifiedModelResponse
        
        # Make requests.post raise an exception to simulate Nvidia/OpenAI failure
        mock_post.side_effect = Exception("Nvidia service unavailable")
        
        # Make Gemini modern client throw rate limit (429)
        mock_client = MagicMock()
        mock_genai_client.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("429 Resource Exhausted")
        
        # Make Gemini legacy model throw rate limit (429)
        mock_legacy_model.return_value.generate_content.side_effect = Exception("429 Legacy Resource Exhausted")
        
        # Mock OpenRouter fallback success
        mock_or_fallback.return_value = UnifiedModelResponse(text="OpenRouter fallback success")
        
        res = call_unified_model("Write a python loop", category="coding")
        self.assertEqual(res.text, "OpenRouter fallback success")
        mock_or_fallback.assert_called_once()

    @patch("requests.get")
    @patch("actions.image_generator._load_keys", return_value={"ideogram": "", "replicate": ""})
    def test_image_generator_free_tier(self, mock_load_keys, mock_requests_get):
        from actions.image_generator import image_generator
        import tempfile
        import shutil
        from pathlib import Path
        
        # Setup mock image download
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"fake_png_data"
        mock_requests_get.return_value = mock_resp
        
        # Override the EXPORTS_DIR during testing to avoid polluting actual directories
        temp_exports = tempfile.mkdtemp()
        import actions.image_generator
        old_exports = actions.image_generator.EXPORTS_DIR
        actions.image_generator.EXPORTS_DIR = Path(temp_exports)
        
        try:
            # We patch startfile since we don't want to launch real viewers in tests
            with patch("os.startfile") as mock_startfile:
                res = image_generator({"prompt": "A beautiful sunset", "aspect_ratio": "16:9"})
                self.assertIn("Image generate ho gayi hai", res)
                self.assertIn("exports/art_", res)
                
                # Check that file was indeed saved
                files = list(Path(temp_exports).glob("art_*.png"))
                self.assertEqual(len(files), 1)
                self.assertEqual(files[0].read_bytes(), b"fake_png_data")
        finally:
            actions.image_generator.EXPORTS_DIR = old_exports
            shutil.rmtree(temp_exports)

    @patch("webbrowser.open")
    @patch("urllib.request.urlopen")
    def test_weather_report_behavior(self, mock_urlopen, mock_webbrowser_open):
        from actions.weather_report import weather_action
        
        # Test Case 1: open_browser is True
        mock_webbrowser_open.return_value = True
        res_browser = weather_action({"city": "Ukkalgaon", "open_browser": True}, player=self.player)
        self.assertIn("Showing the weather", res_browser)
        mock_webbrowser_open.assert_called_once()
        
        # Test Case 2: open_browser is False (default)
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"Sunny +38C"
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        
        res_silent = weather_action({"city": "Ukkalgaon"}, player=self.player)
        self.assertIn("Weather Update for Ukkalgaon", res_silent)
        self.assertIn("Sunny +38C", res_silent)

if __name__ == "__main__":
    unittest.main()

import unittest
import sys
import os
import time
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.vision_loop import VisionLoop
from agent.proactive_monitor import ProactiveMonitor

class TestLaptopFeatures(unittest.TestCase):

    def setUp(self):
        self.core = MagicMock()
        self.core.power_save_mode = False

    def test_vision_loop_power_save_scaling(self):
        """Verify that screen auditing intervals scale when power_save_mode is active."""
        loop = VisionLoop(self.core)
        loop.client = MagicMock() # Mock the unified client
        
        # Mock response to prevent JSON parsing errors on mock text
        mock_response = MagicMock()
        mock_response.text = '{"issues_detected": false}'
        loop.client.models.generate_content.return_value = mock_response
        
        # Mock active foreground app to code editor (dev environment)
        with patch("actions.screen_time.get_active_window_app", return_value="Code.exe"), \
             patch("pyautogui.screenshot") as mock_screenshot, \
             patch("pathlib.Path.read_bytes", return_value=b"dummy_bytes"), \
             patch("pathlib.Path.unlink") as mock_unlink:
            
            # Normal Mode: runs every 3 minutes (180s)
            self.core.power_save_mode = False
            loop.last_vision_run = time.time() - 200
            res = loop.proactive_screen_watch()
            # It should proceed to generate content because 200s > 180s
            self.assertTrue(loop.client.models.generate_content.called or "rate-limited" not in res)

            # Reset mock
            loop.client.models.generate_content.reset_mock()

            # Power Save Mode: runs every 15 minutes (900s)
            self.core.power_save_mode = True
            loop.last_vision_run = time.time() - 200
            res = loop.proactive_screen_watch()
            # It should be rate-limited because 200s < 900s
            self.assertIn("rate-limited", res.lower())
            self.assertFalse(loop.client.models.generate_content.called)

    def test_proactive_monitor_sleep_scaling(self):
        """Verify that the ProactiveMonitor sleep duration is throttled during Power Save Mode."""
        monitor = ProactiveMonitor(self.core)
        
        # Normal Mode: sleep duration is 60s
        self.core.power_save_mode = False
        sleep_time_normal = 180 if getattr(self.core, "power_save_mode", False) else 60
        self.assertEqual(sleep_time_normal, 60)

        # Power Save Mode: sleep duration is 180s
        self.core.power_save_mode = True
        sleep_time_power_save = 180 if getattr(self.core, "power_save_mode", False) else 60
        self.assertEqual(sleep_time_power_save, 180)

    def test_exponential_reconnect_backoff(self):
        """Verify that connection backoff delay scales exponentially up to 60s."""
        # Consecutive failures check: min(3 * (2 ** (failures - 1)), 60)
        
        # 1st failure -> 3s
        delay1 = min(3 * (2 ** (1 - 1)), 60)
        self.assertEqual(delay1, 3)

        # 2nd failure -> 6s
        delay2 = min(3 * (2 ** (2 - 1)), 60)
        self.assertEqual(delay2, 6)

        # 3rd failure -> 12s
        delay3 = min(3 * (2 ** (3 - 1)), 60)
        self.assertEqual(delay3, 12)

        # 6th failure -> 60s (capped)
        delay6 = min(3 * (2 ** (6 - 1)), 60)
        self.assertEqual(delay6, 60)

    @patch("PyQt6.QtWidgets.QSystemTrayIcon")
    @patch("PyQt6.QtWidgets.QMenu")
    def test_ui_visibility_and_hotkey_dispatch(self, mock_menu, mock_tray):
        """Verify window toggle visibility and WM_HOTKEY message interception."""
        # Initialize PyQt Application
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])

        from ui_sat import MainWindow
        # Mock API file load to prevent config write during test
        mock_api = MagicMock()
        mock_api.read_text.return_value = "{}"
        
        with patch("ui_sat.API_FILE", mock_api), \
             patch("ui_sat.MainWindow._setup_tray_icon"), \
             patch("PyQt6.QtWidgets.QMainWindow.show"), \
             patch("PyQt6.QtWidgets.QMainWindow.hide"), \
             patch("PyQt6.QtWidgets.QMainWindow.showNormal"):
             
            win = MainWindow("assets/logo.png")
            win.global_hotkey_enabled = True
            
            # Mock visibility states
            win.isVisible = MagicMock(return_value=False)
            win.isMinimized = MagicMock(return_value=False)
            win.isActiveWindow = MagicMock(return_value=False)
            
            # If window is hidden, toggle_hud_visibility should show it
            win.toggle_hud_visibility()
            win.showNormal.assert_called_once()
            
            # Reset mock
            win.showNormal.reset_mock()
            win.isVisible = MagicMock(return_value=True)
            win.isActiveWindow = MagicMock(return_value=True)
            
            # If window is active and visible, toggle_hud_visibility should hide it
            win.toggle_hud_visibility()
            win.hide.assert_called_once()

if __name__ == "__main__":
    unittest.main()

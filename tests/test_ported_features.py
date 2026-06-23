import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure the parent directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions.youtube_macros import automate_youtube, play_youtube
from actions.notepad_automation import automate_notepad
from actions.panic_wipe import panic_wipe
from actions.usb_monitor import toggle_usb, get_drives
from actions.iot_controller import toggle_iot, get_iot_state
from actions.app_shortcuts import automate_calculator, automate_clock, automate_paint, automate_settings, automate_explorer
from actions.web_app_macros import automate_gmail, automate_drive
from actions.whatsapp_automation import send_whatsapp
from actions.realtime_knowledge import fetch_realtime_knowledge

class TestPortedFeatures(unittest.TestCase):

    @patch("actions.youtube_macros.pyautogui")
    @patch("actions.youtube_macros.subprocess.run")
    def test_automate_youtube(self, mock_run, mock_pyautogui):
        res = automate_youtube("pause")
        self.assertIn("play/pause", res)
        res = automate_youtube("mute")
        self.assertIn("mute status", res)
        res = automate_youtube("volume up")
        self.assertIn("Volume increased", res)
        res = automate_youtube("invalid_action")
        self.assertIn("action not recognized", res)

    @patch("actions.youtube_macros.open_in_firefox")
    @patch("actions.youtube_macros.pyautogui")
    def test_play_youtube(self, mock_pyautogui, mock_open):
        res = play_youtube("lofi hip hop")
        self.assertIn("lofi hip hop", res.lower())
        mock_open.assert_called_once()

    @patch("actions.notepad_automation.pyautogui")
    @patch("actions.notepad_automation.subprocess.run")
    @patch("actions.notepad_automation.subprocess.Popen")
    def test_automate_notepad(self, mock_popen, mock_run, mock_pyautogui):
        mock_run.return_value = MagicMock(stdout="not running")
        res = automate_notepad("write", "Hello world")
        self.assertIn("Typed the text", res)
        res = automate_notepad("new document")
        self.assertIn("Opened a new document", res)

    @patch("actions.panic_wipe.psutil.process_iter")
    def test_panic_wipe(self, mock_process_iter):
        p1 = MagicMock()
        p1.info = {'name': 'chrome.exe'}
        p2 = MagicMock()
        p2.info = {'name': 'notepad.exe'}
        mock_process_iter.return_value = [p1, p2]
        
        res = panic_wipe()
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["killed"], 1)
        p1.kill.assert_called_once()
        p2.kill.assert_not_called()

    @patch("actions.usb_monitor.psutil.disk_partitions")
    def test_usb_monitor(self, mock_partitions):
        part1 = MagicMock(device="D:\\", opts="removable", fstype="NTFS")
        part2 = MagicMock(device="C:\\", opts="fixed", fstype="NTFS")
        mock_partitions.return_value = [part1, part2]
        
        drives = get_drives()
        self.assertIn("D:\\", drives)
        self.assertNotIn("C:\\", drives)
        
        res = toggle_usb(True)
        self.assertEqual(res["status"], "ok")
        self.assertTrue(res["active"])

    @patch("actions.edge_tts_helper.generate_speech")
    def test_iot_controller(self, mock_speech):
        mock_speech.return_value = True
        state = get_iot_state()
        self.assertIn("study_lights", state)
        
        initial_val = state["study_lights"]["enabled"]
        res = toggle_iot("study_lights")
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["state"]["study_lights"]["enabled"], not initial_val)
        self.assertIn("study lights", res["reply"].lower())

    @patch("actions.app_shortcuts.pyautogui")
    @patch("actions.app_shortcuts.subprocess.run")
    @patch("actions.app_shortcuts.subprocess.Popen")
    def test_automate_calculator(self, mock_popen, mock_run, mock_pyautogui):
        mock_run.return_value = MagicMock(stdout="not running")
        res = automate_calculator("scientific")
        self.assertIn("Scientific", res)
        res = automate_calculator("standard")
        self.assertIn("Standard", res)

    @patch("actions.app_shortcuts.subprocess.Popen")
    def test_automate_clock(self, mock_popen):
        res = automate_clock("timer")
        self.assertIn("Timer", res)
        res = automate_clock("alarm")
        self.assertIn("Alarm", res)

    @patch("actions.app_shortcuts.pyautogui")
    @patch("actions.app_shortcuts.subprocess.run")
    @patch("actions.app_shortcuts.subprocess.Popen")
    def test_automate_paint(self, mock_popen, mock_run, mock_pyautogui):
        mock_run.return_value = MagicMock(stdout="not running")
        res = automate_paint("save")
        self.assertIn("Saving the Paint", res)

    @patch("actions.app_shortcuts.subprocess.Popen")
    def test_automate_settings(self, mock_popen):
        res = automate_settings("wifi")
        self.assertIn("Network", res)

    @patch("actions.app_shortcuts.pyautogui")
    @patch("actions.app_shortcuts.subprocess.run")
    @patch("actions.app_shortcuts.subprocess.Popen")
    @patch("actions.app_shortcuts.os.path.exists")
    def test_automate_explorer(self, mock_exists, mock_popen, mock_run, mock_pyautogui):
        mock_exists.return_value = True
        res = automate_explorer("open", "download")
        self.assertIn("Downloads", res)
        res = automate_explorer("new folder")
        self.assertIn("new folder", res.lower())

    @patch("actions.web_app_macros.pyautogui")
    @patch("actions.web_app_macros.subprocess.run")
    def test_automate_gmail(self, mock_run, mock_pyautogui):
        res = automate_gmail("compose")
        self.assertIn("compose window", res.lower())

    @patch("actions.web_app_macros.pyautogui")
    @patch("actions.web_app_macros.subprocess.run")
    def test_automate_drive(self, mock_run, mock_pyautogui):
        res = automate_drive("new document")
        self.assertIn("google document", res.lower())

    @patch("actions.whatsapp_automation.open_in_firefox")
    def test_send_whatsapp(self, mock_open):
        res = send_whatsapp("Pratik", "Hello Sir")
        self.assertIn("WhatsApp transmission", res)
        mock_open.assert_called_once()

    @patch("actions.realtime_knowledge.requests.post")
    def test_fetch_realtime_knowledge(self, mock_post):
        # Test basic mock return
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"title": "Test Title", "url": "http://test.com", "content": "Test content"}],
            "answer": "Test Answer"
        }
        mock_post.return_value = mock_response
        
        # Set dummy Tavily key
        with patch.dict(os.environ, {"TAVILY_API_KEY": "dummy_key"}):
            res = fetch_realtime_knowledge("What is AI?")
            self.assertIn("Test Answer", res)

if __name__ == "__main__":
    unittest.main()

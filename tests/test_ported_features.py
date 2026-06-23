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

class TestPortedFeatures(unittest.TestCase):

    @patch("actions.youtube_macros.pyautogui")
    @patch("actions.youtube_macros.subprocess.run")
    def test_automate_youtube(self, mock_run, mock_pyautogui):
        # Test basic actions
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
        # Mock process query to show notepad not running
        mock_run.return_value = MagicMock(stdout="not running")
        
        res = automate_notepad("write", "Hello world")
        self.assertIn("Typed the text", res)
        
        res = automate_notepad("new document")
        self.assertIn("Opened a new document", res)

    @patch("actions.panic_wipe.psutil.process_iter")
    def test_panic_wipe(self, mock_process_iter):
        # Mock running processes
        p1 = MagicMock()
        p1.info = {'name': 'chrome.exe'}
        
        p2 = MagicMock()
        p2.info = {'name': 'notepad.exe'}
        
        mock_process_iter.return_value = [p1, p2]
        
        res = panic_wipe()
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["killed"], 1) # chrome is killed, notepad is not in target list
        p1.kill.assert_called_once()
        p2.kill.assert_not_called()

    @patch("actions.usb_monitor.psutil.disk_partitions")
    def test_usb_monitor(self, mock_partitions):
        # Mock partition details
        part1 = MagicMock(device="D:\\", opts="removable", fstype="NTFS")
        part2 = MagicMock(device="C:\\", opts="fixed", fstype="NTFS")
        mock_partitions.return_value = [part1, part2]
        
        drives = get_drives()
        self.assertIn("D:\\", drives)
        self.assertNotIn("C:\\", drives)
        
        # Test toggle_usb
        res = toggle_usb(True)
        self.assertEqual(res["status"], "ok")
        self.assertTrue(res["active"])

    @patch("actions.edge_tts_helper.generate_speech")
    def test_iot_controller(self, mock_speech):
        mock_speech.return_value = True
        
        # Test initial state retrieval
        state = get_iot_state()
        self.assertIn("study_lights", state)
        
        # Test toggle study lights
        initial_val = state["study_lights"]["enabled"]
        res = toggle_iot("study_lights")
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["state"]["study_lights"]["enabled"], not initial_val)
        self.assertIn("study lights", res["reply"].lower())

if __name__ == "__main__":
    unittest.main()

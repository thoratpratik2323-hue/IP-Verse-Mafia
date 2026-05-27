# tests/test_session.py
import unittest
from unittest.mock import patch
from core.session import _clean_transcript, _load_system_prompt

class TestSession(unittest.TestCase):
    def test_clean_transcript(self):
        self.assertEqual(_clean_transcript("Hello <ctrl3>world!"), "Hello world!")
        self.assertEqual(_clean_transcript("Hello \x00\x05world!"), "Hello world!")
        self.assertEqual(_clean_transcript("Ahem, hello world!"), "hello world!")
        self.assertEqual(_clean_transcript("ahem ahem hello world!"), "hello world!")
        self.assertEqual(_clean_transcript("  Hello world  "), "Hello world")

    def test_load_system_prompt_fallback(self):
        with patch("pathlib.Path.read_text", side_effect=Exception("File not found")):
            prompt = _load_system_prompt()
            self.assertIn("IP Prime", prompt)
            self.assertIn("advanced personal AI assistant", prompt)

    def test_load_system_prompt_success(self):
        mock_base_prompt = "You are IP Prime. Your master is Pratik Thorat."
        mock_personality = '{"name": "Jarvis", "humour": 80, "energy": 50, "sarcasm": 20, "professionalism": 90, "creativity": 60}'
        
        with patch("pathlib.Path.read_text") as mock_read, \
             patch("pathlib.Path.exists", return_value=True):
            
            mock_read.side_effect = [mock_base_prompt, mock_personality]
            
            prompt = _load_system_prompt()
            self.assertIn("Jarvis", prompt)
            self.assertIn("Humour Level (HIGH)", prompt)
            self.assertIn("Your custom synthesised core name is: Jarvis", prompt)

if __name__ == "__main__":
    unittest.main()

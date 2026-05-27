"""
test_router.py — Zero-dependency unit tests for NVIDIA NIM router and client.
"""

from __future__ import annotations

import sys
import unittest
from unittest.mock import patch, MagicMock

# Inject mocks into sys.modules to simulate external SDKs without installation
mock_openai = MagicMock()
mock_genai = MagicMock()
# Ensure that 'from google import genai' returns the configured mock
mock_genai.genai = mock_genai

sys.modules['openai'] = mock_openai
sys.modules['google'] = mock_genai
sys.modules['google.genai'] = mock_genai

# Now import modules under test
from core.intent_router import is_coding_task
from core.nvidia_client import ask_nvidia

class TestIntentRouter(unittest.TestCase):

    def setUp(self):
        # Reset mocks
        mock_openai.reset_mock()
        mock_genai.reset_mock()
        # Keep genai linked
        mock_genai.genai = mock_genai

    def test_coding_keyword_fast_path(self):
        # Keywords should immediately return True without calling Gemini API
        self.assertTrue(is_coding_task("write a function to add numbers"))
        self.assertTrue(is_coding_task("debug this python traceback"))
        self.assertTrue(is_coding_task("why is this loop not working"))
        
        # Verify mock Gemini client was never called
        mock_genai.Client.assert_not_called()

    @patch('core.session._get_api_key', return_value="dummy_key")
    def test_ambiguous_gemini_fallback_yes(self, mock_get_key):
        # Set up mock response
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "YES"
        mock_client.models.generate_content.return_value = mock_response

        # Ambiguous message that doesn't match keyword
        self.assertTrue(is_coding_task("Can you make the array reverse?"))
        mock_genai.Client.assert_called_once()
        mock_client.models.generate_content.assert_called_once()

    @patch('core.session._get_api_key', return_value="dummy_key")
    def test_ambiguous_gemini_fallback_no(self, mock_get_key):
        # Set up mock response
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "NO"
        mock_client.models.generate_content.return_value = mock_response

        # Ambiguous message that doesn't match keyword
        self.assertFalse(is_coding_task("How is the weather today?"))
        mock_genai.Client.assert_called_once()
        mock_client.models.generate_content.assert_called_once()

    @patch.dict('os.environ', {'NVIDIA_API_KEY': 'dummy_nvidia_key'})
    def test_nvidia_client_streaming(self):
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        
        # Mock streaming iterator
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "def "
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = "add():"
        
        mock_client.chat.completions.create.return_value = [chunk1, chunk2]

        res = ask_nvidia("write addition function")
        self.assertEqual(res, "def add():")
        mock_openai.OpenAI.assert_called_once()

if __name__ == '__main__':
    unittest.main()

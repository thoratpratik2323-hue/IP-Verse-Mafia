# tests/test_memory.py
import unittest
from unittest.mock import patch
from memory.memory_manager import update_memory, _empty_memory, remember, forget

class TestMemory(unittest.TestCase):
    def test_empty_memory(self):
        mem = _empty_memory()
        self.assertIsInstance(mem, dict)
        self.assertIn("identity", mem)
        self.assertIn("preferences", mem)
        self.assertIn("notes", mem)

    def test_update_memory(self):
        with patch("memory.memory_manager.load_memory") as mock_load, \
             patch("memory.memory_manager.save_memory") as mock_save:
            
            mock_mem = _empty_memory()
            mock_load.return_value = mock_mem
            
            updates = {
                "preferences": {
                    "favorite_food": {"value": "Pizza", "updated": "2026-05-27"}
                }
            }
            
            res = update_memory(updates)
            self.assertEqual(res["preferences"]["favorite_food"]["value"], "Pizza")
            mock_save.assert_called_once()

    def test_remember_note(self):
        with patch("memory.memory_manager.load_memory") as mock_load, \
             patch("memory.memory_manager.save_memory") as mock_save:
             
             mock_mem = _empty_memory()
             mock_load.return_value = mock_mem
             
             msg = remember("sister_name", "Priya", "relationships")
             self.assertIn("Remembered", msg)
             self.assertEqual(mock_mem["relationships"]["sister_name"]["value"], "Priya")
             mock_save.assert_called_once()

    def test_forget_note(self):
        with patch("memory.memory_manager.load_memory") as mock_load, \
             patch("memory.memory_manager.save_memory") as mock_save:
             
             mock_mem = _empty_memory()
             mock_mem["notes"]["temp_note"] = {"value": "Will delete", "updated": "2026"}
             mock_load.return_value = mock_mem
             
             msg = forget("temp_note", "notes")
             self.assertIn("Forgotten", msg)
             self.assertNotIn("temp_note", mock_mem["notes"])
             mock_save.assert_called_once()

if __name__ == "__main__":
    unittest.main()

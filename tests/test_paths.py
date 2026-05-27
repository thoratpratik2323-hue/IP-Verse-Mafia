# tests/test_paths.py
import os
import unittest
import importlib
from pathlib import Path
from unittest.mock import patch

class TestPaths(unittest.TestCase):
    def test_path_defaults(self):
        import core.path_config
        importlib.reload(core.path_config)
        
        self.assertTrue(core.path_config.BASE_DIR.exists())
        self.assertEqual(core.path_config.CONFIG_DIR, core.path_config.BASE_DIR / "config")
        self.assertEqual(core.path_config.MEMORY_DIR, core.path_config.BASE_DIR / "memory")

    def test_path_env_var_override(self):
        custom_given_dir = "/tmp/custom_given"
        with patch.dict(os.environ, {"IP_GIVEN_DIR": custom_given_dir}):
            import core.path_config
            importlib.reload(core.path_config)
            
            self.assertEqual(core.path_config.IP_GIVEN_DIR, Path(custom_given_dir))
            self.assertEqual(core.path_config.IP_GIVEN_CODE_DIR, Path(custom_given_dir) / "code")

if __name__ == "__main__":
    unittest.main()

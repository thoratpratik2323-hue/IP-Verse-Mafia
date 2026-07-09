"""
core/plugin_loader.py — Plugin auto-discovery system for IP Prime OS.
Drop any .py file into the plugins/ directory with TOOL_NAME defined
and it will be auto-discovered and loaded.

Plugin file format:
    TOOL_NAME = "my_tool"
    TOOL_DESCRIPTION = "Does something cool"
    TOOL_SCHEMA = {"type": "object", "properties": {...}}
    def execute(args: dict) -> str: ...
"""

from __future__ import annotations
import sys
import importlib.util
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("plugin_loader")

PLUGINS_DIR = Path("plugins")

_REQUIRED_ATTRS = ("TOOL_NAME", "execute")


class PluginRegistry:
    """Registry of all loaded plugins."""

    def __init__(self):
        self._plugins: dict[str, Any] = {}   # name -> module
        self._loaded = False

    def load_all(self) -> int:
        """Scan plugins/ directory and load all valid plugins. Returns count loaded."""
        PLUGINS_DIR.mkdir(exist_ok=True)
        count = 0
        for path in sorted(PLUGINS_DIR.glob("*.py")):
            if path.name.startswith("_"):
                continue
            try:
                module = self._load_module(path)
                if all(hasattr(module, attr) for attr in _REQUIRED_ATTRS):
                    name = module.TOOL_NAME
                    self._plugins[name] = module
                    logger.info(f"[PluginLoader] ✓ Loaded plugin: {name} ({path.name})")
                    count += 1
                else:
                    logger.warning(f"[PluginLoader] Skipped {path.name} — missing TOOL_NAME or execute()")
            except Exception as e:
                logger.error(f"[PluginLoader] Failed to load {path.name}: {e}")
        self._loaded = True
        return count

    def _load_module(self, path: Path):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)  # type: ignore
        sys.modules[path.stem] = module
        spec.loader.exec_module(module)  # type: ignore
        return module

    def call(self, tool_name: str, args: dict) -> str:
        """Execute a plugin by name with given args."""
        if tool_name not in self._plugins:
            return f"❌ Plugin '{tool_name}' not found."
        try:
            return self._plugins[tool_name].execute(args)
        except Exception as e:
            logger.error(f"[Plugin:{tool_name}] Execute failed: {e}")
            return f"❌ Plugin {tool_name} failed: {e}"

    def get_tool_declarations(self) -> list[dict]:
        """Return Gemini-compatible tool declarations for all loaded plugins."""
        decls = []
        for name, mod in self._plugins.items():
            decls.append({
                "name": name,
                "description": getattr(mod, "TOOL_DESCRIPTION", f"Plugin: {name}"),
                "parameters": getattr(mod, "TOOL_SCHEMA", {"type": "object", "properties": {}}),
            })
        return decls

    def list_plugins(self) -> list[str]:
        return list(self._plugins.keys())

    def reload(self, plugin_name: str) -> bool:
        """Hot-reload a single plugin."""
        for path in PLUGINS_DIR.glob("*.py"):
            try:
                module = self._load_module(path)
                if hasattr(module, "TOOL_NAME") and module.TOOL_NAME == plugin_name:
                    self._plugins[plugin_name] = module
                    logger.info(f"[PluginLoader] Reloaded: {plugin_name}")
                    return True
            except Exception:
                pass
        return False


# Singleton
Plugins = PluginRegistry()

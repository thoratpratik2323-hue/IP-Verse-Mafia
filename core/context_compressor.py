"""
core/context_compressor.py — Automatic conversation context compression.
Every N turns, summarises past history into a single paragraph to prevent
Gemini context window overflow and reduce token costs.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("context_compressor")

COMPRESS_EVERY_N_TURNS = 20   # Compress after this many user turns
SUMMARY_PATH = Path("memory/context_summaries.json")


class ContextCompressor:
    """
    Tracks conversation turns and compresses old history into a summary
    injected as a PREVIOUS CONTEXT block in future system prompts.
    """

    def __init__(self, gemini_client=None):
        self._client = gemini_client   # google.genai client
        self._turn_count = 0
        self._current_summary: str = ""
        self._load_summary()

    def _load_summary(self):
        try:
            SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
            if SUMMARY_PATH.exists():
                data = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
                self._current_summary = data.get("summary", "")
                self._turn_count = data.get("turn_count", 0)
        except Exception:
            pass

    def _save_summary(self):
        try:
            SUMMARY_PATH.write_text(
                json.dumps({
                    "summary": self._current_summary,
                    "turn_count": self._turn_count
                }, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.debug(f"[ContextCompressor] Save failed: {e}")

    def tick(self) -> bool:
        """Increment turn counter. Returns True if compression should happen."""
        self._turn_count += 1
        return self._turn_count % COMPRESS_EVERY_N_TURNS == 0

    def compress(self, history: list[dict]) -> str:
        """
        Summarise the given conversation history into 2-3 sentences.
        Returns the summary string. Falls back to truncation if AI unavailable.
        """
        if not history:
            return self._current_summary

        # Build plain text of the last N turns
        text_turns = []
        for msg in history[-COMPRESS_EVERY_N_TURNS:]:
            role = msg.get("role", "")
            parts = msg.get("parts", [])
            content = ""
            if isinstance(parts, list):
                content = " ".join(
                    p.get("text", "") if isinstance(p, dict) else str(p)
                    for p in parts
                )
            elif isinstance(parts, str):
                content = parts
            if content.strip():
                text_turns.append(f"{role.upper()}: {content.strip()[:200]}")

        conversation_text = "\n".join(text_turns)

        summary = self._ai_summarise(conversation_text)
        if summary:
            self._current_summary = summary
            self._save_summary()
            logger.info(f"[ContextCompressor] Compressed {len(text_turns)} turns into summary.")
        return self._current_summary

    def _ai_summarise(self, text: str) -> str:
        """Use Gemini Flash to summarise conversation (cheap + fast)."""
        if not self._client:
            # Fallback: just return last 500 chars
            return f"[Context Summary] {text[-500:]}"
        try:
            resp = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    {"role": "user", "parts": [{
                        "text": (
                            "Summarise this conversation in 2-3 sentences. "
                            "Focus on: what was decided, what was built, what was asked.\n\n"
                            + text
                        )
                    }]}
                ]
            )
            return resp.text.strip()
        except Exception as e:
            logger.debug(f"[ContextCompressor] AI summarise failed: {e}")
            return ""

    def get_context_block(self) -> str:
        """Returns the PREVIOUS CONTEXT block to inject into the system prompt."""
        if not self._current_summary:
            return ""
        return (
            f"\n\nPREVIOUS CONTEXT (auto-compressed summary of older turns):\n"
            f"{self._current_summary}\n"
            "(Use this to maintain continuity. Do not repeat it to the user.)"
        )

    def reset(self):
        """Reset on new session."""
        self._turn_count = 0
        # Keep summary across sessions for continuity

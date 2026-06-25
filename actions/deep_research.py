# actions/deep_research.py
# SATURDAY Deep Research Module — JARVIS-inspired multi-source research synthesizer
# Inspired by Sam Manina's J.A.R.V.I.S. deep research capability (Arc Reactor research series)

from __future__ import annotations

import json
import time
from pathlib import Path
import sys

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
OUTPUT_DIR      = Path.home() / "Downloads" / "sat output"


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _ddg_search(query: str, max_results: int = 8) -> list[dict]:
    """Multi-source web search via DuckDuckGo (ddgs)."""
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title":   r.get("title",  ""),
                    "snippet": r.get("body",   ""),
                    "url":     r.get("href",   ""),
                })
        return results
    except Exception as e:
        print(f"[DeepResearch] ⚠️ DDG search failed: {e}")
        return []


def _gemini_research(topic: str, sub_queries: list[str], depth: str) -> str:
    """Use Gemini with Google Search grounding for deep research.
    
    Retries up to 2 times on 503/429, then gracefully returns empty string
    so the DDG fallback path kicks in automatically.
    """
    try:
        from google import genai

        api_key = _get_api_key()
        client  = genai.Client(api_key=api_key)

        depth_instruction = {
            "quick":    "Give a concise 2-3 paragraph overview with key facts.",
            "standard": "Give a thorough 4-6 paragraph analysis with specific data, statistics, and expert insights.",
            "deep":     "Give an extremely thorough, PhD-level analysis with detailed technical breakdown, multiple perspectives, historical context, current state-of-the-art, challenges, and future directions.",
        }.get(depth, "Give a thorough analysis with specific data and expert insights.")

        prompt = (
            f"Research topic: {topic}\n\n"
            f"{depth_instruction}\n\n"
            f"Cover these specific aspects:\n"
            + "\n".join(f"- {q}" for q in sub_queries) +
            "\n\nProvide concrete facts, numbers, and specific technical details. "
            "Cite sources where possible. Structure the response with clear sections."
        )

        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={"tools": [{"google_search": {}}]},
                )
                text = ""
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text:
                        text += part.text
                if text.strip():
                    return text.strip()
            except Exception as e:
                err_str = str(e)
                is_quota = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
                is_unavail = "503" in err_str or "UNAVAILABLE" in err_str
                if is_quota:
                    print(f"[DeepResearch] ⚠️ Gemini quota exhausted — switching to DDG-only mode")
                    return ""   # Skip immediately, no retry on quota
                if is_unavail and attempt < max_attempts:
                    print(f"[DeepResearch] ⚠️ Gemini unavailable (attempt {attempt}) — retrying in 3s")
                    time.sleep(3)
                    continue
                print(f"[DeepResearch] ⚠️ Gemini grounded search failed: {e}")
                return ""
        return ""

    except Exception as e:
        print(f"[DeepResearch] ⚠️ Gemini setup failed: {e}")
        return ""


def _openrouter_synthesize(topic: str, raw_data: str, depth: str, focus: str) -> str:
    """Use OpenRouter to synthesize and structure the research findings."""
    try:
        from or_client import client as or_client

        depth_instruction = {
            "quick":    "Write a concise 2-paragraph summary.",
            "standard": "Write a structured 5-8 paragraph research brief with sections.",
            "deep":     "Write a comprehensive multi-section research report (1000+ words) with Introduction, Background, Current State, Technical Analysis, Challenges, Opportunities, and Conclusion.",
        }.get(depth, "Write a structured research brief.")

        focus_note = f"\nSpecial focus area: {focus}" if focus else ""

        system = (
            "You are SATURDAY's Deep Research Engine — a JARVIS-class AI research synthesizer. "
            "Your role is to produce structured, insightful research reports from gathered data. "
            "Be precise, technical where appropriate, and always present findings clearly. "
            "Format with clear markdown headers (## for sections, ### for sub-sections)."
        )

        prompt = (
            f"Topic: {topic}{focus_note}\n\n"
            f"Raw research data:\n{raw_data[:6000]}\n\n"
            f"Task: {depth_instruction}\n\n"
            "Format: Use clear headers, bullet points for key facts, and a summary at the end. "
            "Begin with an executive summary, then dive into details."
        )

        result = or_client.chat(prompt, system=system, max_tokens=2048, temperature=0.3)
        return result

    except Exception as e:
        print(f"[DeepResearch] ⚠️ OpenRouter synthesis failed: {e}")
        return raw_data[:3000]  # Return raw data if synthesis fails


def _generate_sub_queries(topic: str, focus: str) -> list[str]:
    """Generate targeted sub-queries for comprehensive research coverage."""
    try:
        from or_client import client as or_client
        focus_note = f" with focus on: {focus}" if focus else ""
        prompt = (
            f"Generate 5 specific research sub-questions for: '{topic}'{focus_note}\n"
            "These should cover: current state, technical details, challenges, key players, and future outlook.\n"
            "Return as a JSON array of strings. Example: [\"question 1\", \"question 2\", ...]"
        )
        raw = or_client.chat(prompt, system="Return ONLY a JSON array. No other text.", max_tokens=300, temperature=0.2)
        import re
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"[DeepResearch] ⚠️ Sub-query generation failed: {e}")

    # Fallback generic sub-queries
    return [
        f"What is the current state of {topic}?",
        f"What are the key technical challenges in {topic}?",
        f"Who are the leading experts and organizations working on {topic}?",
        f"What are recent breakthroughs in {topic}?",
        f"What is the future outlook for {topic}?",
    ]


def _save_report(topic: str, report: str, save: bool) -> str | None:
    """Save research report to file."""
    if not save:
        return None
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        safe_topic = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic)[:50].strip()
        timestamp  = time.strftime("%Y%m%d_%H%M%S")
        filename   = f"research_{safe_topic}_{timestamp}.md"
        filepath   = OUTPUT_DIR / filename

        header = (
            f"# Deep Research Report\n"
            f"**Topic:** {topic}\n"
            f"**Generated by:** S.A.T.U.R.D.A.Y Deep Research Engine\n"
            f"**Date:** {time.strftime('%B %d, %Y at %I:%M %p')}\n\n"
            f"---\n\n"
        )

        filepath.write_text(header + report, encoding="utf-8")
        print(f"[DeepResearch] 📄 Report saved: {filepath}")
        return str(filepath)
    except Exception as e:
        print(f"[DeepResearch] ⚠️ Save failed: {e}")
        return None


def deep_research(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    """
    SATURDAY Deep Research Engine.
    Multi-source, multi-query comprehensive research synthesizer.
    """
    params = parameters or {}
    topic  = params.get("topic", "").strip()
    focus  = params.get("focus", "").strip()
    depth  = params.get("depth", "standard").lower().strip()
    save   = params.get("save", True)

    if not topic:
        return "Please provide a research topic, sir."

    if depth not in ("quick", "standard", "deep"):
        depth = "standard"

    print(f"[DeepResearch] 🔬 Starting {depth} research on: {topic!r}")
    if player:
        player.write_log(f"[Research] 🔬 {topic}")

    # ── Step 1: Generate targeted sub-queries ──────────────────────────────
    if player:
        player.set_activity("GENERATING RESEARCH QUERIES")
    sub_queries = _generate_sub_queries(topic, focus)
    print(f"[DeepResearch] 📋 Sub-queries: {sub_queries}")

    # ── Step 2: Multi-source web search ────────────────────────────────────
    if player:
        player.set_activity("SEARCHING MULTIPLE SOURCES")

    all_snippets = []

    # Gemini grounded search (main source)
    gemini_result = _gemini_research(topic, sub_queries, depth)
    if gemini_result:
        all_snippets.append(f"## Primary Research (Google Search Grounded)\n{gemini_result}")

    # DuckDuckGo supplemental search for each sub-query
    if depth in ("standard", "deep"):
        ddg_results = _ddg_search(topic, max_results=6)
        if ddg_results:
            ddg_text = "\n\n".join(
                f"**{r['title']}**\n{r['snippet']}\nSource: {r['url']}"
                for r in ddg_results if r.get("snippet")
            )
            all_snippets.append(f"## Web Sources\n{ddg_text}")

        # Additional focused search if we have focus area
        if focus:
            focus_results = _ddg_search(f"{topic} {focus}", max_results=4)
            if focus_results:
                focus_text = "\n\n".join(
                    f"**{r['title']}**\n{r['snippet']}"
                    for r in focus_results if r.get("snippet")
                )
                all_snippets.append(f"## Focused Research: {focus}\n{focus_text}")

    raw_data = "\n\n---\n\n".join(all_snippets)

    if not raw_data.strip():
        return f"Sir, I was unable to gather research data on '{topic}'. Please check your internet connection."

    # ── Step 3: Synthesize with OpenRouter ─────────────────────────────────
    if player:
        player.set_activity("SYNTHESIZING RESEARCH")
    print("[DeepResearch] 🧠 Synthesizing findings...")

    if gemini_result and depth == "quick":
        # For quick mode, Gemini result alone is sufficient
        final_report = gemini_result
    else:
        final_report = _openrouter_synthesize(topic, raw_data, depth, focus)

    # ── Step 4: Save report ────────────────────────────────────────────────
    saved_path = _save_report(topic, final_report, save)

    # ── Step 5: Prepare response ───────────────────────────────────────────
    word_count = len(final_report.split())
    save_msg   = f" Report saved to Downloads/sat output." if saved_path else ""

    # For voice response: give a spoken summary + send full report to log
    if player:
        player.write_log(f"[Research Complete] {word_count} words on: {topic}")
        # Show full report in the console log
        player.write_log(final_report[:1500] + ("..." if len(final_report) > 1500 else ""))

    # Return a brief spoken summary + first key paragraph for voice
    first_para = final_report.split("\n\n")[0] if "\n\n" in final_report else final_report[:500]
    # Clean markdown headers for voice
    import re
    voice_summary = re.sub(r"^#{1,3}\s+", "", first_para, flags=re.MULTILINE).strip()
    if len(voice_summary) > 600:
        voice_summary = voice_summary[:600] + "..."

    depth_label = {"quick": "quick overview", "standard": "full research brief", "deep": "comprehensive report"}.get(depth, "research")
    return (
        f"Deep research complete on '{topic}'.{save_msg} Here's the {depth_label}: "
        f"{voice_summary}"
    )

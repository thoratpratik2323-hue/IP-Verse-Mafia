"""Advanced AI writing, translation, and summarization."""
from __future__ import annotations

from prime_platform.config import load_prime_config
from prime_platform.local_first import run_local_prompt


def _cloud_generate(prompt: str) -> str:
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        import google.generativeai as genai
    from pathlib import Path
    import json

    config_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    key = cfg.get("coding_api_key") or cfg.get("gemini_api_key", "")
    genai.configure(api_key=key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    resp = model.generate_content(prompt)
    return (resp.text or "").strip()


def prime_writing(
    action: str,
    text: str = "",
    target_language: str = "English",
    style: str = "clear",
    topic: str = "",
) -> str:
    action = (action or "summarize").strip().lower()
    text = (text or "").strip()
    cfg = load_prime_config()
    use_local = cfg.get("local_first", {}).get("enabled", False)

    prompts = {
        "summarize": (
            f"Summarize the following text concisely in {target_language}. "
            f"Style: {style}.\n\n{text}"
        ),
        "translate": (
            f"Translate the following text to {target_language}. "
            f"Preserve tone and meaning. Output only the translation.\n\n{text}"
        ),
        "write": (
            f"Write original content in {target_language} about: {topic or text}. "
            f"Style: {style}. Length: medium article."
        ),
        "rewrite": (
            f"Rewrite the following in {target_language} with style '{style}'. "
            f"Improve clarity and flow.\n\n{text}"
        ),
        "proofread": (
            f"Proofread and correct grammar/spelling. Return the fixed text only.\n\n{text}"
        ),
        "expand": (
            f"Expand the following into a longer, richer version in {target_language}. "
            f"Style: {style}. Add detail but stay on topic.\n\n{text}"
        ),
        "bullets": (
            f"Convert the following into clear bullet points in {target_language}.\n\n{text}"
        ),
        "email": (
            f"Draft a professional email in {target_language}. Style: {style}. "
            f"Context/topic: {topic or text}\n\nAdditional notes:\n{text}"
        ),
        "tone": (
            f"Rewrite the following in {target_language} with tone '{style}' "
            f"(e.g. formal, friendly, technical). Output only the rewritten text.\n\n{text}"
        ),
    }

    if action not in prompts:
        return (
            "Actions: summarize | translate | write | rewrite | proofread | "
            "expand | bullets | email | tone\n"
            "Provide text (or topic for write/email)."
        )

    if action in ("write", "email") and not text and not topic:
        return f"Provide topic or text for {action} action."
    if action not in ("write", "email") and not text:
        return f"Provide text for {action}."

    prompt = prompts[action]
    if use_local:
        result = run_local_prompt(prompt)
        backend = "local (Ollama)"
    else:
        try:
            result = _cloud_generate(prompt)
            backend = "cloud (Gemini Flash)"
        except Exception as e:
            return f"Writing suite failed: {e}"

    return f"═══ {action.upper()} ({backend}) ═══\n\n{result}"

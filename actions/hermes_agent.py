# actions/hermes_agent.py
# IP Prime — Hermes-Style Agentic Intelligence Engine
# Implements Hermes agent capabilities via Gemini:
#   1. Agentic multi-step planning
#   2. Self-reflection / self-critique
#   3. Chain-of-thought reasoning
#   4. Tool orchestration (auto-chain multiple tools)
#   5. Structured JSON reasoning

import json
import time
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).resolve().parent.parent
API_CONFIG     = BASE_DIR / "config" / "api_keys.json"
HERMES_MODEL   = "gemini-2.5-flash"
LOG_FILE       = Path.home() / ".ipprime" / "hermes_log.jsonl"

MAX_PLAN_STEPS = 8
MAX_REFLECT    = 2


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_model():
    from actions.prime_utils import UnifiedGenerativeModel
    return UnifiedGenerativeModel(HERMES_MODEL, category="coding")


def _log(entry: dict):
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _call(prompt: str) -> str:
    model = _get_model()
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"[Hermes] Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 1: CHAIN-OF-THOUGHT REASONING
# Think step by step before answering — like Hermes' <think> tags
# ═══════════════════════════════════════════════════════════════════════════════

def chain_of_thought(question: str, depth: str = "standard", player=None) -> str:
    """
    Hermes-style Chain of Thought reasoning.
    Thinks through the problem step by step before giving final answer.
    depth: quick | standard | deep
    """
    depth_map = {
        "quick":    3,
        "standard": 5,
        "deep":     8,
    }
    steps = depth_map.get(depth, 5)

    if player:
        player.write_log(f"[Hermes] Chain-of-Thought ({depth})...")

    prompt = f"""You are an expert reasoning engine (Hermes-style). 
Think through this problem carefully before answering.

QUESTION: {question}

INSTRUCTIONS:
- First, think step by step ({steps} thinking steps maximum)
- Label each step as: [THINK 1], [THINK 2], etc.
- After thinking, write [ANSWER] followed by your final, clear answer
- The [ANSWER] section should be concise and direct
- Speak in Hinglish style for IP Prime (Pratik Sir's assistant)

Format:
[THINK 1] ...your reasoning...
[THINK 2] ...continue reasoning...
...
[ANSWER] ...final answer in Hinglish...

Begin:"""

    result = _call(prompt)
    _log({"feature": "chain_of_thought", "question": question, "depth": depth, "ts": time.time()})

    # Extract just the answer for clean output, keep thinking as context
    lines = result.splitlines()
    thinking_lines = [l for l in lines if l.startswith("[THINK")]
    answer_lines   = []
    in_answer = False
    for l in lines:
        if l.startswith("[ANSWER]"):
            in_answer = True
        if in_answer:
            answer_lines.append(l.replace("[ANSWER]", "").strip())

    thinking_block = "\n".join(thinking_lines)
    answer_block   = " ".join(answer_lines).strip()

    return (
        f"### 🧠 Hermes Chain-of-Thought\n\n"
        f"**Reasoning Process:**\n{thinking_block}\n\n"
        f"**Final Answer:**\n{answer_block or result}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 2: AGENTIC TASK PLANNING
# Break any goal into executable steps — like Hermes agent planning
# ═══════════════════════════════════════════════════════════════════════════════

def agentic_plan(goal: str, execute: bool = False, player=None) -> str:
    """
    Hermes-style Agentic Planning.
    Takes a big goal and breaks it into clear executable steps.
    If execute=True, attempts to run each step using Prime tools.
    """
    if player:
        player.write_log(f"[Hermes] Planning: {goal[:60]}...")

    plan_prompt = f"""You are Hermes, an expert agentic planner for IP Prime (Pratik Sir's AI).
Your job: Break the goal into clear, executable steps.

GOAL: {goal}

OUTPUT FORMAT (strict JSON):
{{
  "goal_summary": "one sentence summary",
  "total_steps": <number>,
  "steps": [
    {{
      "step_number": 1,
      "action": "what to do",
      "tool": "which IP Prime tool to use (code_helper/file_explorer/web_search/none)",
      "params": {{"key": "value"}},
      "expected_outcome": "what success looks like",
      "priority": "high/medium/low"
    }}
  ],
  "dependencies": ["step X depends on step Y"],
  "estimated_time": "X minutes",
  "risks": ["potential issue 1"]
}}

Return ONLY valid JSON. No markdown, no backticks."""

    raw = _call(plan_prompt)

    # Clean JSON
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        plan = json.loads(raw)
    except Exception:
        # Fallback: return raw if JSON fails
        return f"### 📋 Hermes Agent Plan\n\nGoal: **{goal}**\n\n{raw}"

    _log({"feature": "agentic_plan", "goal": goal, "plan": plan, "ts": time.time()})

    # Format nicely
    lines = [
        f"### 📋 Hermes Agent Plan",
        f"**Goal:** {plan.get('goal_summary', goal)}",
        f"**Steps:** {plan.get('total_steps', '?')}  |  **Est. Time:** {plan.get('estimated_time', '?')}",
        "",
    ]

    for step in plan.get("steps", []):
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(step.get("priority", "medium"), "⚪")
        lines.append(f"{priority_icon} **Step {step['step_number']}:** {step['action']}")
        if step.get("tool") and step["tool"] != "none":
            lines.append(f"   → Tool: `{step['tool']}`")
        if step.get("expected_outcome"):
            lines.append(f"   ✓ Outcome: {step['expected_outcome']}")
        lines.append("")

    if plan.get("dependencies"):
        lines.append("**Dependencies:**")
        for dep in plan["dependencies"]:
            lines.append(f"  - {dep}")
        lines.append("")

    if plan.get("risks"):
        lines.append("**⚠️ Risks:**")
        for risk in plan["risks"]:
            lines.append(f"  - {risk}")

    if execute:
        lines.append("\n---\n**🤖 Auto-Execution Mode: ON**")
        lines.append("Pratik Sir, main steps execute karna shuru kar raha hoon...\n")
        # Execute steps using Prime tools
        results = _execute_plan_steps(plan.get("steps", []), goal, player)
        lines.append(results)

    return "\n".join(lines)


def _execute_plan_steps(steps: list, goal: str, player=None) -> str:
    """Auto-execute plan steps using Prime tools."""
    results = []
    for step in steps[:MAX_PLAN_STEPS]:
        tool   = step.get("tool", "none")
        action = step.get("action", "")
        params = step.get("params", {})

        if player:
            player.write_log(f"[Hermes] Executing Step {step.get('step_number')}: {action[:50]}")

        result_line = f"**Step {step.get('step_number')} — {action}**\n"

        try:
            if tool == "code_helper":
                from actions.code_helper import code_helper
                r = code_helper({"action": "write", "description": action, **params}, player=player)
                result_line += f"✅ {r[:200]}"

            elif tool == "file_explorer":
                from actions.file_explorer import file_explorer
                r = file_explorer({"action": params.get("action", "browse"), **params}, player=player)
                result_line += f"✅ {r[:200]}"

            elif tool == "web_search":
                from actions.web_search import web_search
                r = web_search({"query": action}, player=player)
                result_line += f"✅ {str(r)[:200]}"

            else:
                # No tool — just mark as noted
                result_line += f"📝 Noted (manual step)"

        except Exception as e:
            result_line += f"⚠️ Error: {e}"

        results.append(result_line)

    return "\n\n".join(results)


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 3: SELF-REFLECTION / SELF-CRITIQUE
# Review and improve its own output — Hermes' signature feature
# ═══════════════════════════════════════════════════════════════════════════════

def self_reflect(content: str, task: str = "", rounds: int = 1, player=None) -> str:
    """
    Hermes-style Self-Reflection.
    Reviews and critiques given content, then produces an improved version.
    rounds: how many times to self-critique (1 or 2)
    """
    if player:
        player.write_log(f"[Hermes] Self-reflecting ({rounds} round(s))...")

    rounds = min(rounds, MAX_REFLECT)
    current = content
    all_critiques = []

    for r in range(rounds):
        critique_prompt = f"""You are Hermes, a self-critical AI reviewer working for IP Prime (Pratik Sir's assistant).

ORIGINAL TASK: {task or "Review and improve the following content"}

CONTENT TO REVIEW:
{current}

INSTRUCTIONS:
1. Find ALL weaknesses: errors, missing info, unclear parts, inefficiencies
2. Rate quality: 1-10
3. Produce an IMPROVED version

OUTPUT FORMAT (JSON):
{{
  "quality_score": <1-10>,
  "weaknesses": ["weakness 1", "weakness 2"],
  "improvements_made": ["what was fixed"],
  "improved_content": "...the full improved version here..."
}}

Return ONLY valid JSON."""

        raw = _call(critique_prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            critique = json.loads(raw)
            all_critiques.append(critique)
            current = critique.get("improved_content", current)
        except Exception:
            all_critiques.append({"quality_score": "?", "weaknesses": [], "improvements_made": [], "improved_content": raw})
            current = raw

    _log({"feature": "self_reflect", "rounds": rounds, "ts": time.time()})

    # Format output
    lines = ["### 🪞 Hermes Self-Reflection\n"]
    for i, c in enumerate(all_critiques, 1):
        score = c.get("quality_score", "?")
        score_bar = "⭐" * int(score) if isinstance(score, int) else str(score)
        lines.append(f"**Round {i} Review** — Quality Score: {score_bar}/10")
        weaknesses = c.get("weaknesses", [])
        if weaknesses:
            lines.append("**Issues Found:**")
            for w in weaknesses:
                lines.append(f"  ❌ {w}")
        improvements = c.get("improvements_made", [])
        if improvements:
            lines.append("**Fixed:**")
            for imp in improvements:
                lines.append(f"  ✅ {imp}")
        lines.append("")

    lines.append("---")
    lines.append("**✨ Final Improved Version:**")
    lines.append(current)

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 4: STRUCTURED JSON REASONING
# Think and respond in structured format — Hermes excels at this
# ═══════════════════════════════════════════════════════════════════════════════

def structured_reason(query: str, output_schema: dict = None, player=None) -> str:
    """
    Hermes-style Structured Reasoning.
    Reasons through a query and returns a structured JSON response.
    Useful for: decisions, comparisons, analysis, research summaries.
    """
    if player:
        player.write_log(f"[Hermes] Structured reasoning: {query[:60]}...")

    default_schema = {
        "summary":        "brief answer",
        "key_points":     ["point 1", "point 2"],
        "pros":           ["advantage 1"],
        "cons":           ["disadvantage 1"],
        "recommendation": "what Pratik Sir should do",
        "confidence":     "high/medium/low",
        "next_steps":     ["step 1", "step 2"]
    }
    schema = output_schema or default_schema

    prompt = f"""You are Hermes, an expert analyst for IP Prime (Pratik Sir's AI).
Analyze the following and respond with structured JSON.

QUERY: {query}

OUTPUT SCHEMA:
{json.dumps(schema, indent=2)}

Fill every field. Be specific, practical, and helpful for Pratik Sir.
Respond in a mix of English and Hinglish where appropriate.
Return ONLY valid JSON."""

    raw = _call(prompt)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        data = json.loads(raw)
    except Exception:
        return f"### 🔍 Hermes Structured Analysis\n\n{raw}"

    _log({"feature": "structured_reason", "query": query, "ts": time.time()})

    # Pretty format
    lines = [f"### 🔍 Hermes Structured Analysis\n**Query:** {query}\n"]
    for key, val in data.items():
        label = key.replace("_", " ").title()
        if isinstance(val, list):
            lines.append(f"**{label}:**")
            for item in val:
                lines.append(f"  • {item}")
        else:
            lines.append(f"**{label}:** {val}")
        lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 5: TOOL ORCHESTRATION
# Automatically chain multiple Prime tools to complete a complex task
# ═══════════════════════════════════════════════════════════════════════════════

def orchestrate(goal: str, player=None) -> str:
    """
    Hermes-style Tool Orchestration.
    Analyzes a goal, decides which Prime tools to chain, runs them in sequence.
    This is the most powerful Hermes feature — full autonomous execution.
    """
    if player:
        player.write_log(f"[Hermes] Orchestrating: {goal[:60]}...")

    # Step 1: Decide which tools to chain
    decide_prompt = f"""You are Hermes Tool Orchestrator for IP Prime.
Given a goal, decide which tools to call in which order.

GOAL: {goal}

AVAILABLE TOOLS:
- code_helper: write/build/edit/run code
- file_explorer: browse/search/copy/move/delete files
- web_search: search the internet
- task_planner: manage tasks
- morning_briefer: briefing/schedule
- chain_of_thought: deep reasoning about a question

OUTPUT (JSON array, max 4 steps):
[
  {{"tool": "tool_name", "action": "action_name", "params": {{}}, "reason": "why"}},
  ...
]
Return ONLY valid JSON array."""

    raw = _call(decide_prompt)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        tool_chain = json.loads(raw)
        if not isinstance(tool_chain, list):
            raise ValueError("Not a list")
    except Exception:
        return f"### 🔗 Hermes Orchestrator\n\nCould not parse tool chain. Raw:\n{raw}"

    lines = [f"### 🔗 Hermes Tool Orchestration\n**Goal:** {goal}\n",
             f"**Tool Chain ({len(tool_chain)} steps):**\n"]

    results = []
    for i, step in enumerate(tool_chain[:4], 1):
        tool   = step.get("tool", "")
        action = step.get("action", "")
        params = step.get("params", {})
        reason = step.get("reason", "")

        lines.append(f"**Step {i}:** `{tool}` → `{action}` — _{reason}_")

        if player:
            player.write_log(f"[Hermes Orchestrate] Step {i}: {tool}.{action}")

        try:
            r = ""
            if tool == "code_helper":
                from actions.code_helper import code_helper
                r = code_helper({"action": action, **params}, player=player)

            elif tool == "file_explorer":
                from actions.file_explorer import file_explorer
                r = file_explorer({"action": action, **params}, player=player)

            elif tool == "task_planner":
                from actions.task_planner import task_planner
                r = task_planner({"action": action, **params}, player=player)

            elif tool == "chain_of_thought":
                r = chain_of_thought(params.get("question", goal), player=player)

            elif tool == "web_search":
                from actions.web_search import web_search
                r = str(web_search({"query": params.get("query", goal)}, player=player))

            else:
                r = f"Tool `{tool}` not available for auto-orchestration."

            result_preview = str(r)[:300] + ("..." if len(str(r)) > 300 else "")
            results.append(f"**Step {i} Result:**\n{result_preview}")

        except Exception as e:
            results.append(f"**Step {i} Error:** {e}")

    _log({"feature": "orchestrate", "goal": goal, "chain": tool_chain, "ts": time.time()})

    lines.append("")
    lines.extend(results)
    lines.append("\n---")
    lines.append("✅ Hermes Orchestration complete, Pratik Sir!")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DISPATCHER
# ═══════════════════════════════════════════════════════════════════════════════

def hermes_agent(parameters: dict, player=None) -> str:
    """
    Hermes Agent — IP Prime's advanced reasoning & agentic engine.

    Actions:
      think        — Chain-of-thought reasoning (step-by-step thinking)
      plan         — Agentic task planning (break goal into steps)
      plan_execute — Plan AND auto-execute steps
      reflect      — Self-reflection (review & improve content)
      analyze      — Structured JSON reasoning/analysis
      orchestrate  — Auto-chain multiple Prime tools for a goal
    """
    params = parameters or {}
    action = params.get("action", "think").lower().strip()

    if player:
        player.write_log(f"[HermesAgent] {action}")

    try:
        if action == "think":
            return chain_of_thought(
                question=params.get("question") or params.get("query", ""),
                depth=params.get("depth", "standard"),
                player=player,
            )

        elif action == "plan":
            return agentic_plan(
                goal=params.get("goal") or params.get("query", ""),
                execute=False,
                player=player,
            )

        elif action == "plan_execute":
            return agentic_plan(
                goal=params.get("goal") or params.get("query", ""),
                execute=True,
                player=player,
            )

        elif action == "reflect":
            return self_reflect(
                content=params.get("content", ""),
                task=params.get("task", ""),
                rounds=int(params.get("rounds", 1)),
                player=player,
            )

        elif action == "analyze":
            return structured_reason(
                query=params.get("query") or params.get("question", ""),
                player=player,
            )

        elif action == "orchestrate":
            return orchestrate(
                goal=params.get("goal") or params.get("query", ""),
                player=player,
            )

        else:
            return (
                f"Unknown action `{action}`.\n"
                "Available: think | plan | plan_execute | reflect | analyze | orchestrate"
            )

    except KeyError as e:
        return f"Missing parameter: {e}"
    except Exception as e:
        return f"Hermes Agent error ({action}): {e}"

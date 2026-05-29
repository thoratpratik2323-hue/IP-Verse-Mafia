import json
import re
import sys
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


PLANNER_PROMPT_TEMPLATE = """You are the planning module of IP Prime, a personal AI assistant. Your owner is Pratik Thorat.
Your job: break any user goal into a sequence of steps using ONLY the tools listed below.

ABSOLUTE RULES:
- NEVER use generated_code or write Python scripts. It does not exist.
- NEVER reference previous step results in parameters. Every step is independent.
- Use web_search for ANY information retrieval, research, or current data.
- Use file_controller to save content to disk.
- Max 5 steps. Use the minimum steps needed.

AVAILABLE TOOLS AND THEIR PARAMETERS:

{AVAILABLE_TOOLS}

EXAMPLES:

Goal: "research mechanical engineering and save it to a notepad file"
Steps:

web_search | query: "mechanical engineering overview definition history"
web_search | query: "mechanical engineering applications and future trends"
file_controller | action: write, path: desktop, name: mechanical_engineering.txt, content: "MECHANICAL ENGINEERING RESEARCH\n\nThis file will be filled with web research results."

Goal: "What is the price of Bitcoin"
Steps:

web_search | query: "Bitcoin price today USD"

Goal: "List the files on the desktop and find the largest 5 files"
Steps:

file_controller | action: list, path: desktop
file_controller | action: largest, path: desktop, count: 5

Goal: "Install PUBG from Steam"
Steps:

game_updater | action: install, platform: steam, game_name: "PUBG"

Goal: "Update all my Steam games"
Steps:

game_updater | action: update, platform: steam

Goal: "Send John a message on WhatsApp saying there is a meeting tomorrow"
Steps:

send_message | receiver: John, message_text: "There is a meeting tomorrow", platform: WhatsApp

Goal: "Open the clock and set a reminder for 30 minutes later"
Steps:

reminder | date: [today], time: [now+30min], message: "Reminder"

OUTPUT — return ONLY valid JSON, no markdown, no explanation, no code blocks:
{
  "goal": "...",
  "steps": [
    {
      "step": 1,
      "tool": "tool_name",
      "description": "what this step does",
      "parameters": {},
      "critical": true
    }
  ]
}
"""


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def create_plan(goal: str, context: str = "") -> dict:
    from agent.skills_manager import format_tools_for_prompt
    from actions.local_llm import is_offline_mode_active

    tools_str = format_tools_for_prompt()
    system_instruction = PLANNER_PROMPT_TEMPLATE.replace("{AVAILABLE_TOOLS}", tools_str)

    user_input = f"Goal: {goal}"
    if context:
        user_input += f"\n\nContext: {context}"

    if is_offline_mode_active():
        print("[Planner] [Offline] Routing planning task to local Ollama...")
        try:
            from actions.local_llm import generate_local_response
            text = generate_local_response(user_input, system_instruction)
            text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
            plan = json.loads(text)
            if "steps" not in plan or not isinstance(plan["steps"], list):
                raise ValueError("Invalid plan structure from local LLM")
            print(f"[Planner] [Offline] [OK] Plan: {len(plan['steps'])} steps")
            return plan
        except Exception as e:
            print(f"[Planner] [Offline] [Error] Ollama planning failed: {e}")
            return _fallback_plan(goal)

    from google import genai
    client = genai.Client(api_key=_get_api_key())
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=user_input,
            config=genai.types.GenerateContentConfig(system_instruction=system_instruction)
        )
        text     = response.text.strip()
        text     = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

        plan = json.loads(text)

        if "steps" not in plan or not isinstance(plan["steps"], list):
            raise ValueError("Invalid plan structure")

        for step in plan["steps"]:
            if step.get("tool") in ("generated_code",):
                print(f"[Planner] [Warning] generated_code detected in step {step.get('step')} — replacing with web_search")
                desc = step.get("description", goal)
                step["tool"] = "web_search"
                step["parameters"] = {"query": desc[:200]}

        print(f"[Planner] [OK] Plan: {len(plan['steps'])} steps")
        for s in plan["steps"]:
            print(f"  Step {s['step']}: [{s['tool']}] {s['description']}")

        return plan

    except json.JSONDecodeError as e:
        print(f"[Planner] [Error] JSON parse failed: {e}")
        return _fallback_plan(goal)
    except Exception as e:
        print(f"[Planner] [Error] Planning failed: {e}")
        return _fallback_plan(goal)


def _fallback_plan(goal: str) -> dict:
    print("[Planner] [Fallback] Fallback plan")
    return {
        "goal": goal,
        "steps": [
            {
                "step": 1,
                "tool": "web_search",
                "description": f"Search for: {goal}",
                "parameters": {"query": goal},
                "critical": True
            }
        ]
    }


def replan(goal: str, completed_steps: list, failed_step: dict, error: str) -> dict:
    from agent.skills_manager import format_tools_for_prompt
    from actions.local_llm import is_offline_mode_active

    tools_str = format_tools_for_prompt()
    system_instruction = PLANNER_PROMPT_TEMPLATE.replace("{AVAILABLE_TOOLS}", tools_str)

    completed_summary = "\n".join(
        f"  - Step {s['step']} ({s['tool']}): DONE" for s in completed_steps
    )

    prompt = f"""Goal: {goal}

Already completed:
{completed_summary if completed_summary else '  (none)'}

Failed step: [{failed_step.get('tool')}] {failed_step.get('description')}
Error: {error}

Create a REVISED plan for the remaining work only. Do not repeat completed steps."""

    if is_offline_mode_active():
        print("[Planner] [Offline] Routing replan task to local Ollama...")
        try:
            from actions.local_llm import generate_local_response
            text = generate_local_response(prompt, system_instruction)
            text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
            plan = json.loads(text)
            print(f"[Planner] [Offline] [Revised] Revised plan: {len(plan.get('steps', []))} steps")
            return plan
        except Exception as e:
            print(f"[Planner] [Offline] [Error] Ollama replanning failed: {e}")
            return _fallback_plan(goal)

    from google import genai
    client = genai.Client(api_key=_get_api_key())
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(system_instruction=system_instruction)
        )
        text     = response.text.strip()
        text     = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        plan     = json.loads(text)

        for step in plan.get("steps", []):
            if step.get("tool") == "generated_code":
                step["tool"] = "web_search"
                step["parameters"] = {"query": step.get("description", goal)[:200]}

        print(f"[Planner] [Revised] Revised plan: {len(plan['steps'])} steps")
        return plan
    except Exception as e:
        print(f"[Planner] [Error] Replan failed: {e}")
        return _fallback_plan(goal)
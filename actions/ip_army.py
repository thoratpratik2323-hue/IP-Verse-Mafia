"""
ip_army.py — Orchestrates the IP AI Army multi-agent pipeline for IP Prime.
Agents included: IP Scout, IP Scribe, IP Codex, IP Lexicon, IP Audit.
"""

import json
import re
from pathlib import Path
from google import genai
from actions.prime_utils import get_base_dir, get_api_key

def clean_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\r?\n?", "", text)
    text = re.sub(r"\r?\n?```\s*$", "", text)
    return text.strip()

def run_ip_army(project_path_str: str, instruction: str, player=None) -> str:
    """
    Main routine coordinating the IP AI Army division.
    Decomposes instructions and routes tasks to specialized agents.
    """
    # 0. Check if this is a request to list or show the IP Army team members
    inst_lower = (instruction or "").strip().lower()
    if inst_lower in ("list", "show", "team", "agents", "members", "introduce", "intro", "show team", "list team", "show agents", "list agents"):
        roster_path = Path(__file__).resolve().parent.parent / "docs" / "ip_army_roster.md"
        if roster_path.exists():
            return roster_path.read_text(encoding="utf-8")
        return "IP AI Army roster file not found."

    def log(msg: str):
        print(f"[IP Army] {msg}")
        if player:
            player.write_log(f"[IP Army] {msg}")

    def think(msg: str):
        if player and hasattr(player, "write_thought"):
            player.write_thought(msg)

    # 1. Resolve Project Path
    if not project_path_str or project_path_str.strip() == "":
        proj_path = Path(get_base_dir()) / "CODING PROJECTS"
    else:
        proj_path = Path(project_path_str).expanduser().resolve()
        
    proj_path.mkdir(parents=True, exist_ok=True)
    log(f"Initializing IP AI Army in workspace: {proj_path}")
    think(f"Mobilizing IP AI Army for workspace: {proj_path.name}")

    # 2. Initialize GenAI client
    api_key = get_api_key()
    if not api_key:
        return "Error: Gemini API Key is missing. Configure it in config/api_keys.json, sir!"
    client = genai.Client(api_key=api_key)

    # 3. Step 1: Manager Planning (IP Prime Decomposes the Task)
    think("IP Prime decomposing task requirements into agent pipelines...")
    planner_prompt = f"""
    You are IP Prime, the personal AI assistant. The user (who is the Commander) wants to accomplish: "{instruction}".
    Split this goal into a sequential plan of 2 to 4 subtasks.
    Assign each subtask to ONE of these specialized AI army agents:
    - ip_scout: For research, gathering facts, competitor telemetry, summarization.
    - ip_scribe: For writing articles, blogs, copy, emails, documentations.
    - ip_codex: For code, HTML pages, CSS layout design, Python scripts, algorithms.
    - ip_translator: For translations or localized copies (Lexicon).
    - ip_audit: For code review, QA checks, loop tests, security/accessibility reviews.
    
    Respond ONLY with a valid JSON array of objects representing steps. Do NOT wrap in markdown blocks, just return raw JSON.
    Example:
    [
      {{"id":"1", "agent":"ip_scout", "title":"Competitive Analysis", "desc":"Gather structures and features of tech landing pages."}},
      {{"id":"2", "agent":"ip_scribe", "title":"Draft Section Copy", "desc":"Write headlines and value propositions for the page."}}
    ]"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=planner_prompt
        )
        cleaned_json = clean_fences(response.text)
        plan = json.loads(cleaned_json)
        if not isinstance(plan, list):
            raise ValueError("Planner response is not a JSON list.")
    except Exception as e:
        log(f"Warning: Planner failed to generate JSON plan: {e}. Falling back to default pipeline.")
        # Fallback plan based on task keywords
        if any(w in instruction.lower() for w in ["code", "page", "script", "html"]):
            plan = [
                {"id": "1", "agent": "ip_scout", "title": "Telemetry Research", "desc": f"Gather requirements and competitor analysis for: {instruction}"},
                {"id": "2", "agent": "ip_codex", "title": "Write Source Code", "desc": f"Write clean source code files for: {instruction}"},
                {"id": "3", "agent": "ip_audit", "title": "QA Security Inspection", "desc": f"Audit code for loopholes, bugs, and edge cases."}
            ]
        else:
            plan = [
                {"id": "1", "agent": "ip_scout", "title": "Telemetry Research", "desc": f"Gather research data and summaries for: {instruction}"},
                {"id": "2", "agent": "ip_scribe", "title": "Compile Content Draft", "desc": f"Write detailed markdown files and draft contents for: {instruction}"},
                {"id": "3", "agent": "ip_translator", "title": "Translate Telemetry", "desc": f"Translate final contents into Spanish or localized languages."}
            ]

    # Log plan
    plan_desc = "\n".join([f"  - Step {p['id']} [{p['agent'].upper()}]: {p['title']}" for p in plan])
    log(f"Commander, I have analyzed your request. As IP Prime, I have compiled the following delegation plan:\n{plan_desc}\n\nInitiating specialized division...")
    
    cumulative_context = f"Commander Instruction: {instruction}\n\n"

    # Agent System Prompt Library
    agent_system_prompts = {
      'ip_scout': "You are IP Scout v1.1. Your specialization is gathering facts, structuring research, summarizing search results, and verifying reference data. Provide clear, well-structured research notes, lists, and summary telemetries. Refuse speculation, write only facts.",
      'ip_scribe': "You are IP Scribe v1.3. Your specialization is content writing, drafting marketing copy, headlines, articles, essays, and email newsletters. Create engaging, high-quality text, formatting with clean markdown headers and rich vocabulary.",
      'ip_codex': "You are IP Codex v1.5. Your specialization is code construction, writing algorithms, scripts (Python, JS, Bash), and HTML/CSS web layouts. Write clean, commented, valid code blocks inside standard markdown blocks. Avoid writing chat fillers, prioritize delivery.",
      'ip_translator': "You are IP Lexicon v1.0. Your specialization is language translation and cultural localization. Translate the provided source texts accurately into the requested languages, preserving tone, formatting, and markdown tags.",
      'ip_audit': "You are IP Audit v1.2. Your specialization is quality assurance, checking code for loops and vulnerabilities, reviewing copy for clarity, checking WCAG accessibility standards, and providing structured suggestion reports."
    }

    # 4. Step 2: Loop through specialist tasks
    for step in plan:
        agent_key = step["agent"]
        step_id = step["id"]
        title = step["title"]
        desc = step["desc"] if "desc" in step else step.get("description", "")
        
        log(f"Deploying agent [{agent_key.upper()}] to work on subtask: {title}...")
        think(f"Agent [{agent_key.upper()}] active on step {step_id}: {title}...")
        
        sys_prompt = agent_system_prompts.get(agent_key, "You are a specialized agentic unit of the IP AI Army.")
        
        agent_prompt = f"""
        Your assigned task: {desc}
        
        Previous compiled context:
        {cumulative_context}

        Complete the task and format your output as a file.
        IMPORTANT: Your final output must start with a header containing the file name, followed by the content:
        ===FILE_NAME===
        filename.ext
        ===FILE_CONTENT===
        file content here...
        """

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=agent_prompt,
                config=genai.types.GenerateContentConfig(system_instruction=sys_prompt)
            )
            response_text = response.text.strip()
            
            # Parse filename and content
            file_name = f"{agent_key}_task_{step_id}.md"
            file_content = response_text
            
            if "===FILE_NAME===" in response_text:
                parts = response_text.split("===FILE_CONTENT===")
                name_part = parts[0].split("===FILE_NAME===")[1].strip()
                if name_part:
                    file_name = name_part
                if len(parts) > 1:
                    file_content = parts[1].strip()
            
            file_content = clean_fences(file_content)
            
            # Write file to disk
            file_path = proj_path / file_name
            file_path.write_text(file_content, encoding="utf-8")
            log(f"Subtask {step_id} complete: Compiled file [{file_name}] inside workspace directory.")
            
            # Update context for subsequent agents
            cumulative_context += f"\n--- Output of Step {step_id} ({file_name}) ---\n{file_content}\n"
            
        except Exception as e:
            log(f"Warning: Agent [{agent_key.upper()}] failed step {step_id}: {e}")
            cumulative_context += f"\n--- Step {step_id} failed: {e} ---\n"

    # 5. Step 3: Commander Final Compilation
    think("IP Prime synthesizing final division summary...")
    final_prompt = "You are IP Prime. Synthesize a final response to the user (Commander) summarizing what the AI army has completed and detailing the files created."
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=cumulative_context,
            config=genai.types.GenerateContentConfig(system_instruction=final_prompt)
        )
        final_summary = response.text.strip()
        log("Orchestration completed successfully, sir!")
        return final_summary
    except Exception as e:
        log(f"Error compiling final summary: {e}")
        return f"Orchestration completed, sir! Division files generated in workspace directory: {proj_path}"

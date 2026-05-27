"""
design_extractor.py — Parses and packages web design systems directly from URLs or local projects.

This is a standard action module for the IP Prime personal assistant suite.
"""

# design_extractor.py
import json
import sys
import subprocess
import re
from pathlib import Path

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

def _get_api_key() -> str:
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)["gemini_api_key"]
    except Exception:
        return ""

def design_extractor(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    SkillUI Design Extractor Action:
    Runs the 'npx skillui' static analyzer CLI tool to extract Design Systems
    and packaged .skill configurations from live websites, local codebases, or Git repositories.
    """
    params = parameters or {}
    source_type = params.get("source_type", "").lower().strip()
    target = params.get("target", "").strip()
    mode = params.get("mode", "default").lower().strip()
    name = params.get("name", "").strip()

    if not source_type or not target:
        return "Pratik Sir, please provide both 'source_type' (url | dir | repo) and a 'target' to analyze."

    if source_type not in ["url", "dir", "repo"]:
        return f"Invalid source_type '{source_type}', sir. Must be one of: url, dir, repo."

    if mode not in ["default", "ultra"]:
        mode = "default"

    # Normalize name or generate a safe default from the target
    if not name:
        # Get last part of path/URL
        clean_target = re.sub(r'https?://', '', target)
        clean_target = re.sub(r'[^a-zA-Z0-9_\-]', '_', clean_target)
        name = clean_target.strip("_")[:30] or "extracted_design"

    # Set up output path
    out_dir = BASE_DIR / "awesome_repos" / "extracted_skills" / name
    out_dir.mkdir(parents=True, exist_ok=True)

    if player:
        player.write_log(f"[SkillUI Extractor] Starting design extraction for {target} ({source_type}) into {name}")

    print("[SkillUI Extractor] [START] Running design extraction...")
    print(f"  Source Type: {source_type}")
    print(f"  Target:      {target}")
    print(f"  Mode:        {mode}")
    print(f"  Output Dir:  {out_dir}")

    # Build command line
    cmd = [
        "cmd.exe", "/c", "npx", "skillui",
        "--format", "both",
        "--mode", mode,
        "--out", str(out_dir),
        "--name", name
    ]

    # Append source flags
    if source_type == "url":
        # Make sure URL has a schema
        if not target.startswith("http://") and not target.startswith("https://"):
            target = "https://" + target
        cmd.extend(["--url", target])
    elif source_type == "dir":
        cmd.extend(["--dir", target])
    elif source_type == "repo":
        cmd.extend(["--repo", target])

    try:
        print(f"[SkillUI Extractor] Executing command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=300 # 5 minutes timeout
        )

        stdout_log = result.stdout or ""
        print("[SkillUI Extractor] Command succeeded!")
        print(f"Stdout:\n{stdout_log[:1000].encode('ascii', 'replace').decode('ascii')}")

        # Check what files were created
        # If skillui nested outputs in {name}-design subdirectory, use that as out_dir
        nested_dir = out_dir / f"{name}-design"
        if nested_dir.exists():
            out_dir = nested_dir

        design_md_path = out_dir / "DESIGN.md"
        skill_md_path = out_dir / "SKILL.md"
        potential_skill_files = list(out_dir.glob("*.skill"))
        
        extracted_files_list = []
        if design_md_path.exists():
            extracted_files_list.append(f"• **Design Documentation**: [DESIGN.md](file:///{design_md_path.as_posix()})")
        if skill_md_path.exists():
            extracted_files_list.append(f"• **Skill Integration Guide**: [SKILL.md](file:///{skill_md_path.as_posix()})")
        for psf in potential_skill_files:
            extracted_files_list.append(f"• **AI-Readable Skill Package**: [{psf.name}](file:///{psf.as_posix()})")

        files_str = "\n".join(extracted_files_list) if extracted_files_list else "No output files detected in output directory."

        summary = (
            f"### [SUCCESS] SkillUI Design Extraction Completed successfully, Pratik Sir!\n\n"
            f"Successfully reverse-engineered the design system for **{name}** from {source_type} target `{target}`.\n\n"
            f"#### [FILES] Extracted Files and Artifacts:\n"
            f"{files_str}\n\n"
            f"#### [DETAILS] Extraction Details:\n"
            f"- **Target**: `{target}`\n"
            f"- **Extraction Mode**: `{mode}`\n"
            f"- **Storage Location**: `{out_dir}`\n\n"
            f"You can now integrate this extracted design system directly into your PyQt/Python GUIs, "
            f"or use the packaged `.skill` schema file directly with Gemini as a customized visual skill!"
        )
        return summary

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.stdout or str(e)
        safe_error = error_msg.encode('ascii', 'replace').decode('ascii')
        print(f"[SkillUI Extractor] [ERROR] Extraction command failed: {safe_error}")
        return (
            f"[WARNING] **SkillUI Design Extraction failed, Pratik Sir.**\n\n"
            f"**Error Details:**\n"
            f"```\n{safe_error}\n```\n"
            f"Please verify that the target source `{target}` is accessible and the format/arguments are correct."
        )
    except subprocess.TimeoutExpired:
        print("[SkillUI Extractor] [ERROR] Extraction timed out after 5 minutes.")
        return "[WARNING] **SkillUI Design Extraction timed out, Pratik Sir.** The target resource is taking too long to scan."
    except Exception as ex:
        safe_ex = str(ex).encode('ascii', 'replace').decode('ascii')
        print(f"[SkillUI Extractor] [ERROR] Unexpected error: {safe_ex}")
        return f"[WARNING] **SkillUI Design Extraction failed due to an unexpected error, Pratik Sir:** {safe_ex}"

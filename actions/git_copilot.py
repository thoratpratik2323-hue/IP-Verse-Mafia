import subprocess
from pathlib import Path
from google import genai as new_genai
from config import get_config

def run_git_cmd(args: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(cwd)
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def get_gemini_commit_message(diff: str) -> str:
    """Uses Gemini API to generate a conventional commit message from git diff."""
    if not diff:
        return "chore: general updates"
    try:
        from main import _get_api_key
        api_key = _get_api_key()
        if not api_key:
            return "chore: general updates"
        
        client = new_genai.Client(api_key=api_key)
        prompt = (
            "Write a concise, professional Git conventional commit message "
            "based on the following diff. Only return the commit message text. "
            "Do not wrap it in markdown or add explanations. "
            "Use conventional commits style (e.g., feat: add login feature, fix: resolve crash, refactor: clean layout).\n\n"
            f"Git Diff:\n{diff[:5000]}"
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        msg = response.text.strip()
        # Clean any quotes or backticks if generated
        msg = msg.replace("`", "").replace('"', "").replace("'", "")
        return msg if msg else "chore: updates"
    except Exception as e:
        print(f"[GitCopilot] ⚠️ Message generation failed: {e}")
        return "chore: updates via Saturday AI"

def git_copilot(parameters: dict, player=None, speak=None) -> str:
    """Automates adding, conventional committing (using Gemini), and pushing git changes."""
    action = parameters.get("action", "commit").lower().strip()
    path_str = parameters.get("path", "").strip()
    
    # Default to current saturday workspace if no path is given
    if path_str:
        target_dir = Path(path_str).resolve()
    else:
        target_dir = Path(__file__).resolve().parent.parent

    if not target_dir.exists() or not (target_dir / ".git").exists():
        # Fallback to check parent directories for .git
        found_git = False
        curr = target_dir
        while curr.parent != curr:
            if (curr / ".git").exists():
                target_dir = curr
                found_git = True
                break
            curr = curr.parent
        if not found_git:
            return f"Error: '{target_dir}' or its parents is not a Git repository."

    # Check git status
    code, out, err = run_git_cmd(["status", "--porcelain"], target_dir)
    if code != 0:
        return f"Git status failed: {err}"
    if not out:
        return f"No changes to commit in '{target_dir.name}', sir."

    if action == "status":
        return f"Git status for '{target_dir.name}':\n{out}"

    # Get diff
    d_code, d_out, d_err = run_git_cmd(["diff"], target_dir)
    # Also get cached/staged diff
    dc_code, dc_out, dc_err = run_git_cmd(["diff", "--cached"], target_dir)
    
    combined_diff = (d_out + "\n" + dc_out).strip()
    
    if speak:
        speak("Analyzing your code changes, sir.")

    # Generate Conventional Commit Message via Gemini
    commit_msg = get_gemini_commit_message(combined_diff)
    if player:
        player.write_log(f"SYS [GitCopilot]: Generated commit message: '{commit_msg}'")

    # Add all changes
    run_git_cmd(["add", "."], target_dir)

    # Commit
    c_code, c_out, c_err = run_git_cmd(["commit", "-m", commit_msg], target_dir)
    if c_code != 0:
        return f"Git commit failed: {c_err}"

    # Push
    if speak:
        speak("Pushing changes to your remote repository, sir.")
        
    p_code, p_out, p_err = run_git_cmd(["push"], target_dir)
    
    if p_code == 0:
        return f"Successfully committed changes with message: '{commit_msg}' and pushed to remote, sir."
    return f"Successfully committed changes locally with message: '{commit_msg}', but push failed: {p_err}"

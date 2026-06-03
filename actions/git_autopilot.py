"""
actions/git_autopilot.py — Git Autopilot & Commit Synthesizer for IP Prime.

This is a premium action module for the IP Prime personal assistant suite.
"""

import json
import subprocess
from pathlib import Path
from google import genai

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
API_KEYS_PATH = BASE_DIR / "config" / "api_keys.json"

class GitAutopilot:
    """Parses local git diffs, synthesizes conventional commit messages, and stages/commits code changes."""
    
    def __init__(self, repo_path: str = None):
        self.repo_path = repo_path or str(BASE_DIR)
        
    def _get_gemini_client(self) -> genai.Client:
        try:
            with open(API_KEYS_PATH, "r", encoding="utf-8") as f:
                api_key = json.load(f)["gemini_api_key"]
            return genai.Client(api_key=api_key)
        except Exception:
            raise ValueError("Gemini API key not found in config/api_keys.json")

    def get_git_diff(self) -> str:
        """Retrieves unstaged and staged changes in the workspace."""
        try:
            # First, check if there are unstaged or staged changes
            r = subprocess.run(
                ["git", "diff", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=5
            )
            if r.returncode == 0:
                return r.stdout.strip()
            return ""
        except Exception as e:
            print(f"[GitAutopilot] Error getting git diff: {e}")
            return ""

    def get_status_summary(self) -> str:
        """Returns a brief description of modified, added, or deleted files."""
        try:
            r = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=5
            )
            if r.returncode == 0:
                return r.stdout.strip()
            return ""
        except Exception:
            return ""

    def generate_commit_message(self, diff: str = None) -> str:
        """Asks Gemini to analyze the diff and generate a precise Conventional Commit message."""
        if not diff:
            diff = self.get_git_diff()
            
        status_summary = self.get_status_summary()
        
        if not diff and not status_summary:
            return "chore: no changes detected in the workspace"
            
        client = self._get_gemini_client()
        
        prompt = (
            f"You are a Senior Software Engineer assisting Pratik with Git Autopilot.\n"
            f"Analyze the following git changes status and diff to synthesize a precise, professional Conventional Commit message.\n\n"
            f"### Git Porcelain Status:\n{status_summary}\n\n"
            f"### Git Diff:\n{diff[:6000]}\n\n"
            f"Follow the Conventional Commits style guide exactly:\n"
            f"- Format: <type>(<scope>): <short summary in lowercase, imperative mood>\n"
            f"- Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, etc.\n"
            f"- Example: 'feat(sandbox): integrate interactive sorting algorithms visualizer'\n"
            f"- Return ONLY the single line commit message. No introductions, markdown, backticks, or extra commentary."
        )
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            msg = response.text.strip().replace("`", "").replace("'", "").replace('"', "")
            # Ensure it is a single line
            msg = msg.split("\n")[0].strip()
            return msg
        except Exception as e:
            print(f"[GitAutopilot] Error generating commit message: {e}")
            # Fallback based on status summary
            if "ui_core" in status_summary or "visualizer" in status_summary:
                return "feat(sandbox): optimize code visualizer controls"
            return "chore(workspace): synchronize pending changes"

    def stage_and_commit(self, message: str) -> bool:
        """Stages all changes and commits them with the synthesized message."""
        try:
            # Stage all changes
            subprocess.run(
                ["git", "add", "."],
                cwd=self.repo_path,
                check=True,
                timeout=5
            )
            # Commit with the message
            r = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            print(f"[GitAutopilot] Successful commit: {message}")
            return True
        except Exception as e:
            print(f"[GitAutopilot] Commit failed: {e}")
            return False

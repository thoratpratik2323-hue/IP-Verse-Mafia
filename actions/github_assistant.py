"""
github_assistant.py — Interacts with GitHub API to manage repositories, PRs, and commit branches.

This is a standard action module for the IP Prime personal assistant suite.
"""

import os
import subprocess
from pathlib import Path

def _run_git_cmd(args: list, cwd: str) -> tuple[str, bool]:
    """Runs a git command inside the target directory and returns stdout and whether it was successful."""
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=True
        )
        if res.returncode == 0:
            return res.stdout.strip(), True
        else:
            return res.stderr.strip() or res.stdout.strip(), False
    except Exception as e:
        return f"Error executing git command: {e}", False

def _run_gh_cmd(args: list, cwd: str) -> tuple[str, bool]:
    """Runs a GitHub CLI command inside the target directory and returns stdout and success flag."""
    try:
        res = subprocess.run(
            ["gh"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=True
        )
        if res.returncode == 0:
            return res.stdout.strip(), True
        else:
            return res.stderr.strip() or res.stdout.strip(), False
    except Exception as e:
        return f"Error executing GitHub CLI (gh) command: {e}", False

def execute_git_automation(action: str, repo_path: str = None, commit_message: str = None, title: str = None, body: str = None) -> str:
    """Orchestrates git status, git diff, commits, pushes, and GitHub pull requests."""
    # Default to current workspace if not specified
    if not repo_path:
        repo_path = str(Path(__file__).resolve().parent.parent)
        
    repo_path = os.path.abspath(repo_path)
    if not os.path.exists(repo_path):
        return f"Error: Repository path '{repo_path}' does not exist."
        
    action_clean = action.lower().strip()
    
    # Verify it is a git repository
    _, is_git = _run_git_cmd(["rev-parse", "--is-inside-work-tree"], repo_path)
    if not is_git:
        return f"Error: The path '{repo_path}' is not a valid Git repository (no `.git` directory)."
        
    if action_clean == "get_diff":
        status_out, _ = _run_git_cmd(["status", "-s"], repo_path)
        diff_out, _ = _run_git_cmd(["diff"], repo_path)
        
        if not status_out:
            return "### 🐙 Git Status & Diff\nYour repository is perfectly clean! No changes detected."
            
        return (
            f"### 🐙 Git Status & Diff\n"
            f"**Workspace**: `{repo_path}`\n\n"
            f"#### Modified Files Status:\n"
            f"```text\n{status_out}\n```\n\n"
            f"#### Active Diffs:\n"
            f"```diff\n{diff_out or 'No staged/unstaged line diffs to show (new untracked files only).'}\n```"
        )
        
    elif action_clean == "commit_push":
        if not commit_message:
            commit_message = "Automated commit by IP Prime assistant"
            
        # 1. Add all changes
        _, ok = _run_git_cmd(["add", "."], repo_path)
        if not ok:
            return "Failed to run `git add .` on the repository."
            
        # 2. Check if there are active changes to commit
        status_out, _ = _run_git_cmd(["status", "-s"], repo_path)
        if not status_out:
            return "No changes found to commit. Repository is clean."
            
        # 3. Commit changes
        commit_out, ok = _run_git_cmd(["commit", "-m", commit_message], repo_path)
        if not ok:
            return f"Failed to commit changes:\n```\n{commit_out}\n```"
            
        # 4. Get active branch
        branch_name, _ = _run_git_cmd(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)
        if not branch_name:
            branch_name = "main"
            
        # 5. Push to remote
        push_out, ok = _run_git_cmd(["push", "origin", branch_name], repo_path)
        if not ok:
            return (
                f"Successfully committed changes locally, but remote push failed.\n"
                f"**Branch**: `{branch_name}`\n"
                f"**Commit Output**: \n```\n{commit_out}\n```\n"
                f"**Push Output/Error**: \n```\n{push_out}\n```"
            )
            
        return (
            f"### 🐙 Git Commit & Push Successful!\n"
            f"**Workspace**: `{repo_path}`\n"
            f"**Branch**: `{branch_name}`\n"
            f"**Commit Message**: `\"{commit_message}\"`\n\n"
            f"#### Push Output details:\n"
            f"```text\n{commit_out}\n{push_out or 'Pushed successfully.'}\n```"
        )
        
    elif action_clean == "create_pr":
        if not title:
            title = "IP Prime Automated Pull Request"
        if not body:
            body = "This pull request was generated autonomously by the IP Prime AI Desktop Assistant."
            
        # Check if gh CLI is installed and logged in
        gh_check, ok = _run_gh_cmd(["auth", "status"], repo_path)
        if not ok:
            return (
                f"Error: GitHub CLI (`gh`) is not logged in or not installed.\n"
                f"Please run `gh auth login` in your terminal to authenticate.\n"
                f"**Diagnostics output**: \n```\n{gh_check}\n```"
            )
            
        # Get active branch name
        branch_name, _ = _run_git_cmd(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)
        if branch_name in ["main", "master"]:
            return f"Error: Cannot create a Pull Request directly from the base branch `{branch_name}`. Please create and switch to a custom feature branch first."
            
        # Push branch first
        _run_git_cmd(["push", "-u", "origin", branch_name], repo_path)
        
        # Create pull request
        pr_out, ok = _run_gh_cmd(["pr", "create", "--title", title, "--body", body], repo_path)
        if not ok:
            return f"Failed to create GitHub Pull Request:\n```\n{pr_out}\n```"
            
        return (
            f"### 🐙 GitHub Pull Request Created!\n"
            f"**PR Link/Output**: {pr_out}\n"
            f"**Branch**: `{branch_name}`\n"
            f"**Title**: `\"{title}\"`"
        )
        
    else:
        return f"Error: Unknown git action '{action}'."

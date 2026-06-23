"""
coding_workflow.py — Next-Gen self-healing and self-committing coding pipeline for IP Prime.

Chains:
1. IP AI Army specialized division to write/modify code.
2. Subprocess command to run tests/verification.
3. Terminal Doctor to automatically diagnose and heal syntax/compilation errors if verification fails.
4. Git Assistant to stage and auto-commit the verified changes with premium conventional messages.
"""

import os
import sys
import subprocess
import re
import time
from pathlib import Path
from typing import Any, Optional
from actions.ip_army import run_ip_army
from actions.terminal_doctor import diagnose_and_heal_command
from actions.dev_agent import git_assistant

def run_git_cmd(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

def is_git_repository(cwd: str) -> bool:
    try:
        res = run_git_cmd(["rev-parse", "--is-inside-work-tree"], cwd)
        return res.returncode == 0 and res.stdout.strip() == "true"
    except Exception:
        return False

def get_git_status(cwd: str) -> str:
    try:
        res = run_git_cmd(["status", "--porcelain"], cwd)
        return res.stdout.strip()
    except Exception:
        return ""

def find_stash_index(cwd: str, unique_msg: str) -> Optional[str]:
    try:
        res = run_git_cmd(["stash", "list"], cwd)
        if res.returncode != 0:
            return None
        for line in res.stdout.splitlines():
            if unique_msg in line:
                match = re.match(r"^(stash@\{\d+\})", line)
                if match:
                    return match.group(1)
    except Exception:
        pass
    return None

def create_stash_backup(cwd: str, unique_msg: str) -> bool:
    try:
        if not get_git_status(cwd):
            return False
        res = run_git_cmd(["stash", "push", "-u", "-m", unique_msg], cwd)
        if res.returncode != 0:
            res = run_git_cmd(["stash", "save", "-u", unique_msg], cwd)
        if res.returncode == 0:
            stash_idx = find_stash_index(cwd, unique_msg)
            if stash_idx:
                apply_res = run_git_cmd(["stash", "apply", stash_idx], cwd)
                return apply_res.returncode == 0
    except Exception:
        pass
    return False

def drop_stash_backup(cwd: str, unique_msg: str):
    try:
        stash_idx = find_stash_index(cwd, unique_msg)
        if stash_idx:
            run_git_cmd(["stash", "drop", stash_idx], cwd)
    except Exception:
        pass

def rollback_git_changes(cwd: str, unique_msg: str, stashed: bool):
    try:
        run_git_cmd(["reset", "--hard", "HEAD"], cwd)
        run_git_cmd(["clean", "-fd"], cwd)
        if stashed:
            stash_idx = find_stash_index(cwd, unique_msg)
            if stash_idx:
                run_git_cmd(["stash", "pop", stash_idx], cwd)
    except Exception:
        pass

def run_coding_workflow(parameters: dict, player: Any, speak: Any = None) -> str:
    """
    Executes the elite self-healing coding workflow.
    
    Args:
        parameters: dict with project_path, instruction, test_command, auto_commit
        player: UI/system state logger
        speak: speak function for vocal feedback
    """
    project_path = parameters.get("project_path", "").strip()
    instruction = parameters.get("instruction", "").strip()
    test_command = parameters.get("test_command", "").strip()
    auto_commit = parameters.get("auto_commit", True)

    if not project_path:
        # Fallback to current workspace directory
        project_path = str(Path.cwd())
        
    if not instruction:
        return "Pratik Sir, please provide an instruction or feature request for the coding workflow."

    # Initialize Git Backup Guard if applicable
    is_git = is_git_repository(project_path)
    backup_msg = f"ip_prime_backup_{int(time.time())}"
    stashed = False

    if is_git:
        player.write_log(f"Workflow: Git repository detected at '{project_path}'. Setting up Rollback Guard...")
        stashed = create_stash_backup(project_path, backup_msg)
        if stashed:
            player.write_log("Workflow: Workspace backup stash created and applied successfully.")
        else:
            player.write_log("Workflow: No uncommitted changes or clean repository. Ready to modify.")

    player.write_log(f"Workflow: Initiating coding pipeline on '{project_path}'")
    player.write_thought(f"Phase 1: Deploying IP AI Army to execute changes for request: '{instruction}'")
    if speak:
        speak("Mobilizing the IP AI Army specialized division to write the code.")

    # Phase 1: Run IP Army Coding Task
    try:
        coding_result = run_ip_army(project_path, instruction, player=player)
        player.write_log(f"Workflow: IP Army complete. Result:\n{coding_result}")
    except Exception as e:
        err_msg = f"Phase 1 Coding failed: {e}"
        player.write_log(f"Workflow Error: {err_msg}")
        if is_git:
            player.write_log("Workflow: Initiating automatic rollback due to coding failure...")
            rollback_git_changes(project_path, backup_msg, stashed)
        return f"### ❌ Workflow Aborted (Phase 1 Coding Fail)\n{err_msg}"

    # Phase 2: Run Verification Test
    if not test_command:
        # Guess test runner if not provided
        test_dir = Path(project_path) / "tests"
        if test_dir.exists():
            test_command = f'"{sys.executable}" -m unittest discover -s tests'
        else:
            test_command = f'"{sys.executable}" -m unittest'

    player.write_thought(f"Phase 2: Running verification tests via: '{test_command}'")
    if speak:
        speak("Phase 2: Running automated tests to verify code changes.")

    try:
        test_proc = subprocess.run(
            test_command,
            shell=True,
            cwd=project_path,
            capture_output=True,
            text=True
        )
        test_success = test_proc.returncode == 0
        test_output = (test_proc.stdout or "") + "\n" + (test_proc.stderr or "")
    except Exception as e:
        test_success = False
        test_output = f"Test execution threw an error: {e}"

    # Phase 3: Self-Healing via Terminal Doctor if verification failed
    if not test_success:
        player.write_thought("Verification failed! Phase 3: Launching Terminal Doctor self-healing agent...")
        if speak:
            speak("Verification failed! Deploying Terminal Doctor to automatically diagnose and heal the error.")

        try:
            heal_result = diagnose_and_heal_command(test_command, cwd=project_path, max_rounds=3, ui=player)
            player.write_log(f"Workflow: Self-healing run complete. Result:\n{heal_result}")

            # Re-run tests to confirm resolution
            player.write_thought("Re-running verification tests to confirm heal...")
            test_proc = subprocess.run(
                test_command,
                shell=True,
                cwd=project_path,
                capture_output=True,
                text=True
            )
            test_success = test_proc.returncode == 0
            test_output = (test_proc.stdout or "") + "\n" + (test_proc.stderr or "")
        except Exception as e:
            player.write_log(f"Workflow Error: Self-healing crashed: {e}")
            test_success = False

    # Phase 4: Stage & Commit via Git Assistant on success
    if test_success:
        player.write_thought("Verification successful! Phase 4: Auto-saving work to Git repository...")
        if speak:
            speak("Verification successful, sir! Auto-saving all changes to the git repository.")

        # If tests passed and we had a backup, drop it to clean up the stash stack
        if is_git and stashed:
            player.write_thought("Dropping backup stash as verification succeeded.")
            drop_stash_backup(project_path, backup_msg)

        if auto_commit:
            try:
                commit_result = git_assistant(
                    action_type="commit",
                    project_path=project_path,
                    player=player
                )
                player.write_log(f"Workflow: Git commit complete. Result:\n{commit_result}")
                return f"### 🏆 Elite Coding Workflow Succeeded!\n\n1. **Coding**: Successfully executed changes via IP AI Army.\n2. **Verification**: Tests passed successfully.\n3. **Commit**: {commit_result}"
            except Exception as e:
                player.write_log(f"Workflow Warning: Auto-commit failed: {e}")
                return f"### 🏆 Elite Coding Workflow Succeeded (Commit failed)!\n\n1. **Coding**: Successfully executed changes.\n2. **Verification**: Tests passed successfully.\n3. **Warning**: Git auto-commit failed: {e}"
        else:
            return "### 🏆 Elite Coding Workflow Succeeded!\n\n1. **Coding**: Successfully executed changes.\n2. **Verification**: Tests passed successfully.\n3. **Git**: Auto-commit bypassed as per configuration."
    else:
        player.write_log("Workflow Failed: Verification failed and could not be auto-healed.")
        if speak:
            speak("Alert! Verification failed and could not be auto-healed, sir.")
            
        # If git repository and tests failed (healing failed), perform rollback!
        if is_git:
            player.write_log("Workflow: Initiating automatic rollback and restoring original workspace...")
            rollback_git_changes(project_path, backup_msg, stashed)
            
        return f"### ❌ Elite Coding Workflow Failed (Workspace Rolled Back)!\n\n1. **Coding**: Executed changes.\n2. **Verification**: Tests failed.\n3. **Status**: Workspace rolled back to clean state / original uncommitted changes restored.\n4. **Diagnostics Output**:\n```\n{test_output[-1500:]}\n```"

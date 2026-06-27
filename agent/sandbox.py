import logging
import ast
import os
import sys
import subprocess
from pathlib import Path

# Allowed directories for file operations
SAFE_ROOTS = [
    Path.home() / "Downloads",
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path(os.environ.get("TEMP", "/tmp")),
    Path.home() / ".gemini" / "antigravity" / "scratch",
]

def is_safe_path(target_path: Path) -> bool:
    try:
        resolved = target_path.resolve(strict=False)
        # Check if the path is inside at least one of the safe roots
        for safe_root in SAFE_ROOTS:
            try:
                resolved_safe = safe_root.resolve(strict=False)
                # Check if resolved is relative to resolved_safe
                resolved.relative_to(resolved_safe)
                return True
            except ValueError:
                continue
    except Exception as _exc:  # noqa: BLE001
        logging.debug("[%s] Suppressed: %s", __name__, _exc)
    return False

class SafetyScanner(ast.NodeVisitor):
    def __init__(self):
        self.errors = []

    def visit_Call(self, node):
        # Check for system/subprocess runs that might be destructive
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        # Block direct subprocess/os shell calls that bypass safe commands
        if func_name in ("system", "popen", "run", "call", "check_output", "exec"):
            # If the tool uses os.system or subprocess, check if the command contains dangerous strings
            cmd = ""
            if node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant):
                    cmd = str(first_arg.value)
                elif isinstance(first_arg, ast.List) and first_arg.elts:
                    # e.g., ["rm", "-rf", "/"]
                    cmd_parts = []
                    for el in first_arg.elts:
                        if isinstance(el, ast.Constant):
                            cmd_parts.append(str(el.value))
                    cmd = " ".join(cmd_parts)
            
            danger_patterns = ["rmdir /s", "del /f", "rm -rf", "format", "shutdown", "mkfs"]
            for pat in danger_patterns:
                if pat in cmd.lower():
                    self.errors.append(f"Blocked destructive command call: {cmd}")

        # Block shutil.rmtree or os.remove on non-safe folders
        if func_name in ("rmtree", "remove", "rmdir", "unlink"):
            if node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant):
                    target_path = Path(str(first_arg.value))
                    if not is_safe_path(target_path):
                        self.errors.append(f"Attempted file/folder deletion outside safe paths: {target_path}")

        self.generic_visit(node)


def execute_in_sandbox(code: str, tmp_path: str, timeout: int = 120) -> tuple[int, str, str]:
    """
    Performs static safety check, then executes code inside a subprocess.
    Returns: (returncode, stdout, stderr)
    """
    # ── Step 1: AST Safety Analysis ──
    try:
        tree = ast.parse(code)
        scanner = SafetyScanner()
        scanner.visit(tree)
        if scanner.errors:
            error_details = "; ".join(scanner.errors)
            raise PermissionError(f"Security Alert: {error_details}")
    except SyntaxError as e:
        # Syntax issues will fail standard compile, let execution raise standard syntax error
        pass
    except Exception as e:
        if isinstance(e, PermissionError):
            raise
        # Log other AST parsing issues but don't crash
        print(f"[Sandbox] ⚠️ Static analysis skipped: {e}")

    # ── Step 2: Subprocess Execution ──
    # Run the temporary script in the user's downloads folder or home directory
    result = subprocess.run(
        [sys.executable, tmp_path],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(Path.home() / "Downloads")
    )
    return result.returncode, result.stdout, result.stderr

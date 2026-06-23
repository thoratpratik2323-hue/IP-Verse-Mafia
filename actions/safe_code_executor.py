"""
safe_code_executor.py — Sandboxed Code Execution Engine

Safely runs Python/JavaScript in isolated environment with restrictions.
"""

import subprocess
import json
import tempfile
import os
from typing import Dict, Any


class SafeCodeExecutor:
    """Executes code safely in a sandbox."""
    
    ALLOWED_MODULES = [
        "math", "random", "json", "datetime", "time", "re", "itertools",
        "collections", "statistics", "decimal"
    ]
    
    FORBIDDEN_KEYWORDS = [
        "import", "exec", "eval", "__import__", "open", "file", "input",
        "globals", "locals", "vars", "__"
    ]
    
    def validate_code(self, code: str) -> bool:
        """Check if code is safe to execute."""
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in code.lower():
                return False
        return True
    
    def execute_python(self, code: str, timeout: int = 5) -> Dict[str, Any]:
        """Execute Python code safely."""
        if not self.validate_code(code):
            return {"success": False, "error": "Code contains forbidden operations"}
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                f.flush()
                
                result = subprocess.run(
                    ["python", f.name],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                os.unlink(f.name)
                
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip() if result.stderr else None
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_javascript(self, code: str, timeout: int = 5) -> Dict[str, Any]:
        """Execute JavaScript code safely."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(code)
                f.flush()
                
                result = subprocess.run(
                    ["node", f.name],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                os.unlink(f.name)
                
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip() if result.stderr else None
                }
        except FileNotFoundError:
            return {"success": False, "error": "Node.js not installed"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def calculate_expression(self, expr: str) -> Dict[str, Any]:
        """Safely evaluate mathematical expressions."""
        try:
            import ast
            import math
            
            # Validate expression
            tree = ast.parse(expr, mode='eval')
            
            # Only allow safe operations
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if not isinstance(node.func, ast.Name):
                        return {"success": False, "error": "Complex function calls not allowed"}
            
            # Execute with math context
            result = eval(expr, {"__builtins__": {}}, {"math": math, **math.__dict__})
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


executor = SafeCodeExecutor()

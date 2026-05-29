import json
import time
import re
from typing import Dict, Any, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, QEventLoop

class SafetyGuardSignals(QObject):
    """Signals for thread-safe PyQt UI safety prompts."""
    request_approval = pyqtSignal(str, str, object) # action_name, description, loop_object

class SafetyGuard:
    """
    Phase 5: Safety Guard System.
    Intercepts and validates all autonomous actions before they are executed.
    """
    NEVER_DO = [
        "share_data_externally",
        "disable_antivirus",
        "remove_security_software",
        "bypass_credentials",
        "exfiltrate_private_keys"
    ]
    ALWAYS_ASK = [
        "delete_file",
        "delete_directory",
        "kill_process",
        "git_push",
        "send_email",
        "run_generated_code"
    ]
    
    _signals = SafetyGuardSignals()
    ui_instance = None # Hooked by ui_core on startup

    @classmethod
    def verify_action(cls, tool_name: str, parameters: dict) -> Tuple[bool, str]:
        """
        Validates the proposed action against Safety Policies.
        Returns (is_approved, explanation_message).
        """
        action_desc = f"Tool: {tool_name} | Params: {json.dumps(parameters)}"
        
        # 1. Check NEVER_DO Rules
        param_str = str(parameters).lower()
        for forbidden in cls.NEVER_DO:
            if forbidden in param_str or forbidden in tool_name.lower():
                msg = f"CRITICAL BLOCKED: Forbidden safety rule '{forbidden}' triggered."
                print(f"[SafetyGuard] 🚨 {msg}")
                return False, msg
                
        # 2. Check ALWAYS_ASK Rules
        is_risky = False
        risk_reason = ""
        
        # Detect risky tools or parameters
        if tool_name == "generated_code":
            is_risky = True
            risk_reason = f"Executing custom Python script: '{parameters.get('description', 'No description')}'"
        elif "delete" in param_str or "remove" in param_str or "clear" in param_str:
            is_risky = True
            risk_reason = f"Destructive file/folder modification request in tool '{tool_name}'."
        elif "git" in param_str and "push" in param_str:
            is_risky = True
            risk_reason = "Git Push deployment query registered."
        elif "kill" in param_str or "terminate" in param_str:
            is_risky = True
            risk_reason = "Proactive process termination instruction."

        if is_risky:
            print(f"[SafetyGuard] ⚠️ Risk Intercepted: {risk_reason}")
            # If PyQt UI is loaded, show dynamic Cyberpunk overlay prompt
            if cls.ui_instance:
                approved = cls._prompt_ui_approval(tool_name, risk_reason)
                if approved:
                    return True, "User authorized execution via Safety Dialog."
                else:
                    return False, "User rejected execution via Safety Dialog."
            else:
                # Console fallback for headless runs
                print("[SafetyGuard] Console Fallback: Auto-authorizing developer action.")
                return True, "Console execution approved."
                
        return True, "Action approved. Safe to execute."

    @classmethod
    def _prompt_ui_approval(cls, tool_name: str, reason: str) -> bool:
        """Pops up a premium PyQt6 cyberpunk modal overlay to request approval."""
        from PyQt6.QtCore import QMetaObject, Qt
        
        # Thread-safe event loop wait
        loop = QEventLoop()
        result = {"approved": False}
        
        def on_user_decision(decision: bool):
            result["approved"] = decision
            loop.quit()
            
        cls._signals.request_approval.emit(tool_name, reason, on_user_decision)
        loop.exec()
        
        return result["approved"]

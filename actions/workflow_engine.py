"""
workflow_engine.py — Visual Workflow Builder & Automation

Create multi-step automations with if-then-else logic.
"""

import json
from typing import Dict, List, Any, Callable
from datetime import datetime


class WorkflowEngine:
    """Builds and executes multi-step workflows."""
    
    def __init__(self):
        self.workflows: Dict[str, Dict] = {}
        self.actions: Dict[str, Callable] = {}
    
    def register_action(self, name: str, func: Callable) -> None:
        """Register an action function."""
        self.actions[name] = func
    
    def create_workflow(self, name: str, description: str) -> None:
        """Create new workflow."""
        self.workflows[name] = {
            "name": name,
            "description": description,
            "steps": [],
            "created_at": datetime.now().isoformat(),
            "enabled": True
        }
    
    def add_step(self, workflow_name: str, step: Dict[str, Any]) -> bool:
        """Add step to workflow."""
        if workflow_name not in self.workflows:
            return False
        
        step_obj = {
            "id": len(self.workflows[workflow_name]["steps"]) + 1,
            "type": step.get("type"),  # "action", "condition", "delay"
            "action": step.get("action"),
            "condition": step.get("condition"),
            "params": step.get("params", {}),
            "next_on_success": step.get("next_on_success"),
            "next_on_failure": step.get("next_on_failure")
        }
        
        self.workflows[workflow_name]["steps"].append(step_obj)
        return True
    
    def execute_workflow(self, workflow_name: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a workflow."""
        if workflow_name not in self.workflows:
            return {"success": False, "error": "Workflow not found"}
        
        if not self.workflows[workflow_name]["enabled"]:
            return {"success": False, "error": "Workflow is disabled"}
        
        workflow = self.workflows[workflow_name]
        context = context or {}
        results = []
        current_step_id = 1
        
        while current_step_id:
            step = next((s for s in workflow["steps"] if s["id"] == current_step_id), None)
            if not step:
                break
            
            result = self._execute_step(step, context)
            results.append(result)
            
            # Determine next step
            if result["success"]:
                current_step_id = step.get("next_on_success")
            else:
                current_step_id = step.get("next_on_failure")
        
        return {
            "workflow": workflow_name,
            "success": all(r["success"] for r in results),
            "steps_executed": len(results),
            "results": results,
            "context": context
        }
    
    def _execute_step(self, step: Dict, context: Dict) -> Dict[str, Any]:
        """Execute individual step."""
        try:
            if step["type"] == "action":
                action_name = step["action"]
                if action_name not in self.actions:
                    return {"success": False, "error": f"Action {action_name} not found"}
                
                result = self.actions[action_name](**step["params"], context=context)
                return {"success": True, "action": action_name, "result": result}
            
            elif step["type"] == "condition":
                condition = step["condition"]
                # Simple condition evaluation
                result = self._evaluate_condition(condition, context)
                return {"success": result, "condition": condition, "result": result}
            
            elif step["type"] == "delay":
                import time
                delay = step["params"].get("seconds", 1)
                time.sleep(delay)
                return {"success": True, "type": "delay", "seconds": delay}
            
            else:
                return {"success": False, "error": f"Unknown step type: {step['type']}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        """Evaluate a condition string."""
        try:
            # Simple variable substitution for safe evaluation
            for key, value in context.items():
                condition = condition.replace(f"{{{key}}}", str(value))
            
            # Evaluate the expression
            return bool(eval(condition, {"__builtins__": {}}))
        except:
            return False
    
    def list_workflows(self) -> List[Dict]:
        """List all workflows."""
        return [
            {
                "name": w["name"],
                "description": w["description"],
                "steps": len(w["steps"]),
                "enabled": w["enabled"]
            }
            for w in self.workflows.values()
        ]
    
    def export_workflow(self, workflow_name: str) -> str:
        """Export workflow as JSON."""
        if workflow_name not in self.workflows:
            return None
        return json.dumps(self.workflows[workflow_name], indent=2)
    
    def import_workflow(self, workflow_json: str) -> bool:
        """Import workflow from JSON."""
        try:
            workflow = json.loads(workflow_json)
            self.workflows[workflow["name"]] = workflow
            return True
        except:
            return False


engine = WorkflowEngine()

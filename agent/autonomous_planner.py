import json
import re
import queue
import time
from dataclasses import dataclass, field
from google import genai

from agent.planner import create_plan
from actions.prime_utils import get_api_key

@dataclass(order=True)
class PrioritizedTask:
    priority: int
    timestamp: float
    goal: str = field(compare=False)
    context: str = field(compare=False, default="")

class AutonomousPlanner:
    """
    Advanced Planning Engine for IP Prime.
    Features: Task Decomposition, Priority Queue, and Self-Reflection Loop.
    """
    def __init__(self):
        self.task_queue = queue.PriorityQueue()
        self.client = genai.Client(api_key=get_api_key())
        
    def add_goal(self, goal: str, context: str = "", priority: int = 2):
        """
        Adds a goal to the priority queue.
        Priority: 0 = Urgent/Critical, 1 = High, 2 = Medium (default), 3 = Low/Background
        """
        task = PrioritizedTask(priority=priority, timestamp=time.time(), goal=goal, context=context)
        self.task_queue.put(task)
        print(f"[Planner] 📥 Goal added to priority queue (Priority: {priority}): {goal[:50]}...")
        
    def has_tasks(self) -> bool:
        return not self.task_queue.empty()
        
    def get_next_task(self) -> PrioritizedTask:
        return self.task_queue.get()
        
    def task_done(self):
        self.task_queue.task_done()
        
    def decompose_and_reflect(self, goal: str, context: str = "") -> dict:
        """
        Decomposes a goal into a plan, then uses self-reflection to verify it.
        """
        print(f"[Planner] 🧠 Decomposing goal: {goal}")
        
        # Step 1: Decompose
        initial_plan = create_plan(goal, context)
        
        if not initial_plan or not initial_plan.get("steps"):
            return initial_plan
            
        # Step 2: Self-Reflection
        return self._self_reflect(goal, initial_plan, context)
        
    def _self_reflect(self, goal: str, plan: dict, context: str) -> dict:
        """
        Critic AI reviews its own plan and fixes flaws before execution.
        """
        print("[Planner] 🪞 Initiating Self-Reflection Loop...")
        
        prompt = f"""You are the Self-Reflection Critic for an autonomous AI.
Your job is to review the proposed execution plan for a user's goal.

User Goal: {goal}
Context: {context}

Proposed Plan:
{json.dumps(plan, indent=2)}

Check for:
1. Missing prerequisite steps (e.g., trying to read a file before downloading it).
2. Logical flaws or dangerous commands.
3. Inefficiency (can it be done in fewer steps?).

If the plan is perfect, respond with ONLY the word "APPROVED".
If the plan is flawed, return a newly corrected JSON plan using the exact same JSON structure. Do NOT include markdown blocks, just the raw JSON.
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            result_text = response.text.strip()
            
            if result_text.upper() == "APPROVED":
                print("[Planner] ✅ Plan Approved by Self-Reflection.")
                return plan
                
            # If not approved, parse the new plan
            text = re.sub(r"```(?:json)?", "", result_text).strip().rstrip("`").strip()
            new_plan = json.loads(text)
            
            if "steps" in new_plan and isinstance(new_plan["steps"], list):
                print("[Planner] 🔄 Plan Revised by Self-Reflection.")
                return new_plan
                
        except json.JSONDecodeError as e:
            print(f"[Planner] ⚠️ Self-reflection failed to parse JSON, using original plan. Error: {e}")
        except Exception as e:
            print(f"[Planner] ⚠️ Self-reflection error: {e}")
            
        return plan

    def has_goal(self, goal_name: str) -> bool:
        """Checks if a goal is already in the priority queue."""
        g_l = goal_name.lower().strip()
        for task in list(self.task_queue.queue):
            if g_l in task.goal.lower():
                return True
        return False

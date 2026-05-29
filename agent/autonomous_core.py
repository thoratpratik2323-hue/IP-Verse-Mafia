import time
from memory.autonomous_memory import AutonomousMemory
from agent.executor import AgentExecutor, _call_tool
from agent.error_handler import analyze_error, generate_fix
from agent.autonomous_planner import AutonomousPlanner
from agent.emotion_context import EmotionContextDetector
from agent.proactive_monitor import ProactiveMonitor
from agent.learning_system import LearningSystem
from brain.core_intelligence import IPBrain

class AutonomousCore:
    """
    100% Autonomous AI Heartbeat.
    Perceives tasks, thinks (plans), acts (executes & self-heals), and learns (memory).
    """

    def __init__(self):
        self.memory = AutonomousMemory()
        self.executor = AgentExecutor()
        
        # Phase 2 advanced modules
        self.planner = AutonomousPlanner()
        self.emotion_detector = EmotionContextDetector(self.memory)
        self.monitor = ProactiveMonitor(self)
        
        # Phase 3: The 6-Layer Brain Architecture and Learning System
        self.brain = IPBrain()
        self.learning_system = LearningSystem()  # Phase 3 Learning System
        
        self.running = False
        print("[AutonomousCore] Initialized 100% Autonomous Engine with Proactive Intelligence.")

    def add_goal(self, goal: str, context: str = "", priority: int = 2):
        """Adds a goal to the autonomous priority queue."""
        # Check emotion and append to context if it's user input
        if "proactive" not in context.lower(): 
            mood_data = self.emotion_detector.analyze_input(goal)
            mood_context = self.emotion_detector.get_behavioral_context(mood_data)
            context += f"\n{mood_context}"
            
        self.planner.add_goal(goal, context, priority)

    def think(self, goal: str, input_context: str = "") -> dict:
        """
        Task Decomposer: Breaks down a goal using priority queue and self-reflection.
        """
        print(f"\n[AutonomousCore] 🧠 Thinking about: {goal}")
        
        # Check episodic memory for past experience
        past_experiences = self.memory.recall_past_experience(goal)
        context = input_context + "\n"
        if past_experiences:
            context += "Past experiences for similar goals:\n"
            for ep in past_experiences:
                context += f"- Goal: {ep['goal']} (Success: {ep['success']})\n"
                
        # Check procedural memory for standard ways of doing things
        procedures = self.memory.recall_all_procedures()
        if procedures:
            context += "Standard Procedures available:\n"
            for p_name, p_data in procedures.items():
                context += f"- {p_name}\n"

        # Ask the advanced planner to decompose and reflect
        plan = self.planner.decompose_and_reflect(goal, context=context)
        
        if plan and plan.get("steps"):
            print(f"[AutonomousCore] 🧠 Plan approved with {len(plan['steps'])} steps.")
        else:
            print("[AutonomousCore] ⚠️ Failed to create a valid plan.")
            
        return plan

    def act(self, goal: str, plan: dict) -> bool:
        """
        Executes the plan step-by-step with self-healing capabilities.
        """
        if not plan or not plan.get("steps"):
            return False

        steps = plan["steps"]
        step_results = {}
        success = True

        for step in steps:
            step_num = step.get("step")
            tool = step.get("tool", "generated_code")
            desc = step.get("description", "")
            params = step.get("parameters", {})
            
            print(f"\n[AutonomousCore] 🚀 Acting -> Step {step_num}: [{tool}] {desc}")
            
            attempt = 1
            step_success = False
            
            while attempt <= 3:
                try:
                    # Execute tool
                    result = _call_tool(tool, params, speak=None)
                    step_results[step_num] = result
                    print(f"[AutonomousCore] ✅ Step {step_num} Success: {str(result)[:100]}")
                    step_success = True
                    break
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"[AutonomousCore] ❌ Step {step_num} Failed (Attempt {attempt}): {error_msg}")
                    
                    # Self-heal
                    healed = self.self_heal(step, error_msg, attempt)
                    if healed == "retry":
                        attempt += 1
                        time.sleep(2)
                        continue
                    elif healed == "skip":
                        step_success = True
                        break
                    elif healed == "replan":
                        # For simplicity in Phase 1, we treat replan as failure at step level
                        # and let the higher level retry or abort.
                        step_success = False
                        break
                    else:
                        step_success = False
                        break
                        
            if not step_success:
                print(f"[AutonomousCore] ⛔ Task aborted due to step {step_num} failure.")
                success = False
                break
                
        # Learn from the experience
        final_result = "Task completed successfully" if success else "Task failed"
        self.memory.remember_task(goal, plan, final_result, success)
        
        return success

    def self_heal(self, failed_step: dict, error: str, attempt: int) -> str:
        """
        Khud galti sudharo - analyze the error and return action (retry, skip, replan, abort).
        """
        print("[AutonomousCore] 🩹 Initiating Self-Healing...")
        recovery = analyze_error(failed_step, error, attempt=attempt)
        decision = recovery["decision"].value if hasattr(recovery["decision"], "value") else recovery["decision"]
        
        print(f"[AutonomousCore] 🩹 Decision: {decision}")
        
        if decision == "replan" and recovery.get("fix_suggestion") and failed_step.get("tool") != "generated_code":
            print(f"[AutonomousCore] 🩹 Generating alternative fix: {recovery['fix_suggestion']}")
            try:
                fixed_step = generate_fix(failed_step, error, recovery["fix_suggestion"])
                print(f"[AutonomousCore] 🩹 Trying alternative tool: {fixed_step['tool']}")
                _call_tool(fixed_step["tool"], fixed_step["parameters"], speak=None)
                print("[AutonomousCore] 🩹 Fix successful.")
                return "skip" # Skip the main loop since we ran it here
            except Exception as e:
                print(f"[AutonomousCore] 🩹 Alternative fix failed: {e}")
                return "abort"
                
        return decision

    def run_forever(self):
        """
        The Autonomous Loop (Heartbeat).
        Runs indefinitely, taking goals from the priority queue and executing them.
        """
        print("[AutonomousCore] 🫀 Heartbeat started. Waiting for tasks...")
        self.running = True
        self.monitor.start() # Start proactive intelligence
        
        while self.running:
            if self.planner.has_tasks():
                task = self.planner.get_next_task()
                
                # 1. Perceive & Think
                plan = self.think(task.goal, task.context)
                
                # 2. Act & Learn
                self.act(task.goal, plan)
                
                self.planner.task_done()
            else:
                # Sleep briefly to avoid high CPU usage
                time.sleep(1)

    def stop(self):
        """Stops the autonomous loop."""
        self.running = False
        self.monitor.stop()
        print("[AutonomousCore] 🧠 Compiling self-learning optimization review before shutdown...")
        try:
            review = self.learning_system.daily_review()
            print(f"[AutonomousCore] 🧠 Self-Learning Summary: {review}")
        except Exception as e:
            print(f"[AutonomousCore] 🧠 Self-Learning failed: {e}")
        print("[AutonomousCore] 🛑 Heartbeat stopped.")

    def goal_exists(self, goal_name: str) -> bool:
        """Checks if a goal is already present in the active planner queue."""
        if hasattr(self, "planner") and self.planner:
            return self.planner.has_goal(goal_name)
        return False

if __name__ == "__main__":
    # Simple test
    core = AutonomousCore()
    core.add_goal("Find the largest file on the desktop")
    core.add_goal("Get the current weather in Tokyo")
    
    # Run briefly then stop for testing
    import threading
    t = threading.Thread(target=core.run_forever)
    t.start()
    
    time.sleep(20)
    core.stop()
    t.join()

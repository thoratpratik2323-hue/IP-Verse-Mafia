import threading
import uuid
import time

class SwarmManager:
    """
    Multi-Agent Swarm Orchestrator.
    Allows IP Prime to spawn background threads (sub-agents) to do parallel tasks.
    """
    def __init__(self):
        self.active_agents = {}
        print("[SwarmManager] \U0001f916 Multi-Agent Swarm Online. Ready to delegate tasks.")

    def spawn_agent(self, role: str, goal: str, context: str = ""):
        """Creates a new sub-agent thread to handle a specific goal."""
        agent_id = str(uuid.uuid4())[:8]
        
        def agent_worker(a_id, a_role, a_goal, a_context):
            print(f"[{a_id}:{a_role}] Started working on: {a_goal}")
            # Simulate work for now
            # In full production, this would initialize a separate ReasoningEngine instance
            time.sleep(3)
            result = f"Task completed by {a_role}. Handled goal: {a_goal}"
            print(f"[{a_id}:{a_role}] Finished work.")
            self.active_agents[a_id]["status"] = "completed"
            self.active_agents[a_id]["result"] = result
            
        thread = threading.Thread(target=agent_worker, args=(agent_id, role, goal, context))
        self.active_agents[agent_id] = {
            "role": role,
            "goal": goal,
            "status": "running",
            "thread": thread,
            "result": None
        }
        
        thread.start()
        return agent_id

    def check_agent_status(self, agent_id: str):
        """Checks if a sub-agent has finished its task."""
        if agent_id not in self.active_agents:
            return "Agent not found."
            
        agent = self.active_agents[agent_id]
        if agent["status"] == "completed":
            return f"Agent Completed. Result: {agent['result']}"
        else:
            return "Agent is still running..."

# Global instance
swarm_manager = SwarmManager()

def delegate_task(parameters: dict, player=None):
    """
    Tool function for IP Prime to delegate a task to a swarm agent.
    parameters: {"role": "Researcher/Coder", "goal": "What to do"}
    """
    role = parameters.get("role", "General Assistant")
    goal = parameters.get("goal", "Do a background task")
    
    agent_id = swarm_manager.spawn_agent(role, goal)
    return f"Successfully delegated to {role} sub-agent (ID: {agent_id}). Check back later using check_agent_status."

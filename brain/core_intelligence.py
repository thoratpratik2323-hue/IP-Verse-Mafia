from brain.perception import PerceptionEngine
from brain.memory_engine import MemoryEngine
from brain.reasoning import ReasoningEngine
from brain.emotion_engine import EmotionEngine
from brain.learning_engine import LearningEngine
from brain.rag_engine import RAGEngine
from agent.executor import AgentExecutor, _call_tool

class IPBrain:
    """
    LAYER 1 - Core Intelligence.
    IP Prime ka actual dimag. Ye sab kuch control karta hai.
    """
    
    def __init__(self):
        print("[IPBrain] 🧠 Booting up Core Intelligence (6-Layer Architecture)...")
        
        self.perception   = PerceptionEngine()   # Aankhein + Kaan
        self.memory       = MemoryEngine()        # Yaaddasht
        self.rag          = RAGEngine()           # Knowledge Base
        self.reasoning    = ReasoningEngine(self.memory)     # Sochna
        self.emotion      = EmotionEngine()       # Dil (Feel karna)
        self.learning     = LearningEngine(self.memory)      # Seekhna
        self.execution    = AgentExecutor()       # Haath-pair (Execution)
        
        print("[IPBrain] 🟢 All Brain Engines Online.")
        
    def process_input(self, raw_input: str) -> str:
        """
        The Master Loop: Perceive -> RAG -> Reason -> Execute -> Learn -> Emote
        """
        # 1. PERCEIVE
        print(f"[IPBrain] 🔍 Perceiving input: {raw_input[:50]}")
        perception_data = self.perception.perceive(raw_input)
        
        # 2. RAG
        print("[IPBrain] 📚 Querying Knowledge Base...")
        knowledge = self.rag.query_knowledge(raw_input)
        context = raw_input
        if knowledge:
            print("[IPBrain] 💡 Knowledge retrieved.")
            context = f"{raw_input}\n\n[CONTEXT]: {knowledge}"
        
        # 3. REASON
        print("[IPBrain] 🤔 Reasoning...")
        plan = self.reasoning.create_plan(context, perception_data)
        confidence = plan.get("confidence", 0.5)
        decision = self.reasoning.should_ask_or_assume(confidence)
        
        if decision == "ASK":
            # Don't execute, ask user first
            response = f"I think you want to: {plan.get('understanding')}. Should I proceed with {plan.get('approach')}?"
            return self.emotion.adapt_response(response, perception_data.get('emotion'))
            
        # 3. EXECUTE
        print(f"[IPBrain] ⚙️ Executing Plan: {plan.get('approach')}")
        success = True
        final_result = ""
        error_msg = None
        
        for step in plan.get("steps", []):
            try:
                result = _call_tool(step.get("action", "generated_code"), step.get("parameters", {}), speak=None)
                final_result += str(result) + "\n"
            except Exception as e:
                success = False
                error_msg = str(e)
                print(f"[IPBrain] ❌ Execution failed: {e}")
                break
                
        # 4. LEARN
        print("[IPBrain] ⚡ Learning from outcome...")
        if success:
            self.learning.learn_from_success(raw_input, plan.get('approach'))
            self.memory.remember(raw_input, plan.get('approach'), final_result, perception_data.get('emotion'))
            raw_response = f"Done! {plan.get('understanding')} completed successfully."
        else:
            self.learning.learn_from_failure(raw_input, plan.get('approach'), error_msg)
            self.memory.remember(raw_input, plan.get('approach'), f"Failed: {error_msg}", perception_data.get('emotion'))
            raw_response = f"I tried to {plan.get('understanding')} but ran into an error: {error_msg}"
            
        # 5. EMOTE
        print("[IPBrain] ❤️ Adapting emotional response...")
        return self.emotion.adapt_response(raw_response, perception_data.get('emotion'))

    def shutdown(self):
        """Clean shutdown of resources."""
        print("[IPBrain] 💤 Shutting down core engines...")
        self.memory.close()

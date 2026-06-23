"""
features_loader.py — Load all new IP Prime v2.1 features

Import this in main.py to activate all 15 feature modules.
"""

# Import all feature modules
from actions.model_orchestrator import orchestrator, ModelOrchestrator
from actions.sentiment_analyzer import analyzer, SentimentAnalyzer
from actions.safe_code_executor import executor, SafeCodeExecutor
from actions.workflow_engine import engine, WorkflowEngine
from actions.advanced_memory import memory, AdvancedMemory
from actions.screenshot_ocr import ocr, ScreenshotOCR
from actions.quick_notes import notes, QuickNotes
from actions.system_monitor_ai import monitor, SystemMonitorAI
from actions.clipboard_history import clipboard, ClipboardHistory
from actions.content_generator import generator, ContentGenerator
from actions.habit_tracker_ai import tracker, HabitTrackerAI
from actions.battery_optimizer import optimizer, BatteryOptimizer
from actions.story_generator import generator as story_gen, StoryGenerator
from actions.pomodoro_ai import pomodoro, PomodoroAI
from actions.anomaly_detector import detector, AnomalyDetector
from actions.elite_coder import elite, EliteCoder

# Feature registry
FEATURES = {
    "model_orchestrator": orchestrator,
    "sentiment_analyzer": analyzer,
    "code_executor": executor,
    "workflow_engine": engine,
    "advanced_memory": memory,
    "screenshot_ocr": ocr,
    "quick_notes": notes,
    "system_monitor": monitor,
    "clipboard_history": clipboard,
    "content_generator": generator,
    "habit_tracker": tracker,
    "battery_optimizer": optimizer,
    "story_generator": story_gen,
    "pomodoro": pomodoro,
    "anomaly_detector": detector,
    "elite_coder": elite
}

def get_feature(name: str):
    """Get a feature by name."""
    return FEATURES.get(name.lower())

def list_features():
    """List all available features."""
    return list(FEATURES.keys())

def init_all_features():
    """Initialize all features with defaults."""
    
    # Establish baselines
    monitor.get_system_stats()
    detector.establish_baseline()
    memory.get_memory_stats()
    
    return {
        "status": "All features initialized",
        "features": len(FEATURES),
        "modules": list(FEATURES.keys())
    }

# Quick command aliases
def query(prompt, model="gemini"):
    """Quick query with model selection."""
    return orchestrator.query(prompt, model=model)

def analyze_sentiment(text):
    """Quick sentiment analysis."""
    return analyzer.analyze(text)

def add_note(text):
    """Quick note addition."""
    return notes.add_note(text)

def log_habit(habit_name):
    """Quick habit logging."""
    return tracker.log_habit(habit_name)

def check_system():
    """Check system health."""
    health = monitor.get_health_score()
    anomalies = detector.detect_anomalies()
    battery = optimizer.get_battery_status()
    return {
        "health": health,
        "anomalies": anomalies,
        "battery": battery
    }

if __name__ == "__main__":
    print("IP Prime v2.1 Features Loader")
    print("=" * 40)
    print(f"Available features: {len(FEATURES)}")
    for name in FEATURES.keys():
        print(f"  ✓ {name}")
    print("\nInitializing all features...")
    result = init_all_features()
    print(f"✅ {result['status']}")

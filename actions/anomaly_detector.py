"""
anomaly_detector.py — AI Anomaly Detection & Auto-Fix

Detects unusual system behavior and suggests fixes.
"""

import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any
import statistics


class AnomalyDetector:
    """Detects and responds to system anomalies."""
    
    def __init__(self):
        self.baseline = {}
        self.history: List[Dict] = []
        self.anomalies: List[Dict] = []
    
    def establish_baseline(self) -> Dict[str, Any]:
        """Establish normal system behavior baseline."""
        
        samples = []
        for _ in range(5):
            sample = {
                "cpu": psutil.cpu_percent(interval=0.5),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage('/').percent
            }
            samples.append(sample)
        
        self.baseline = {
            "cpu_avg": statistics.mean([s["cpu"] for s in samples]),
            "cpu_stdev": statistics.stdev([s["cpu"] for s in samples]) if len(samples) > 1 else 0,
            "memory_avg": statistics.mean([s["memory"] for s in samples]),
            "memory_stdev": statistics.stdev([s["memory"] for s in samples]) if len(samples) > 1 else 0,
            "established_at": datetime.now().isoformat()
        }
        
        return {
            "baseline_established": True,
            "cpu_baseline": round(self.baseline["cpu_avg"], 1),
            "memory_baseline": round(self.baseline["memory_avg"], 1)
        }
    
    def detect_anomalies(self) -> List[Dict]:
        """Scan for anomalies in system behavior."""
        
        if not self.baseline:
            return [{"warning": "Baseline not established. Run establish_baseline() first"}]
        
        current = {
            "cpu": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('/').percent,
            "timestamp": datetime.now().isoformat()
        }
        
        self.history.append(current)
        detected = []
        
        # CPU anomaly
        cpu_deviation = abs(current["cpu"] - self.baseline["cpu_avg"])
        if cpu_deviation > (self.baseline["cpu_stdev"] * 2 or 20):
            detected.append({
                "type": "cpu_spike",
                "severity": "high" if current["cpu"] > 80 else "medium",
                "current": current["cpu"],
                "baseline": self.baseline["cpu_avg"],
                "message": f"⚠️ Unexpected CPU usage: {current['cpu']}%"
            })
            self.anomalies.append(detected[-1])
        
        # Memory anomaly
        mem_deviation = abs(current["memory"] - self.baseline["memory_avg"])
        if mem_deviation > (self.baseline["memory_stdev"] * 2 or 15):
            detected.append({
                "type": "memory_spike",
                "severity": "high" if current["memory"] > 85 else "medium",
                "current": current["memory"],
                "baseline": self.baseline["memory_avg"],
                "message": f"⚠️ Unexpected memory usage: {current['memory']}%"
            })
            self.anomalies.append(detected[-1])
        
        # Disk space anomaly
        if current["disk"] > 90:
            detected.append({
                "type": "disk_full",
                "severity": "critical",
                "current": current["disk"],
                "message": "🔴 Disk almost full!"
            })
            self.anomalies.append(detected[-1])
        
        return detected
    
    def get_suggestions(self) -> List[str]:
        """Get suggestions for detected anomalies."""
        
        if not self.anomalies:
            return ["✅ No anomalies detected. System running normally."]
        
        suggestions = []
        
        for anomaly in self.anomalies[-5:]:  # Last 5 anomalies
            if anomaly["type"] == "cpu_spike":
                suggestions.append("• Close unused applications")
                suggestions.append("• Check Task Manager for CPU-heavy processes")
                suggestions.append("• Run malware scan if spike persists")
            elif anomaly["type"] == "memory_spike":
                suggestions.append("• Restart your computer")
                suggestions.append("• Close memory-heavy applications (browsers, IDEs)")
                suggestions.append("• Check for memory leaks in running programs")
            elif anomaly["type"] == "disk_full":
                suggestions.append("• Delete temporary files (Temp folder, Downloads)")
                suggestions.append("• Move files to external storage")
                suggestions.append("• Empty Recycle Bin")
                suggestions.append("• Run Disk Cleanup utility")
        
        return list(dict.fromkeys(suggestions))  # Remove duplicates
    
    def get_suspicious_processes(self) -> List[Dict]:
        """Find potentially suspicious processes."""
        
        suspicious = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.as_dict(attrs=['pid', 'name', 'cpu_percent', 'memory_percent'])
                cpu = pinfo.get('cpu_percent') or 0
                memory = pinfo.get('memory_percent') or 0
                
                # Flag high resource usage
                if cpu > 30 or memory > 20:
                    suspicious.append({
                        "name": pinfo['name'],
                        "pid": pinfo['pid'],
                        "cpu": cpu,
                        "memory": memory,
                        "risk": "high" if (cpu > 80 or memory > 50) else "medium"
                    })
            except:
                pass
        
        # Sort by risk
        suspicious.sort(key=lambda x: x["risk"], reverse=True)
        return suspicious[:10]
    
    def auto_fix_suggestions(self) -> Dict[str, Any]:
        """Get auto-fix suggestions."""
        
        anomalies = self.detect_anomalies()
        suggestions = self.get_suggestions()
        
        fixes = {
            "quick_fixes": [
                "Restart explorer.exe",
                "Clear temp files",
                "Disable startup programs",
                "Update drivers"
            ],
            "aggressive_fixes": [
                "Restart system",
                "Run disk cleanup",
                "Perform malware scan",
                "Reinstall problematic software"
            ],
            "current_anomalies": len(anomalies),
            "recommendations": suggestions[:5]
        }
        
        return fixes
    
    def get_anomaly_report(self) -> Dict[str, Any]:
        """Get detailed anomaly report."""
        
        return {
            "report_time": datetime.now().isoformat(),
            "total_anomalies_detected": len(self.anomalies),
            "recent_anomalies": self.anomalies[-10:],
            "history_samples": len(self.history),
            "system_health": self._calculate_health()
        }
    
    def _calculate_health(self) -> str:
        """Calculate system health score."""
        
        if len(self.history) < 2:
            return "unknown"
        
        recent = self.history[-10:]
        avg_cpu = statistics.mean([h["cpu"] for h in recent])
        avg_memory = statistics.mean([h["memory"] for h in recent])
        
        if avg_cpu > 80 or avg_memory > 85:
            return "poor"
        elif avg_cpu > 60 or avg_memory > 70:
            return "fair"
        else:
            return "good"


detector = AnomalyDetector()

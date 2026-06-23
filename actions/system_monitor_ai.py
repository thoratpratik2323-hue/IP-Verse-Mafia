"""
system_monitor_ai.py — AI-Powered System Health Dashboard

Monitor CPU, RAM, disk, temperature with intelligent alerts.
"""

import psutil
from datetime import datetime
from typing import Dict, Any, List
import statistics


class SystemMonitorAI:
    """Monitors system health with AI insights."""
    
    def __init__(self):
        self.history: List[Dict] = []
        self.thresholds = {
            "cpu": 80,
            "memory": 85,
            "disk": 90,
            "temp": 80
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            stats = {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "cores": psutil.cpu_count(),
                    "freq": psutil.cpu_freq().current if psutil.cpu_freq() else None
                },
                "memory": {
                    "percent": memory.percent,
                    "used_gb": memory.used / (1024**3),
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3)
                },
                "disk": {
                    "percent": disk.percent,
                    "used_gb": disk.used / (1024**3),
                    "total_gb": disk.total / (1024**3),
                    "free_gb": disk.free / (1024**3)
                },
                "processes": {
                    "total": len(psutil.pids()),
                    "running": sum(1 for p in psutil.pids() if self._is_running(p))
                }
            }
            
            self.history.append(stats)
            return stats
        except Exception as e:
            return {"error": str(e)}
    
    def _is_running(self, pid: int) -> bool:
        """Check if process is running."""
        try:
            p = psutil.Process(pid)
            return p.status() == psutil.STATUS_RUNNING
        except:
            return False
    
    def get_health_score(self) -> Dict[str, Any]:
        """Calculate overall system health score (0-100)."""
        stats = self.get_system_stats()
        
        if "error" in stats:
            return {"error": stats["error"]}
        
        # Calculate scores
        cpu_score = max(0, 100 - stats["cpu"]["percent"])
        mem_score = max(0, 100 - stats["memory"]["percent"])
        disk_score = max(0, 100 - stats["disk"]["percent"])
        
        overall = (cpu_score + mem_score + disk_score) / 3
        
        return {
            "overall_score": round(overall, 1),
            "cpu_score": round(cpu_score, 1),
            "memory_score": round(mem_score, 1),
            "disk_score": round(disk_score, 1),
            "status": self._get_status(overall)
        }
    
    def _get_status(self, score: float) -> str:
        """Get health status from score."""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Fair"
        else:
            return "Poor"
    
    def get_alerts(self) -> List[str]:
        """Get system health alerts."""
        stats = self.get_system_stats()
        alerts = []
        
        if stats["cpu"]["percent"] > self.thresholds["cpu"]:
            alerts.append(f"⚠️ High CPU usage: {stats['cpu']['percent']}%")
        
        if stats["memory"]["percent"] > self.thresholds["memory"]:
            alerts.append(f"⚠️ High memory usage: {stats['memory']['percent']}%")
        
        if stats["disk"]["percent"] > self.thresholds["disk"]:
            alerts.append(f"⚠️ Low disk space: {stats['disk']['percent']}% used")
        
        return alerts
    
    def get_top_processes(self, top_n: int = 5, by: str = "memory") -> List[Dict]:
        """Get top processes by CPU or memory."""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    pinfo = proc.as_dict(attrs=['pid', 'name', 'cpu_percent', 'memory_percent'])
                    processes.append(pinfo)
                except:
                    pass
            
            # Sort by requested metric
            key = 'memory_percent' if by == "memory" else 'cpu_percent'
            processes.sort(key=lambda x: x.get(key, 0) or 0, reverse=True)
            
            return processes[:top_n]
        except Exception as e:
            return []
    
    def set_alert_threshold(self, metric: str, value: float) -> bool:
        """Set custom alert threshold."""
        if metric in self.thresholds:
            self.thresholds[metric] = value
            return True
        return False
    
    def get_history_stats(self) -> Dict[str, Any]:
        """Get statistics from history."""
        if len(self.history) < 2:
            return {"error": "Insufficient history"}
        
        cpu_values = [h["cpu"]["percent"] for h in self.history]
        mem_values = [h["memory"]["percent"] for h in self.history]
        
        return {
            "samples": len(self.history),
            "cpu": {
                "average": round(statistics.mean(cpu_values), 1),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory": {
                "average": round(statistics.mean(mem_values), 1),
                "max": max(mem_values),
                "min": min(mem_values)
            }
        }


monitor = SystemMonitorAI()

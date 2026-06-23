"""
battery_optimizer.py — Intelligent Battery Optimization

Close unnecessary apps and optimize power consumption.
"""

import psutil
import os
from typing import Dict, List, Any


class BatteryOptimizer:
    """Optimizes battery life by managing processes."""
    
    # Apps that typically drain battery
    BATTERY_DRAINERS = {
        "chrome": "Browser with many tabs",
        "firefox": "Browser with media",
        "spotify": "Music streaming",
        "discord": "Always-on communication",
        "slack": "Background notifications",
        "Teams": "Video conferencing",
        "zoom": "Virtual meetings",
        "steam": "Gaming platform",
        "visual studio": "Development IDEs"
    }
    
    # Priority levels for closing
    PRIORITY_TO_CLOSE = 3  # High priority processes to suggest closing
    
    def get_battery_status(self) -> Dict[str, Any]:
        """Get current battery status."""
        try:
            battery = psutil.sensors_battery()
            
            if not battery:
                return {"error": "No battery detected (desktop?)"}
            
            return {
                "percent": battery.percent,
                "is_plugged": battery.power_plugged,
                "seconds_left": battery.secsleft,
                "time_remaining": self._format_time(battery.secsleft),
                "status": "Charging" if battery.power_plugged else "On Battery"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _format_time(self, seconds: int) -> str:
        """Format seconds to readable time."""
        if seconds == psutil.POWER_TIME_UNLIMITED:
            return "Calculating..."
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    
    def get_battery_drainers(self) -> List[Dict]:
        """Get processes that are draining battery."""
        drainers = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.as_dict(attrs=['pid', 'name', 'cpu_percent', 'memory_percent'])
                name_lower = pinfo['name'].lower()
                
                # Check if this is a known drainer
                for drainer, description in self.BATTERY_DRAINERS.items():
                    if drainer.lower() in name_lower:
                        cpu_usage = pinfo.get('cpu_percent') or 0
                        memory_usage = pinfo.get('memory_percent') or 0
                        drain_score = (cpu_usage * 0.7) + (memory_usage * 0.3)
                        
                        drainers.append({
                            "process": pinfo['name'],
                            "pid": pinfo['pid'],
                            "cpu_percent": cpu_usage,
                            "memory_percent": memory_usage,
                            "drain_score": round(drain_score, 1),
                            "description": description
                        })
            except:
                pass
        
        # Sort by drain score
        drainers.sort(key=lambda x: x['drain_score'], reverse=True)
        return drainers[:10]
    
    def optimize_battery(self) -> Dict[str, Any]:
        """Get optimization recommendations."""
        battery = self.get_battery_status()
        
        if "error" in battery:
            return battery
        
        recommendations = []
        actions_to_take = []
        
        # Battery percentage based recommendations
        if battery["percent"] < 20:
            recommendations.append("🔴 Critical battery! Enable maximum power saving mode.")
            recommendations.append("Close all unnecessary applications immediately.")
        elif battery["percent"] < 50:
            recommendations.append("🟠 Battery below 50%. Consider using battery saver mode.")
        
        # Check for drainers
        drainers = self.get_battery_drainers()
        if drainers:
            top_drainer = drainers[0]
            if top_drainer["drain_score"] > 20:
                recommendations.append(f"⚠️ {top_drainer['process']} is draining battery ({top_drainer['drain_score']}% drain score).")
                actions_to_take.append({
                    "action": f"Consider closing {top_drainer['process']}",
                    "process": top_drainer['process'],
                    "pid": top_drainer['pid']
                })
        
        # General tips
        if battery["percent"] < 80 and not battery["is_plugged"]:
            recommendations.append("💡 Reduce screen brightness to extend battery life.")
            recommendations.append("💡 Disable Wi-Fi and Bluetooth if not in use.")
            recommendations.append("💡 Close background app refresh.")
        
        return {
            "battery_percent": battery["percent"],
            "time_remaining": battery.get("time_remaining"),
            "recommendations": recommendations,
            "top_drainers": drainers[:5],
            "suggested_actions": actions_to_take
        }
    
    def estimate_battery_life(self, actions: List[str] = None) -> Dict[str, str]:
        """Estimate battery life with optimizations."""
        battery = self.get_battery_status()
        
        if "error" in battery:
            return battery
        
        base_time = battery.get("seconds_left", 3600)
        
        optimizations = {
            "reduce_brightness": 1.3,
            "close_chrome": 1.5,
            "disable_wifi": 1.2,
            "disable_bluetooth": 1.1,
            "close_spotify": 1.4,
            "max_power_saving": 2.0
        }
        
        estimated_improvement = 1.0
        for action in (actions or []):
            estimated_improvement *= optimizations.get(action.lower(), 1.0)
        
        estimated_new_life = base_time * estimated_improvement
        
        return {
            "current_estimate": self._format_time(int(base_time)),
            "with_optimizations": self._format_time(int(estimated_new_life)),
            "improvement_percent": round((estimated_improvement - 1) * 100, 1)
        }
    
    def close_process(self, process_name: str) -> Dict[str, Any]:
        """Safely close a process."""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == process_name.lower():
                    proc.kill()
                    return {"success": True, "closed": process_name}
            
            return {"success": False, "error": f"Process '{process_name}' not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_optimization_profile(self) -> Dict[str, Any]:
        """Get detailed optimization recommendations."""
        return {
            "power_modes": {
                "balanced": "Default mode with balanced performance and battery life",
                "battery_saver": "Reduced performance for extended battery life",
                "maximum_performance": "Full power (not recommended on battery)"
            },
            "quick_wins": [
                "Reduce screen brightness (saves 10-20%)",
                "Close browser tabs (saves 5-15%)",
                "Disable Wi-Fi/Bluetooth (saves 5-10%)",
                "Close video/music apps (saves 10-25%)",
                "Enable airplane mode (saves 15-30%)"
            ],
            "advanced": [
                "Use Edge instead of Chrome (more efficient)",
                "Disable background app refresh",
                "Reduce screen refresh rate if possible",
                "Close background Windows Update"
            ]
        }


optimizer = BatteryOptimizer()

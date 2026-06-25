import logging
import psutil
import platform
import subprocess

def get_battery_info() -> dict:
    try:
        battery = psutil.sensors_battery()
        if battery:
            return {
                "percent": battery.percent,
                "secsleft": battery.secsleft,
                "power_plugged": battery.power_plugged
            }
    except Exception as _exc:  # noqa: BLE001
        logging.debug("[%s] Suppressed: %s", __name__, _exc)
    return {}

def get_cpu_temp() -> float:
    if platform.system() == "Windows":
        try:
            cmd = "Get-CimInstance -Namespace root/wmi -ClassName MsAcpi_ThermalZoneTemperature | Select-Object -ExpandProperty CurrentTemperature"
            res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=3)
            if res.returncode == 0 and res.stdout.strip():
                # Value is in tenths of Kelvin
                val = float(res.stdout.strip().split()[0])
                temp_c = (val / 10.0) - 273.15
                return round(temp_c, 1)
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)
    else:
        try:
            temps = psutil.sensors_temperatures()
            if "coretemp" in temps:
                return temps["coretemp"][0].current
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)
    return -1.0

def system_monitor(parameters: dict, player=None) -> str:
    bat = get_battery_info()
    temp = get_cpu_temp()
    
    cpu_usage = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    
    status_parts = []
    
    if bat:
        status_parts.append(f"Battery is at {bat['percent']}% ({'charging' if bat['power_plugged'] else 'not charging'}).")
        if bat['percent'] < 20 and not bat['power_plugged']:
            status_parts.append("⚠️ WARNING: Battery is low. Please plug in your charger.")
    else:
        status_parts.append("Battery sensor unavailable.")
        
    if temp > 0:
        status_parts.append(f"CPU temperature is {temp}°C.")
        if temp > 85:
            status_parts.append("⚠️ WARNING: CPU is running hot! Consider closing heavy apps.")
    
    status_parts.append(f"CPU usage is {cpu_usage}% and RAM usage is {ram.percent}%.")
    
    return " ".join(status_parts)

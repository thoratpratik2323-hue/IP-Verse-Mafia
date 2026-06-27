"""Self-hosted homelab — Docker container management."""
from __future__ import annotations

import json
import subprocess

from prime_platform.config import load_prime_config


def _docker_cmd(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    cfg = load_prime_config()
    docker = cfg.get("homelab", {}).get("docker_path", "docker")
    try:
        return subprocess.run(
            [docker, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args=[docker, *args],
            returncode=127,
            stdout="",
            stderr=f"Docker command not found: '{docker}' is not installed or not in PATH."
        )
    except Exception as e:
        return subprocess.CompletedProcess(
            args=[docker, *args],
            returncode=1,
            stdout="",
            stderr=str(e)
        )


def docker_status() -> str:
    r = _docker_cmd("version", "--format", "{{.Server.Version}}", timeout=6)
    if r.returncode != 0:
        return (
            "Docker is not available on this machine.\n"
            f"Error: {(r.stderr or r.stdout or 'unknown').strip()}\n"
            "Install Docker Desktop or set homelab.docker_path in config/prime_features.json"
        )
    version = (r.stdout or "").strip()
    return f"Docker online (server {version})"


def list_containers(all_containers: bool = False) -> str:
    if docker_status().startswith("Docker is not"):
        return docker_status()
    args = ["ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"]
    if all_containers:
        args.insert(1, "-a")
    r = _docker_cmd(*args, timeout=12)
    if r.returncode != 0:
        return f"docker ps failed: {r.stderr or r.stdout}"
    out = (r.stdout or "").strip()
    if not out:
        return "No containers running." if not all_containers else "No containers found."
    return "═══ DOCKER CONTAINERS ═══\n" + out


def container_action(action: str, name: str) -> str:
    action = (action or "").strip().lower()
    name = (name or "").strip()
    if not name:
        return "Provide container name for homelab action."

    if docker_status().startswith("Docker is not"):
        return docker_status()

    mapping = {
        "start": ["start", name],
        "stop": ["stop", name],
        "restart": ["restart", name],
        "logs": ["logs", "--tail", "80", name],
        "stats": ["stats", "--no-stream", name],
        "inspect": ["inspect", name, "--format", "{{json .State}}"],
    }
    if action not in mapping:
        return f"Unknown action '{action}'. Use: start, stop, restart, logs, stats, inspect"

    r = _docker_cmd(*mapping[action], timeout=60)
    if r.returncode != 0:
        return f"docker {action} failed: {(r.stderr or r.stdout or '').strip()}"
    out = (r.stdout or r.stderr or "").strip()
    if action == "inspect" and out:
        try:
            state = json.loads(out)
            return f"Container {name}: status={state.get('Status')}, running={state.get('Running')}"
        except Exception:
            pass
    return out or f"docker {action} {name}: OK"


def compose_action(action: str, project_path: str = "") -> str:
    action = (action or "ps").strip().lower()
    if docker_status().startswith("Docker is not"):
        return docker_status()
    args = ["compose", action]
    if project_path:
        args.extend(["-f", f"{project_path}/docker-compose.yml"])
    r = _docker_cmd(*args, timeout=120)
    if r.returncode != 0:
        return f"docker compose {action} failed: {(r.stderr or r.stdout or '').strip()}"
    return (r.stdout or r.stderr or "").strip() or f"compose {action}: OK"

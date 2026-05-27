"""
docker_controller.py — Docker and virtual machine (VirtualBox/VMware) controller action for IP Prime.

Interfaces with the Docker daemon via docker-py and controls local hypervisors via
vboxmanage subprocess utilities.
"""

from __future__ import annotations

import logging
import os
import subprocess
import shutil
from typing import Any, Optional

logger = logging.getLogger("ip_prime.docker_controller")

MOCK_CONTAINERS = [
    {"id": "d13f8902a11b", "name": "postgres_db", "image": "postgres:15-alpine", "status": "running", "ports": "5432/tcp"},
    {"id": "e42fa023910c", "name": "redis_cache", "image": "redis:7-alpine", "status": "stopped", "ports": "6379/tcp"}
]

MOCK_VMS = [
    {"uuid": "3a09fa23-90bc-432d-ae21-023fa098b1c2", "name": "Ubuntu_Server_Core", "status": "powered off"},
    {"uuid": "e9b023af-43cd-498b-bc11-a890bc23df01", "name": "Windows_Sandbox_Test", "status": "running"}
]

def list_containers() -> str:
    """Lists all active and stopped Docker containers on the host."""
    logger.info("Listing Docker containers...")
    
    # Try using Docker Python SDK
    try:
        import docker
        client = docker.from_env()
        containers = client.containers.list(all=True)
        if containers:
            output = ["### [DOCKER] Active Container Configurations:\n"]
            for c in containers:
                output.append(f"• **{c.name}** ({c.short_id}) | Image: {c.image.tags[0]} | Status: {c.status.upper()}")
            return "\n".join(output)
        else:
            return "No Docker containers found on the host machine, sir."
    except Exception as e:
        logger.warning("Docker SDK connection failed (%s). Using mock simulation fallback.", e)

    # Simulation fallback
    output = ["### [DOCKER (Simulated)] active container grid:\n"]
    for c in MOCK_CONTAINERS:
        output.append(f"• **{c['name']}** ({c['id']}) | Image: {c['image']} | Status: {c['status'].upper()} | Ports: {c['ports']}")
        
    return "\n".join(output) + "\n\nOllama/Docker daemon is running in test configuration, sir."

def control_container(container_name: str, action: str) -> str:
    """Sends start, stop, or restart signals to a Docker container."""
    if not container_name:
        return "Container identifier is required, sir."
        
    logger.info("Executing container action: %s on %s", action, container_name)
    
    try:
        import docker
        client = docker.from_env()
        container = client.containers.get(container_name)
        
        if action == "start":
            container.start()
        elif action == "stop":
            container.stop()
        elif action == "restart":
            container.restart()
            
        return f"Successfully sent '{action}' directive to live container '{container_name}', sir!"
    except Exception as e:
        logger.warning("Could not execute container SDK action (%s). Simulating.", e)

    # Simulation update
    for c in MOCK_CONTAINERS:
        if c["name"].lower() == container_name.lower().strip():
            if action == "start":
                c["status"] = "running"
            elif action == "stop":
                c["status"] = "stopped"
            return f"Simulated container action success: '{action.upper()}' dispatched to container '{c['name']}'!"

    return f"Container matching identifier '{container_name}' was not found, sir."

def get_container_logs(container_name: str, tail: int = 20) -> str:
    """Retrieves execution logs from a container."""
    logger.info("Fetching logs for container: %s", container_name)
    try:
        import docker
        client = docker.from_env()
        container = client.containers.get(container_name)
        logs = container.logs(tail=tail).decode("utf-8")
        return f"### [LOGS] Container: {container_name}\n```\n{logs}\n```"
    except Exception:
        pass
        
    return (
        f"### [LOGS (Simulated)] Container: {container_name}\n"
        "```\n"
        "2026-05-27 11:30:15 [info] PostgreSQL Database Server initialized.\n"
        "2026-05-27 11:30:16 [info] Accepting TCP/IP connections on port 5432.\n"
        "2026-05-27 11:30:18 [info] Autovacuum daemon online. Ready for queries.\n"
        "```"
    )

def list_vms() -> str:
    """Lists virtual machines registered under VirtualBox (VBoxManage)."""
    logger.info("Listing registered hypervisor virtual machines...")
    
    vbox = shutil.which("vboxmanage")
    if vbox:
        try:
            res = subprocess.run([vbox, "list", "vms"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                output = ["### [VIRTUALBOX] Registered Virtual Machines:\n"]
                for line in res.stdout.strip().split("\n"):
                    if line:
                        output.append(f"• {line}")
                return "\n".join(output)
        except Exception as e:
            logger.error("Error listing vbox VMs: %s", e)

    # Simulation fallback
    output = ["### [HYPERVISOR (Simulated)] Virtual Machines registered:\n"]
    for vm in MOCK_VMS:
        output.append(f"• **{vm['name']}** ({vm['uuid'][:8]}) | Status: {vm['status'].upper()}")
        
    return "\n".join(output)

def control_vm(vm_name: str, action: str) -> str:
    """Starts or stops virtual hypervisor machines via VBoxManage subprocesses."""
    if not vm_name:
        return "Virtual machine identifier is required, sir."
        
    logger.info("Sending VM control directive: %s to %s", action, vm_name)
    
    vbox = shutil.which("vboxmanage")
    if vbox:
        try:
            if action == "start":
                # Headless mode recommended for background hypervisors
                cmd = [vbox, "startvm", vm_name, "--type", "headless"]
            elif action == "stop":
                cmd = [vbox, "controlvm", vm_name, "poweroff"]
            else:
                return "Unknown VM control action, sir."

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            if res.returncode == 0:
                return f"Virtual Machine '{vm_name}' successfully received command: {action.upper()}!"
            else:
                return f"VBoxManage returned error: {res.stderr.strip()}"
        except Exception as e:
            logger.error("VM command execution error: %s", e)

    # Simulation fallback
    for vm in MOCK_VMS:
        if vm["name"].lower() == vm_name.lower().strip():
            if action == "start":
                vm["status"] = "running"
            elif action == "stop":
                vm["status"] = "powered off"
            return f"Simulated hypervisor command success: VM '{vm['name']}' status is now {vm['status'].upper()}."
            
    return f"Virtual machine '{vm_name}' was not found in registered hypervisors list, sir."

def docker_controller(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for docker_controller action."""
    action = parameters.get("action", "list_containers").lower().strip()
    name = parameters.get("name", "")
    vm_name = parameters.get("vm_name", name)
    container_action = parameters.get("container_action", "start")
    vm_action = parameters.get("vm_action", "start")
    tail = int(parameters.get("tail", 20))
    
    if action == "list_containers":
        return list_containers()
    elif action == "control_container":
        return control_container(name, container_action)
    elif action == "logs":
        return get_container_logs(name, tail)
    elif action == "list_vms":
        return list_vms()
    elif action == "control_vm":
        return control_vm(vm_name, vm_action)
    else:
        return "Unknown Docker or VM controller action parameter, sir."

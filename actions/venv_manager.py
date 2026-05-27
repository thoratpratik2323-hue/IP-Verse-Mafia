"""
venv_manager.py — Local virtualenv and Conda environments manager module for IP Prime.

Executes subprocess system shell directives to create, list, delete, and inspect
python virtual environments and conda environments.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("ip_prime.venv_manager")

BASE_DIR = Path(__file__).resolve().parent.parent

def list_venvs() -> str:
    """Lists Conda and common local directory virtual environments."""
    logger.info("Listing Python environments...")
    output = ["### [ENVIRONMENT ENGINE] Registered Python Environments:\n"]
    
    # 1. Conda check
    conda_path = shutil.which("conda")
    if conda_path:
        try:
            res = subprocess.run([conda_path, "env", "list"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                output.append("**Conda Environments**:")
                for line in res.stdout.strip().split("\n"):
                    if line and not line.startswith("#"):
                        output.append(f"  • {line.strip()}")
        except Exception as e:
            logger.error("Conda environment list query failed: %s", e)
            
    # 2. Local venv check
    output.append("\n**Local Directories**:")
    common_names = [".venv", "venv", "env", "ml_project"]
    found_local = False
    for name in common_names:
        path = BASE_DIR / name
        if path.exists() and (path / "Scripts" / "python.exe").exists() or (path / "bin" / "python").exists():
            output.append(f"  • [VENV] {name} | Path: `{path}`")
            found_local = True
            
    if not found_local:
        output.append("  • No local directory virtual environments found.")
        
    return "\n".join(output)

def create_venv(name: str, mode: str = "venv") -> str:
    """Creates a new virtual environment using venv or Conda."""
    if not name:
        return "Virtual environment name is required, sir."
        
    logger.info("Creating python environment '%s' using %s...", name, mode)
    
    if mode.lower() == "conda":
        conda = shutil.which("conda")
        if not conda:
            return "Conda is not installed on this system, sir."
        try:
            cmd = [conda, "create", "-y", "-n", name, "python=3.10"]
            subprocess.run(cmd, check=True, timeout=120)
            return f"Conda environment '{name}' successfully created with Python 3.10, sir!"
        except Exception as e:
            return f"Failed to create Conda environment: {e}, sir."
    else:
        # Standard venv creation
        target_path = BASE_DIR / name
        try:
            subprocess.run([sys.executable, "-m", "venv", str(target_path)], check=True, timeout=90)
            return f"Sabash sir! Local venv '{name}' successfully initialized at path: `{target_path}`."
        except Exception as e:
            return f"Failed to initialize venv: {e}, sir."

def delete_venv(name: str, mode: str = "venv") -> str:
    """Removes a virtual environment."""
    if not name:
        return "Virtual environment name is required, sir."
        
    logger.info("Deleting environment '%s'...", name)
    
    if mode.lower() == "conda":
        conda = shutil.which("conda")
        if not conda:
            return "Conda is not installed, sir."
        try:
            cmd = [conda, "env", "remove", "-y", "-n", name]
            subprocess.run(cmd, check=True, timeout=60)
            return f"Conda environment '{name}' successfully removed, sir."
        except Exception as e:
            return f"Failed to delete Conda environment: {e}, sir."
    else:
        # Standard folder sweep
        target_path = BASE_DIR / name
        if target_path.exists():
            try:
                shutil.rmtree(target_path)
                return f"Local virtual environment folder '{name}' successfully deleted, sir."
            except Exception as e:
                return f"Failed to delete folder: {e}, sir."
        return f"Environment '{name}' was not found at `{target_path}`, sir."

def list_packages(venv_path_or_conda_name: str, mode: str = "venv") -> str:
    """Lists installed packages inside the selected environment."""
    logger.info("Listing packages for environment: %s", venv_path_or_conda_name)
    
    if mode.lower() == "conda":
        conda = shutil.which("conda")
        if conda:
            try:
                res = subprocess.run([conda, "list", "-n", venv_path_or_conda_name], capture_output=True, text=True, timeout=10)
                if res.returncode == 0:
                    return f"### [CONDA] Packages in '{venv_path_or_conda_name}':\n```\n{res.stdout[:1200]}\n```"
            except Exception as e:
                return f"Failed to query Conda packages: {e}"
    else:
        # Resolve python executable inside local venv
        p = Path(venv_path_or_conda_name)
        if not p.exists():
            p = BASE_DIR / venv_path_or_conda_name
            
        py_exec = p / "Scripts" / "pip.exe" if os.name == "nt" else p / "bin" / "pip"
        if py_exec.exists():
            try:
                res = subprocess.run([str(py_exec), "list"], capture_output=True, text=True, timeout=10)
                return f"### [VENV] Packages in '{venv_path_or_conda_name}':\n```\n{res.stdout[:1200]}\n```"
            except Exception as e:
                return f"Failed to list pip packages: {e}"
                
    return "Could not resolve the target Python environment path or Conda name, sir."

def install_package(venv_path_or_conda_name: str, package_name: str, mode: str = "venv") -> str:
    """Installs a package in the selected environment."""
    if not package_name:
        return "Package name is required to install, sir."
        
    logger.info("Installing package %s inside environment %s...", package_name, venv_path_or_conda_name)
    
    if mode.lower() == "conda":
        conda = shutil.which("conda")
        if conda:
            try:
                subprocess.run([conda, "install", "-y", "-n", venv_path_or_conda_name, package_name], check=True, timeout=120)
                return f"Package '{package_name}' successfully installed in Conda env '{venv_path_or_conda_name}'!"
            except Exception as e:
                return f"Conda install failed: {e}"
    else:
        p = Path(venv_path_or_conda_name)
        if not p.exists():
            p = BASE_DIR / venv_path_or_conda_name
        pip_exec = p / "Scripts" / "pip.exe" if os.name == "nt" else p / "bin" / "pip"
        if pip_exec.exists():
            try:
                subprocess.run([str(pip_exec), "install", package_name], check=True, timeout=90)
                return f"Package '{package_name}' successfully installed in local venv '{venv_path_or_conda_name}', sir!"
            except Exception as e:
                return f"Pip install failed: {e}"
                
    return "Could not find valid Python target environment to complete package installation, sir."

def venv_manager(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for venv_manager action."""
    action = parameters.get("action", "list").lower().strip()
    name = parameters.get("name", "")
    mode = parameters.get("mode", "venv")
    package = parameters.get("package", "")
    
    if action == "list":
        return list_venvs()
    elif action == "create":
        return create_venv(name, mode)
    elif action == "delete":
        return delete_venv(name, mode)
    elif action == "packages":
        target = name if name else ".venv"
        return list_packages(target, mode)
    elif action == "install":
        target = name if name else ".venv"
        return install_package(target, package, mode)
    else:
        return "Unknown environment manager action parameter, sir."

"""
actions/llama_factory_helper.py — Integrates LLaMA-Factory fine-tuning control loops.
Allows IP Prime to clone, run WebUI, and execute training jobs in the background.
"""

from __future__ import annotations

import os
import sys
import json
import subprocess
import threading
import logging
from typing import Any, Optional, Callable

logger = logging.getLogger("ip_prime.llama_factory")

# Base directory setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_file = os.path.join(BASE_DIR, "config", "paths.json")
projects_dir = os.path.join(BASE_DIR, "CODING PROJECTS")

if os.path.exists(config_file):
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            projects_dir = data.get("ip_given_dir", projects_dir)
    except Exception:
        pass

LLAMA_FACTORY_DIR = os.path.join(projects_dir, "LLaMA-Factory")

# Subprocess tracker
_active_processes: dict[str, subprocess.Popen] = {}
_process_lock = threading.Lock()

def register_process(name: str, proc: subprocess.Popen):
    with _process_lock:
        if name in _active_processes:
            try:
                _active_processes[name].terminate()
            except Exception:
                pass
        _active_processes[name] = proc

def terminate_process(name: str):
    with _process_lock:
        if name in _active_processes:
            try:
                _active_processes[name].terminate()
                _active_processes[name].wait(timeout=0.5)
            except Exception:
                pass
            del _active_processes[name]

def is_process_running(name: str) -> bool:
    with _process_lock:
        if name in _active_processes:
            return _active_processes[name].poll() is None
        return False

def check_repo_status() -> str:
    """Checks if LLaMA-Factory directory exists and contains source code."""
    if not os.path.exists(LLAMA_FACTORY_DIR):
        return "NOT_FOUND"
    src_dir = os.path.join(LLAMA_FACTORY_DIR, "src")
    if os.path.exists(src_dir):
        return "CLONED"
    return "INCOMPLETE"

def clone_llama_factory_bg(log_callback: Optional[Callable[[str], None]] = None) -> None:
    """Clones the repository and installs editable package in a background thread."""
    def run():
        os.makedirs(projects_dir, exist_ok=True)
        if log_callback:
            log_callback("SYS: Initiating LLaMA-Factory clone from GitHub...")
            log_callback(f"SYS: Target path: {LLAMA_FACTORY_DIR}")

        try:
            if not os.path.exists(LLAMA_FACTORY_DIR):
                proc = subprocess.Popen(
                    ["git", "clone", "--depth", "1", "https://github.com/hiyouga/LLaMA-Factory.git", "LLaMA-Factory"],
                    cwd=projects_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                register_process("clone", proc)
                
                # Stream logs
                for line in proc.stdout:
                    if log_callback:
                        log_callback(line.strip())
                proc.wait()
                
                if proc.returncode != 0:
                    if log_callback:
                        log_callback("SYS ERROR: Git clone failed. Check connection.")
                    return
            else:
                if log_callback:
                    log_callback("SYS: Repository folder already exists, skipping clone.")

            # Run pip install -e .[metrics]
            if log_callback:
                log_callback("SYS: Installing requirements in editable mode (pip install -e .)...")
                
            proc = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "-e", "."],
                cwd=LLAMA_FACTORY_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            register_process("install", proc)
            for line in proc.stdout:
                if log_callback:
                    log_callback(line.strip())
            proc.wait()

            if proc.returncode == 0:
                if log_callback:
                    log_callback("SYS SUCCESS: LLaMA-Factory setup completed successfully!")
            else:
                if log_callback:
                    log_callback(f"SYS WARNING: Installation returned non-zero code {proc.returncode}.")
        except Exception as e:
            if log_callback:
                log_callback(f"SYS ERROR during installation: {e}")
            logger.error("Error during LLaMA-Factory clone: %s", e)

    threading.Thread(target=run, daemon=True).start()

def launch_llama_board_bg(log_callback: Optional[Callable[[str], None]] = None) -> None:
    """Launches the LLaMA Board web UI in the background."""
    if check_repo_status() != "CLONED":
        if log_callback:
            log_callback("SYS ERROR: LLaMA-Factory is not cloned or setup yet. Please clone it first.")
        return

    if is_process_running("webui"):
        if log_callback:
            log_callback("SYS: LLaMA Board is already running in background.")
        return

    def run():
        if log_callback:
            log_callback("SYS: Launching LLaMA Board (WebUI)...")
        try:
            # Command to launch web UI (train_web.py or cli command)
            cmd = ["llamafactory-cli", "webui"]
            # Fallback check if llamafactory-cli command is not on global path
            # We can run standard python src/train_web.py
            if not os.path.exists(os.path.join(LLAMA_FACTORY_DIR, "src", "train_web.py")):
                if log_callback:
                    log_callback("SYS ERROR: LLaMA Board startup script train_web.py not found in source.")
                return

            # Check if command is responsive, otherwise fallback
            try:
                proc = subprocess.Popen(
                    [sys.executable, "src/train_web.py"],
                    cwd=LLAMA_FACTORY_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
            except Exception:
                proc = subprocess.Popen(
                    cmd,
                    cwd=LLAMA_FACTORY_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

            register_process("webui", proc)
            if log_callback:
                log_callback("SYS: WebUI process started. Listening on default port 7860 (Gradio)...")

            for line in proc.stdout:
                if log_callback:
                    log_callback(f"[WebUI] {line.strip()}")
            proc.wait()
        except Exception as e:
            if log_callback:
                log_callback(f"SYS ERROR: Failed to launch WebUI: {e}")

    threading.Thread(target=run, daemon=True).start()

def start_training_bg(parameters: dict[str, Any], log_callback: Optional[Callable[[str], None]] = None) -> None:
    """Starts a model training job using llamafactory-cli or train.py."""
    if check_repo_status() != "CLONED":
        if log_callback:
            log_callback("SYS ERROR: LLaMA-Factory is not setup. Please clone first.")
        return

    if is_process_running("train"):
        if log_callback:
            log_callback("SYS ERROR: An active training job is already running.")
        return

    model_name = parameters.get("model_name", "Qwen/Qwen2.5-1.5B-Instruct")
    dataset = parameters.get("dataset", "identity")
    finetuning_type = parameters.get("finetuning_type", "lora")
    output_dir = parameters.get("output_dir", "saves/qwen_lora")
    
    # Ensure relative paths resolve inside LLaMA-Factory folder
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(LLAMA_FACTORY_DIR, output_dir)
    os.makedirs(output_dir, exist_ok=True)

    def run():
        if log_callback:
            log_callback("SYS: Initializing training job...")
            log_callback(f"SYS: Model: {model_name} | Dataset: {dataset} | Type: {finetuning_type}")

        # Construct basic training parameters (yaml or cli arg format)
        # We write a custom yaml config or pass arguments
        config_path = os.path.join(output_dir, "train_config.yaml")
        yaml_config = {
            "stage": "sft",
            "do_train": True,
            "model_name_or_path": model_name,
            "dataset": dataset,
            "template": "default",
            "finetuning_type": finetuning_type,
            "lora_target": "all",
            "output_dir": output_dir,
            "overwrite_output_dir": True,
            "cutoff_len": 1024,
            "preprocessing_num_workers": 4,
            "per_device_train_batch_size": 2,
            "gradient_accumulation_steps": 4,
            "lr_scheduler_type": "cosine",
            "logging_steps": 10,
            "save_steps": 100,
            "learning_rate": 5e-5,
            "num_train_epochs": 3.0,
            "plot_loss": True,
            "fp16": True
        }

        try:
            import yaml
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_config, f, default_flow_style=False)
            cmd = ["llamafactory-cli", "train", config_path]
        except Exception:
            # Fallback CLI args
            cmd = [
                sys.executable, "src/train.py",
                "--stage", "sft",
                "--do_train", "True",
                "--model_name_or_path", model_name,
                "--dataset", dataset,
                "--template", "default",
                "--finetuning_type", finetuning_type,
                "--output_dir", output_dir,
                "--overwrite_output_dir", "True",
                "--per_device_train_batch_size", "2",
                "--num_train_epochs", "3.0",
                "--fp16", "True"
            ]

        # Write command run to logs
        if log_callback:
            log_callback(f"SYS COMMAND: {' '.join(cmd)}")

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=LLAMA_FACTORY_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            register_process("train", proc)
            
            # Stream stdout to logs
            for line in proc.stdout:
                if log_callback:
                    log_callback(line.strip())
            proc.wait()
            
            if proc.returncode == 0:
                if log_callback:
                    log_callback("SYS SUCCESS: Training job finished successfully!")
            else:
                if log_callback:
                    log_callback(f"SYS ERROR: Training job exited with error code {proc.returncode}.")
        except Exception as e:
            if log_callback:
                log_callback(f"SYS ERROR: Training failed: {e}")

    threading.Thread(target=run, daemon=True).start()

def llama_factory(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main action entry point for tool_dispatcher.py"""
    action = parameters.get("action", "").lower().strip()
    
    def log_to_player(txt: str):
        if player and hasattr(player, "write_log"):
            player.write_log(txt)
        logger.info(txt)

    if action == "clone":
        status = check_repo_status()
        if status == "CLONED":
            return "LLaMA-Factory is already cloned and setup, sir!"
        clone_llama_factory_bg(log_to_player)
        return "Started LLaMA-Factory repository clone and install in the background, sir."

    elif action == "webui":
        launch_llama_board_bg(log_to_player)
        return "Started LLaMA Board (WebUI) launch in the background. Gradio will open on port 7860, sir."

    elif action == "train":
        start_training_bg(parameters, log_to_player)
        return "Started LLaMA-Factory model training job in the background, sir."

    elif action == "status":
        status = check_repo_status()
        is_ui = "RUNNING" if is_process_running("webui") else "IDLE"
        is_tr = "RUNNING" if is_process_running("train") else "IDLE"
        return (
            f"LLaMA-Factory status: Repo: {status} | "
            f"LLaMA Board WebUI: {is_ui} | "
            f"Active Training Job: {is_tr}."
        )
    else:
        return f"Unknown LLaMA-Factory action '{action}', sir."

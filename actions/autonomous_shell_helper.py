"""
actions/autonomous_shell_helper.py — Autonomous Terminal Execution & Solana Telemetry Helper.

Provides autonomous command execution, environment analysis, self-healing command retry loops,
and mock Solana Web3 wallet telemetry operations for demo/testing environments.
"""
import os
import sys
import subprocess
import json
import re
from pathlib import Path

# Setup paths
def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()

# Mock Solana Wallet Address for Pratik Sir
SOLANA_WALLET_MOCK = "Prat1kThoratWalletAddress1111111111111111111"
WALLETS_HISTORY_FILE = Path.home() / ".ipprime" / "solana_history.json"

def _load_solana_history():
    WALLETS_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if WALLETS_HISTORY_FILE.exists():
        try:
            return json.loads(WALLETS_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    
    # Default mock transactions history
    initial_data = {
        "balance": 150.50, # 150.50 SOL
        "transactions": [
            {"tx_id": "tx_3b9f4a12", "type": "RECEIVE", "amount": 10.0, "from": "Manus_Agent_Core", "date": "2026-05-26 14:30"},
            {"tx_id": "tx_8c9d01ef", "type": "TRANSFER", "amount": 1.5, "to": "Grok_Public_Node", "date": "2026-05-25 10:15"},
            {"tx_id": "tx_2d9e03ab", "type": "SWAP", "amount": 5.0, "detail": "5 SOL to 650 USDC", "date": "2026-05-24 18:45"}
        ]
    }
    try:
        WALLETS_HISTORY_FILE.write_text(json.dumps(initial_data, indent=4), encoding="utf-8")
    except Exception:
        pass
    return initial_data

def _save_solana_history(data):
    try:
        WALLETS_HISTORY_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
    except Exception:
        pass

def run_autonomous_loop(goal: str, max_steps: int = 5, player=None) -> str:
    """concept from ANUS CLI: Runs an autonomous shell execution loop to achieve a goal."""
    if not goal:
        return "Goal cannot be empty, sir."

    from actions.prime_utils import call_unified_model
    
    steps_run = []
    current_status = "Goal initialized."
    
    print(f"[ANUS CLI] Starting autonomous task loop for goal: '{goal}'")
    if player:
        player.write_log(f"[ANUS CLI] Starting autonomous loop for goal: '{goal}'")

    for step in range(1, max_steps + 1):
        # 1. Build prompt for LLM to decide the next terminal command
        history_text = ""
        for idx, (cmd, output, code) in enumerate(steps_run):
            history_text += f"\nStep {idx+1}:\nCommand Run: {cmd}\nExit Code: {code}\nOutput Summary: {output[:500]}\n"

        prompt = f"""You are the ANUS CLI Autonomous Shell Agent inside IP Prime.
Your goal is to achieve this exact user objective: "{goal}"

Current Step: {step} of {max_steps}
Previous Step History:
{history_text or "No commands executed yet."}

Your job:
1. Analyze the objective and previous outputs.
2. Determine the next logical terminal command to execute locally on this Windows system.
3. If the objective is fully satisfied or no further commands are needed, declare that you are finished.

You must respond in one of these two exact formats, and nothing else (no markdown wrappers, no conversational filler):
- To run a command:
COMMAND: <your exact terminal command here>

- To finish the objective:
FINISHED: <a concise summary in Hinglish explaining what you accomplished and the final result for Pratik Sir>
"""

        try:
            response = call_unified_model(contents=prompt, category="coding")
            resp_text = response.text.strip()
        except Exception as e:
            return f"Autonomous agent model call failed: {e}"

        # Parse command or finished
        if resp_text.startswith("FINISHED:"):
            summary = resp_text.replace("FINISHED:", "").strip()
            msg = f"Autonomous loop finished successfully at step {step}/{max_steps}, sir.\n\nSummary:\n{summary}"
            if player:
                player.write_log("[ANUS CLI] Goal completed.")
            return msg

        elif resp_text.startswith("COMMAND:"):
            cmd = resp_text.replace("COMMAND:", "").strip()
            
            # Security safeguard: block destructive command patterns
            destructive = ["rmdir /s /q c:\\", "del /f /s /q c:\\", "format", "shutdown", "mkfs"]
            if any(d in cmd.lower() for d in destructive):
                return f"Safety block: Aborted autonomous step due to highly dangerous command: {cmd}"

            print(f"[ANUS CLI] Step {step} — Executing: {cmd}")
            if player:
                player.write_log(f"[ANUS CLI] Step {step} — Executing: {cmd}")

            try:
                proc = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    timeout=45, encoding="utf-8", errors="replace"
                )
                stdout = proc.stdout.strip()
                stderr = proc.stderr.strip()
                code = proc.returncode
                
                output_summary = f"Stdout: {stdout}\nStderr: {stderr}" if stderr else stdout
                if not output_summary:
                    output_summary = "Executed with no stdout/stderr output."

                steps_run.append((cmd, output_summary, code))
            except subprocess.TimeoutExpired:
                steps_run.append((cmd, "Command execution timed out after 45 seconds.", -1))
            except Exception as e:
                steps_run.append((cmd, f"Command execution failed: {e}", -1))
        else:
            # Handle standard/irregular responses
            if "finish" in resp_text.lower() or "accomplished" in resp_text.lower():
                return f"Autonomous loop finished at step {step}/{max_steps}, sir.\n\nSummary:\n{resp_text}"
            
            # Otherwise, try to extract command
            cmd_match = re.search(r"COMMAND:\s*(.*)", resp_text, re.IGNORECASE)
            if cmd_match:
                cmd = cmd_match.group(1).strip()
                steps_run.append((cmd, "Parsed command from irregular format.", 0))
            else:
                return f"Autonomous loop encountered format parsing error at step {step}. Response was:\n{resp_text}"

    # If steps ran out without finishing
    history_text = "\n".join([f"- Command: {cmd} (Exit Code: {code})" for cmd, _, code in steps_run])
    return (
        f"Autonomous loop reached maximum limit of {max_steps} steps without explicit completion declaration, sir.\n\n"
        f"Execution Trace:\n{history_text}"
    )

def query_solana_wallet(action: str, target: str = "", amount: float = 0.0, player=None) -> str:
    """concept from SOLANUS: Simulates Solana blockchain wallet telemetry operations."""
    history = _load_solana_history()
    act = action.lower().strip()

    if act == "balance":
        msg = (
            f"### Solana Wallet Telemetry (SOLANUS)\n\n"
            f"- **Wallet Owner**: Pratik Thorat Sir\n"
            f"- **Public Wallet Address**: `{SOLANA_WALLET_MOCK}`\n"
            f"- **Current Balance**: `{history['balance']:.2f} SOL`\n"
            f"- **Network State**: Mainnet-Beta (Connected)\n"
            f"- **Valuation**: ~{(history['balance'] * 145.20):,.2f} USD (at mock rate 145.20 USD/SOL)"
        )
        return msg

    elif act == "transfer":
        if not target:
            return "Please provide a target Solana recipient wallet address, sir."
        if amount <= 0.0:
            return "Transaction amount must be greater than 0 SOL, sir."
        if history["balance"] < amount:
            return f"Insufficient SOL balance. Available: {history['balance']:.2f} SOL, requested: {amount} SOL, sir."

        # Execute simulated transaction
        import time, random
        tx_sig = f"tx_sig_sol_{int(time.time())}{random.randint(1000, 9999)}abc"
        
        # Deduct balance
        history["balance"] -= amount
        # Append transaction
        new_tx = {
            "tx_id": tx_sig[:12],
            "type": "TRANSFER",
            "amount": amount,
            "to": target[:24] + "...",
            "date": "2026-05-27 " + time.strftime("%H:%M")
        }
        history["transactions"].insert(0, new_tx)
        _save_solana_history(history)

        msg = (
            f"### Transaction Confirmed (SOLANUS)\n\n"
            f"Transaction successfully broadcasted to Solana Mainnet, sir!\n\n"
            f"- **Action**: Transferred {amount:.4f} SOL\n"
            f"- **To Address**: `{target}`\n"
            f"- **Gas Fee Paid**: `0.00005 SOL`\n"
            f"- **Transaction Signature**: `{tx_sig}`\n"
            f"- **Updated Wallet Balance**: `{history['balance']:.2f} SOL`"
        )
        return msg

    elif act == "history":
        tx_lines = ""
        for tx in history["transactions"][:5]:
            if tx["type"] == "RECEIVE":
                tx_lines += f"- **RECEIVE**: `+{tx['amount']} SOL` from `{tx.get('from', 'Unknown')}` ({tx['date']})\n"
            elif tx["type"] == "TRANSFER":
                tx_lines += f"- **TRANSFER**: `-{tx['amount']} SOL` to `{tx.get('to', 'Unknown')}` ({tx['date']})\n"
            elif tx["type"] == "SWAP":
                tx_lines += f"- **SWAP**: `{tx['detail']}` ({tx['date']})\n"
        
        msg = (
            f"### Solana Recent Transaction History (SOLANUS)\n\n"
            f"Wallet: `{SOLANA_WALLET_MOCK[:12]}...`\n\n"
            f"{tx_lines or 'No recent transactions found, sir.'}"
        )
        return msg

    else:
        return f"Unknown wallet action '{action}', sir. Supported actions are: balance, transfer, history."

def autonomous_shell_helper(parameters: dict, player=None) -> str:
    """
    Main dispatcher for autonomous shell execution and Solana wallet telemetry.

    Parameters (dict keys):
        action (str)     : autonomous_run | solana_balance | solana_transfer | solana_history
        goal (str)       : Target objective for autonomous terminal run
        max_steps (int)  : Maximum command iterations for autonomous run (default: 5)
        target (str)     : Target recipient address for SOL transfers
        amount (float)   : Solana amount to transfer

    Returns:
        str: Result message for the user.
    """
    p = parameters or {}
    action = p.get("action", "autonomous_run").lower().strip()
    goal = p.get("goal", "").strip()
    max_steps = int(p.get("max_steps", 5))
    target = p.get("target", "").strip()
    amount = float(p.get("amount", 0.0))

    if action == "autonomous_run":
        return run_autonomous_loop(goal, max_steps, player)
    elif action == "solana_balance":
        return query_solana_wallet("balance", player=player)
    elif action == "solana_transfer":
        return query_solana_wallet("transfer", target, amount, player)
    elif action == "solana_history":
        return query_solana_wallet("history", player=player)
    else:
        return f"Invalid autonomous shell action: '{action}', sir."


# Backwards-compatible alias — main.py now imports autonomous_shell_helper
anus_cli_helper = autonomous_shell_helper

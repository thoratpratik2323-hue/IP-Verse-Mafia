# actions/browser_agent.py
import asyncio
import os
import sys
import logging
import subprocess
from config import get_api_key

logger = logging.getLogger("saturday.browser_agent")

def browser_agent(parameters: dict, player=None, speak=None) -> str:
    """
    Runs the autonomous browser agent using the browser-use library.
    Parameters:
      - task (str): The prompt detailing what the agent should perform.
    """
    task = (parameters or {}).get("task", "").strip()
    if not task:
        return "Error: No task specified for the browser agent."

    api_key = get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing. Please configure 'gemini_api_key' in api_keys.json."

    # Set environment variable for langchain-google-genai and debug logs
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["BROWSER_USE_LOGGING_LEVEL"] = "debug"
    
    # Configure root logger to show debug outputs
    logging.basicConfig(level=logging.DEBUG)

    # Run the agent in an asyncio loop
    try:
        # On Windows, set the event loop policy to avoid issues with SelectorEventLoop
        if sys.platform == 'win32':
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception as _exc:  # noqa: BLE001
                logging.debug("[%s] Suppressed: %s", __name__, _exc)
        
        result = asyncio.run(_run_agent(task, api_key, player, speak))
        return result
    except Exception as e:
        logger.exception("Failed running browser_agent")
        return f"Browser agent failed with error: {e}"

async def _run_agent(task: str, api_key: str, player, speak) -> str:
    from browser_use.llm.google import ChatGoogle
    from browser_use import Agent

    if player:
        try:
            player.write_log(f"SYS: Initializing browser_agent for task: '{task[:60]}...'")
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)

    # Initialize LLM with Gemini 2.5 Flash using browser-use's native wrapper
    llm = ChatGoogle(model="gemini-2.5-flash", api_key=api_key)

    # Instantiate Agent
    agent = Agent(
        task=task,
        llm=llm,
    )

    try:
        # Run Agent
        history = await agent.run()
        if history.is_done():
            res = history.final_result()
            if not res:
                res = "Task completed successfully, but no final text result was returned by the agent."
            return res
        else:
            return "Task could not be completed successfully by the browser agent."
            
    except Exception as e:
        err_msg = str(e).lower()
        if "playwright" in err_msg or "executable" in err_msg or "chromium" in err_msg or "browser" in err_msg:
            if player:
                try:
                    player.write_log("SYS: Playwright browser binaries not found. Installing Chromium...")
                except Exception as _exc:  # noqa: BLE001
                    logging.debug("[%s] Suppressed: %s", __name__, _exc)
            try:
                # Install playwright chromium browser
                res = subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    capture_output=True, text=True, timeout=180
                )
                if player:
                    try:
                        player.write_log(f"SYS: Playwright install complete. Output: {res.stdout[:100]}")
                    except Exception as _exc:  # noqa: BLE001
                        logging.debug("[%s] Suppressed: %s", __name__, _exc)
                
                # Retry running the agent
                history = await agent.run()
                if history.is_done():
                    res = history.final_result()
                    if not res:
                        res = "Task completed successfully, but no final text result was returned by the agent."
                    return res
                else:
                    return "Task could not be completed successfully by the browser agent after installing Chromium."
            except Exception as install_err:
                logger.exception("Failed to install Playwright dynamically")
                return f"Browser agent failed: {e}. Automatic installation of Playwright Chromium also failed: {install_err}"
        else:
            raise e

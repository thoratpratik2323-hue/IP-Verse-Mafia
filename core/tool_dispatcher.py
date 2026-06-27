import threading
import traceback

# ── Action Imports ────────────────────────────────────────────────────────────
from actions.file_processor import file_processor
from actions.open_app          import open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor  import screen_process
from actions.youtube_video     import youtube_video
from actions.desktop           import desktop_control
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.web_hud           import web_hud
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.design_extractor  import design_extractor as design_extractor_action
from actions.computer_control  import computer_control
from actions.game_updater      import game_updater
from actions.screen_processor  import screen_clicker, screen_explainer, clipboard_action
from actions.dev_agent         import dev_bootstrap, git_assistant, refactor_code, focus_mode
from actions.premium_utilities import (
    meeting_notetaker, browser_news_reader, morning_briefing,
    expense_logger, wifi_file_share, notification_dispatcher,
    drag_drop_converter, spotify_ambient_dj, smart_light_control,
    voice_alarm_suite
)
from actions.warp_helper import warp_helper
from actions.ask_antigravity import ask_antigravity
from actions.image_generator import image_generator
from actions.youtube_macros import automate_youtube, play_youtube
from actions.notepad_automation import automate_notepad
from actions.panic_wipe import panic_wipe as run_panic_wipe
from actions.usb_monitor import toggle_usb as run_usb_toggle
from actions.iot_controller import toggle_iot as run_iot_toggle, get_iot_state as run_get_iot_state
from actions.app_shortcuts import automate_calculator, automate_clock, automate_paint, automate_settings, automate_explorer
from actions.web_app_macros import automate_gmail, automate_drive
from actions.whatsapp_automation import send_whatsapp as run_send_whatsapp
from actions.realtime_knowledge import fetch_realtime_knowledge as run_fetch_realtime_knowledge
from actions.multitasking_control import (
    automate_multitasking as run_automate_multitasking,
    automate_browser as run_automate_browser,
    switch_app as run_switch_app,
    run_system_maintenance,
    toggle_sandbox as run_toggle_sandbox,
)

# Premium Actions Suite 2026
from actions.task_planner import task_planner
from actions.morning_briefer import morning_briefer
from actions.screenshot_code_gen import screenshot_code_gen
from actions.live_code_reviewer import live_code_reviewer
from actions.email_summarizer import email_summarizer
from actions.mobile_telekinesis import mobile_telekinesis
from actions.smart_home import smart_home_enhanced
from actions.autonomous_shell_helper import autonomous_cli_helper
from actions.file_explorer import file_explorer
from actions.hermes_agent import hermes_agent
from actions.code_companion import code_companion
from actions.git_terminal_companion import git_terminal_companion
from actions.project_debug_companion import project_debug_companion
from actions.multimodal_perception import multimodal_perception
from core.autonomy_engine import autonomy_engine as autonomy_engine_action
from actions.autonomous_autopilot import autonomous_autopilot
from actions.advanced_communicator import advanced_communicator
from actions.token_juice import token_juice
from actions.predictive_workspace import predictive_workspace
from actions.llama_factory_helper import llama_factory
from actions.mythos_sentinel import mythos_sentinel
from actions.pentagi_engine import pentagi_engine
from actions.mythos_internet import mythos_internet
from actions.wifi_security import wifi_security
from actions.auto_updater import auto_update

# ── SAT Batch 4 — 39 New Action Imports ─────────────────────────────────────
from actions.deep_research      import deep_research
from actions.document_generator import document_generator
from actions.email_reader       import email_reader
from actions.email_sender       import send_email
from actions.notion_tool        import notion_tool
from actions.google_drive_tool  import google_drive_tool
from actions.huggingface_tool   import huggingface_tool
from actions.security_auditor   import security_audit
from actions.study_mode         import study_mode
from actions.game_mode          import game_mode
from actions.goals_tracker      import goals_tracker
from actions.project_memory     import project_memory
from actions.project_setup      import project_setup
from actions.plugin_creator     import plugin_creator
from actions.error_detective    import error_detective
from actions.explorer_control   import open_folder, navigate_active
from actions.export_conversation import export_conversation
from actions.focus_mode         import focus_mode as sat_focus_mode
from actions.git_copilot        import git_copilot
from actions.github_tool        import github_tool
from actions.github_control     import github_action
from actions.hacker_tools       import hacker_action
from actions.local_ingester     import local_ingester
from actions.local_search       import local_search
from actions.music_control      import music_control
from actions.obsidian_organizer import obsidian_action
from actions.auto_code_explainer import auto_code_explainer
from actions.auto_code_helper   import auto_code_helper
from actions.voice_to_code      import voice_to_code
from actions.content_creator    import content_creator
from actions.browser_agent      import browser_agent
from actions.calendar_tool      import calendar_tool
from actions.scheduled_task     import scheduled_task
from actions.system_monitor     import system_monitor
from actions.translate          import translate_text
from actions.query_visual       import query_visual_timeline
from actions.briefing           import get_morning_briefing
from actions.search             import web_search as quick_web_search


# Also import play_sfx if needed inside threads

async def dispatch_tool(name: str, args: dict, player, speak, loop) -> str:
    result = 'Done.'
    try:
        if name == "open_app":
            r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=player))
            result = r or f"Opened {args.get('app_name')}."

        elif name == "weather_report":
            r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=player))
            result = r or "Weather delivered."

        elif name == "browser_control":
            r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=player))
            result = r or "Done."

        elif name == "file_controller":
            r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=player))
            result = r or "Done."

        elif name == "ask_antigravity":
            r = await loop.run_in_executor(None, lambda: ask_antigravity(parameters=args, player=player))
            result = r or "Done."

        elif name == "send_message":
            r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=player, session_memory=None))
            result = r or f"Message sent to {args.get('receiver')}."

        elif name == "reminder":
            r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=player))
            result = r or "Reminder set."

        elif name == "youtube_video":
            r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=player))
            result = r or "Done."

        elif name == "screen_process":
            threading.Thread(
                target=screen_process,
                kwargs={"parameters": args, "response": None,
                        "player": player, "session_memory": None},
                daemon=True
            ).start()
            result = "Vision module activated. Stay completely silent — vision module will speak directly."

        elif name == "computer_settings":
            r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=player))
            result = r or "Done."

        elif name == "desktop_control":
            r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=player))
            result = r or "Done."

        elif name == "code_helper":
            def run_bg():
                try:
                    player.write_thought("Starting background Code Helper process...")
                    res = code_helper(parameters=args, player=player, speak=speak)
                    player.write_thought("Code Helper task complete!")
                    player.write_log(f"SYS: Code Helper Finished: {res}")
                    speak("Sir, the background code helper task is complete.")
                except Exception as e:
                    player.write_log(f"SYS ERROR: Code Helper failed: {e}")
                    speak(f"Sir, the background code helper task failed: {e}")
            
            threading.Thread(target=run_bg, daemon=True).start()
            result = "Sir, I have started the Code Helper in the background. You can continue speaking or performing other tasks!"

        elif name == "dev_agent":
            def run_bg():
                try:
                    player.write_thought("Starting background Developer Agent...")
                    res = dev_agent(parameters=args, player=player, speak=speak)
                    player.write_thought("Developer Agent task complete!")
                    player.write_log(f"SYS: Developer Agent Finished: {res}")
                    speak("Sir, the background developer agent task is complete.")
                except Exception as e:
                    player.write_log(f"SYS ERROR: Developer Agent failed: {e}")
                    speak(f"Sir, the background developer agent task failed: {e}")
            
            threading.Thread(target=run_bg, daemon=True).start()
            result = "Sir, the Developer Agent has been successfully launched in a secure background thread. I will notify you the moment it finishes!"

        elif name == "agent_task":
            from agent.task_queue import get_queue, TaskPriority
            priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
            priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
            task_id  = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=speak)
            result   = f"Task started (ID: {task_id})."

        elif name == "web_search":
            r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=player))
            result = r or "Done."

        elif name == "design_extractor":
            r = await loop.run_in_executor(None, lambda: design_extractor_action(parameters=args, player=player))
            result = r or "Done."
        elif name == "file_processor":
            if not args.get("file_path") and player.current_file:
                args["file_path"] = player.current_file
            r = await loop.run_in_executor(
                None,
                lambda: file_processor(parameters=args, player=player, speak=speak)
            )
            result = r or "Done."

        elif name == "image_generator":
            r = await loop.run_in_executor(None, lambda: image_generator(parameters=args, player=player))
            result = r or "Done."

        elif name == "computer_control":
            r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=player))
            result = r or "Done."

        elif name == "youtube_macros":
            action = args.get("action", "").lower().strip()
            if action == "play_video":
                r = await loop.run_in_executor(None, lambda: play_youtube(query=args.get("query", "")))
            else:
                r = await loop.run_in_executor(None, lambda: automate_youtube(action=action))
            result = r or "Done."

        elif name == "notepad_automation":
            action = args.get("action", "").lower().strip()
            text = args.get("text", "")
            r = await loop.run_in_executor(None, lambda: automate_notepad(action=action, arg=text))
            result = r or "Done."

        elif name == "panic_wipe":
            r = await loop.run_in_executor(None, lambda: run_panic_wipe())
            result = r.get("reply", "Done.")

        elif name == "usb_monitor":
            enabled = bool(args.get("enabled", False))
            r = await loop.run_in_executor(None, lambda: run_usb_toggle(enabled=enabled))
            result = f"USB monitor lockdown is now {'active' if r.get('active') else 'inactive'}."

        elif name == "iot_controller":
            action = args.get("action", "").lower().strip()
            if action == "toggle":
                r = await loop.run_in_executor(None, lambda: run_iot_toggle(device=args.get("device", "")))
                result = r.get("reply", "Done.")
            else:
                r = await loop.run_in_executor(None, lambda: run_get_iot_state())
                result = str(r)

        elif name == "app_shortcuts":
            app = args.get("app", "").lower().strip()
            action = args.get("action", "").lower().strip()
            path_arg = args.get("path_arg", "")
            
            if app == "calc":
                r = await loop.run_in_executor(None, lambda: automate_calculator(action=action))
            elif app == "clock":
                r = await loop.run_in_executor(None, lambda: automate_clock(action=action))
            elif app == "paint":
                r = await loop.run_in_executor(None, lambda: automate_paint(action=action))
            elif app == "settings":
                r = await loop.run_in_executor(None, lambda: automate_settings(action=action))
            elif app == "explorer":
                r = await loop.run_in_executor(None, lambda: automate_explorer(action=action, arg=path_arg))
            else:
                r = f"Unknown app shortcut target: '{app}'"
            result = r or "Done."

        elif name == "web_app_macros":
            service = args.get("service", "").lower().strip()
            action = args.get("action", "").lower().strip()
            
            if service == "gmail":
                r = await loop.run_in_executor(None, lambda: automate_gmail(action=action))
            elif service == "drive":
                r = await loop.run_in_executor(None, lambda: automate_drive(action=action))
            else:
                r = f"Unknown web app service macro: '{service}'"
            result = r or "Done."

        elif name == "whatsapp_automation":
            target = args.get("target", "")
            message = args.get("message", "")
            r = await loop.run_in_executor(None, lambda: run_send_whatsapp(target=target, message=message))
            result = r or "Done."

        elif name == "realtime_knowledge":
            query = args.get("query", "")
            r = await loop.run_in_executor(None, lambda: run_fetch_realtime_knowledge(query=query))
            result = r or "Done."

        elif name == "game_updater":
            r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=player, speak=speak))
            result = r or "Done."

        elif name == "orchestrated_coder":
            from actions.agent_orchestrator import run_orchestrated_coder
            proj = args.get("project_path", "")
            inst = args.get("instruction", "")
            def run_bg():
                try:
                    player.write_thought("Starting background Orchestrated Coder...")
                    res = run_orchestrated_coder(project_path_str=proj, instruction=inst, player=player)
                    player.write_thought("Orchestrated Coder task complete!")
                    player.write_log(f"SYS: Orchestrated Coder Finished: {res}")
                    speak("Sir, the background orchestrated coding task is complete.")
                except Exception as e:
                    player.write_log(f"SYS ERROR: Orchestrated Coder failed: {e}")
                    speak(f"Sir, the background orchestrated coding task failed: {e}")
            
            threading.Thread(target=run_bg, daemon=True).start()
            result = "Sir, I have launched the Orchestrated Coder in a secure background thread. I will notify you the moment it finishes. You can continue speaking or performing other tasks!"

        elif name == "ip_army":
            from actions.ip_army import run_ip_army
            proj = args.get("project_path", "")
            inst = args.get("instruction", "")
            def run_bg():
                try:
                    player.write_thought("Mobilizing the IP AI Army specialized division...")
                    res = run_ip_army(project_path_str=proj, instruction=inst, player=player)
                    player.write_thought("IP AI Army orchestration task complete!")
                    player.write_log(f"SYS: IP Army Finished:\n{res}")
                    speak("Sir, the IP AI Army has completed its tasks successfully.")
                except Exception as e:
                    player.write_log(f"SYS ERROR: IP Army failed: {e}")
                    speak(f"Sir, the IP AI Army task has failed: {e}")
            
            threading.Thread(target=run_bg, daemon=True).start()
            result = "Sir, I have deployed the IP AI Army of specialized agents in the background. They are working on your request right now!"


        # --- Vision Suite ---
        elif name == "screen_clicker":
            r = await loop.run_in_executor(None, lambda: screen_clicker(
                element_description=args.get("element_description", "")
            ))
            result = r or "Done."

        elif name == "screen_explainer":
            r = await loop.run_in_executor(None, lambda: screen_explainer(
                description=args.get("description", "")
            ))
            result = r or "Done."

        elif name == "clipboard_action":
            r = await loop.run_in_executor(None, lambda: clipboard_action(
                action_type=args.get("action_type", "summarize")
            ))
            result = r or "Done."

        # --- Dev Suite ---
        elif name == "dev_bootstrap":
            r = await loop.run_in_executor(None, lambda: dev_bootstrap(
                project_path=args.get("project_path", "")
            ))
            result = r or "Done."

        elif name == "git_assistant":
            def run_bg():
                try:
                    player.write_thought("Starting background Git Assistant...")
                    res = git_assistant(
                        action_type=args.get("action_type", "commit"),
                        project_path=args.get("project_path", ""),
                        player=player
                    )
                    player.write_thought("Git Assistant complete!")
                    player.write_log(f"SYS: Git Assistant Finished: {res}")
                    speak("Sir, the background git assistant task is complete.")
                except Exception as e:
                    player.write_log(f"SYS ERROR: Git Assistant failed: {e}")
                    speak(f"Sir, the background git assistant task failed: {e}")
            
            threading.Thread(target=run_bg, daemon=True).start()
            result = "Sir, I have started the Git Assistant task in the background. You can continue speaking or performing other tasks!"

        elif name == "refactor_code":
            def run_bg():
                try:
                    player.write_thought("Starting background Refactor Code process...")
                    res = refactor_code(
                        file_path=args.get("file_path", ""),
                        action=args.get("action", "refactor"),
                        player=player
                    )
                    player.write_thought("Refactor Code task complete!")
                    player.write_log(f"SYS: Refactor Code Finished: {res}")
                    speak("Sir, the background refactoring task is complete.")
                except Exception as e:
                    player.write_log(f"SYS ERROR: Refactor Code failed: {e}")
                    speak(f"Sir, the background refactoring task failed: {e}")
            
            threading.Thread(target=run_bg, daemon=True).start()
            result = "Sir, I have started the Refactoring task in the background. You can continue speaking or performing other tasks!"

        elif name == "focus_mode":
            r = await loop.run_in_executor(None, lambda: focus_mode(
                duration_minutes=int(args.get("duration_minutes", 25))
            ))
            result = r or "Done."

        # --- Premium Utilities Suite ---
        elif name == "meeting_notetaker":
            r = await loop.run_in_executor(None, lambda: meeting_notetaker(
                action=args.get("action", "start"),
                duration_seconds=int(args.get("duration_seconds", 15))
            ))
            result = r or "Done."

        elif name == "browser_news_reader":
            r = await loop.run_in_executor(None, lambda: browser_news_reader(
                query=args.get("query", "technology")
            ))
            result = r or "Done."

        elif name == "morning_briefing":
            r = await loop.run_in_executor(None, morning_briefing)
            result = r or "Done."

        elif name == "expense_logger":
            r = await loop.run_in_executor(None, lambda: expense_logger(
                action=args.get("action", "log"),
                description=args.get("description", ""),
                amount=float(args.get("amount", 0.0)),
                category=args.get("category", "Other")
            ))
            result = r or "Done."

        elif name == "wifi_file_share":
            r = await loop.run_in_executor(None, lambda: wifi_file_share(
                file_path=args.get("file_path", ""),
                action=args.get("action", "start")
            ))
            result = r or "Done."

        elif name == "notification_dispatcher":
            r = await loop.run_in_executor(None, lambda: notification_dispatcher(
                action=args.get("action", "summary"),
                app=args.get("app", ""),
                message=args.get("message", "")
            ))
            result = r or "Done."

        elif name == "drag_drop_converter":
            r = await loop.run_in_executor(None, lambda: drag_drop_converter(
                file_path=args.get("file_path", ""),
                target_format=args.get("target_format", "")
            ))
            result = r or "Done."

        elif name == "spotify_ambient_dj":
            r = await loop.run_in_executor(None, lambda: spotify_ambient_dj(
                command=args.get("command", "play"),
                playlist=args.get("playlist", "lofi")
            ))
            result = r or "Done."

        elif name == "smart_light_control":
            r = await loop.run_in_executor(None, lambda: smart_light_control(
                state=args.get("state", "on"),
                brightness=int(args.get("brightness", 80)),
                color=args.get("color", "cyan")
            ))
            result = r or "Done."

        elif name == "voice_alarm_suite":
            r = await loop.run_in_executor(None, lambda: voice_alarm_suite(
                action=args.get("action", "create"),
                time_str=args.get("time_str", ""),
                message=args.get("message", "Time to wake up!"),
                alarm_id=args.get("alarm_id", "")
            ))
            result = r or "Done."

        elif name == "semantic_search":
            from actions.semantic_store import semantic_search
            r = await loop.run_in_executor(None, lambda: semantic_search(
                query=args.get("query", "")
            ))
            result = r or "Done."

        elif name == "index_workspace":
            from actions.semantic_store import index_directory
            r = await loop.run_in_executor(None, lambda: index_directory(
                dir_path_str=args.get("path", "")
            ))
            result = r or "Done."

        elif name == "compact_memory":
            from actions.semantic_store import compact_memory
            r = await loop.run_in_executor(None, lambda: compact_memory())
            result = r or "Done."

        elif name == "claude_code":
            from actions.claude_code_helper import claude_code_helper
            r = await loop.run_in_executor(None, lambda: claude_code_helper(
                parameters=args,
                player=player,
                speak=speak
            ))
            result = r or "Done."

        elif name == "coding_workflow":
            from actions.coding_workflow import run_coding_workflow
            r = await loop.run_in_executor(None, lambda: run_coding_workflow(
                parameters=args,
                player=player,
                speak=speak
            ))
            result = r or "Done."

        elif name == "auto_organize_notes":
            from actions.obsidian_helper import auto_organize_notes
            r = await loop.run_in_executor(None, lambda: auto_organize_notes(player=player))
            result = r or "Done."

        elif name == "generate_vault_digest":
            from actions.obsidian_helper import generate_vault_digest
            r = await loop.run_in_executor(None, lambda: generate_vault_digest(
                digest_type=args.get("digest_type", "daily"),
                player=player
            ))
            result = r or "Done."

        elif name == "media_control":
            from actions.media_controller import execute_media_control
            r = await loop.run_in_executor(None, lambda: execute_media_control(
                action=args.get("action", "")
            ))
            result = r or "Done."

        elif name == "github_assistant":
            from actions.github_assistant import execute_git_automation
            r = await loop.run_in_executor(None, lambda: execute_git_automation(
                action=args.get("action", ""),
                repo_path=args.get("repo_path"),
                commit_message=args.get("commit_message"),
                title=args.get("title"),
                body=args.get("body")
            ))
            result = r or "Done."

        elif name == "schedule_manager":
            from actions.calendar_helper import execute_schedule_manager
            r = await loop.run_in_executor(None, lambda: execute_schedule_manager(
                action=args.get("action", ""),
                title=args.get("title"),
                date=args.get("date"),
                time=args.get("time"),
                event_id=args.get("event_id")
            ))
            result = r or "Done."

        elif name == "n8n_automation":
            from actions.n8n_dispatcher import trigger_n8n_webhook
            payload = args.get("payload") or args.get("data")
            r = await loop.run_in_executor(None, lambda: trigger_n8n_webhook(
                webhook_name=args.get("webhook_name", ""),
                payload=payload
            ))
            result = r or "Done."

        # --- Obsidian Vault Local RAG ---
        elif name == "index_obsidian_vault":
            from actions.obsidian_helper import index_obsidian_vault
            r = await loop.run_in_executor(None, index_obsidian_vault)
            result = r or "Done."

        elif name == "search_obsidian_notes":
            from actions.obsidian_helper import search_obsidian_notes
            r = await loop.run_in_executor(None, lambda: search_obsidian_notes(
                query=args.get("query", ""),
                limit=int(args.get("limit", 5))
            ))
            result = r or "Done."

        elif name == "obsidian_rag_query":
            from actions.obsidian_helper import obsidian_rag_query
            r = await loop.run_in_executor(None, lambda: obsidian_rag_query(
                query=args.get("query", ""),
                player=player
            ))
            result = r or "Done."

        # --- Screen Multimodal Vision & OCR ---
        elif name == "capture_and_analyze_screen":
            from actions.screen_vision import capture_and_analyze_screen
            r = await loop.run_in_executor(None, lambda: capture_and_analyze_screen(
                prompt=args.get("prompt", "Explain what is currently on my screen.")
            ))
            result = r or "Done."

        # --- Spotify Web API Integration ---
        elif name == "search_spotify_track":
            from actions.spotify_helper import search_spotify_track
            r = await loop.run_in_executor(None, lambda: search_spotify_track(
                query=args.get("query", "")
            ))
            result = r or "Done."

        # --- Smart Home Integration ---
        elif name == "execute_smart_home_command":
            from actions.smart_home import execute_smart_home_command
            r = await loop.run_in_executor(None, lambda: execute_smart_home_command(
                action=args.get("action", "turn_on"),
                device_name=args.get("device_name", ""),
                domain=args.get("domain", "light")
            ))
            result = r or "Done."

        # --- Granular WASAPI Audio Mixer ---
        elif name == "list_active_audio_sessions":
            from actions.audio_mixer import list_active_audio_sessions
            r = await loop.run_in_executor(None, list_active_audio_sessions)
            result = r or "Done."

        elif name == "set_application_volume":
            from actions.audio_mixer import set_application_volume
            r = await loop.run_in_executor(None, lambda: set_application_volume(
                app_name=args.get("app_name", ""),
                volume_level=int(args.get("volume_level", 100))
            ))
            result = r or "Done."

        elif name == "mute_application":
            from actions.audio_mixer import mute_application
            r = await loop.run_in_executor(None, lambda: mute_application(
                app_name=args.get("app_name", ""),
                mute_state=bool(args.get("mute_state", False))
            ))
            result = r or "Done."

        elif name == "run_aider_coding_task":
            from actions.aider_helper import run_aider_coding_task
            r = await loop.run_in_executor(None, lambda: run_aider_coding_task(
                instruction=args.get("instruction", ""),
                file_paths=args.get("file_paths"),
                project_path=args.get("project_path")
            ))
            result = r or "Done."

        elif name == "get_awesome_repo_info":
            from actions.awesome_repos_helper import get_awesome_repo_info
            r = await loop.run_in_executor(None, lambda: get_awesome_repo_info(
                query=args.get("query")
            ))
            result = r or "Done."

        elif name == "clone_awesome_repo":
            from actions.awesome_repos_helper import clone_awesome_repo
            r = await loop.run_in_executor(None, lambda: clone_awesome_repo(
                repo_name=args.get("repo_name"),
                dest_dir=args.get("dest_dir")
            ))
            result = r or "Done."


        elif name == "web_hud":
            r = await loop.run_in_executor(None, lambda: web_hud(parameters=args, player=player))
            result = r or "Done."

        elif name == "warp_helper":
            r = await loop.run_in_executor(None, lambda: warp_helper(parameters=args, player=player))
            result = r or "Done."

        elif name == "prime_local_first":
            from actions.prime_features import prime_local_first
            r = await loop.run_in_executor(None, lambda: prime_local_first(args, player))
            result = r or "Done."

        elif name == "prime_infinite_memory":
            from actions.prime_features import prime_infinite_memory
            r = await loop.run_in_executor(None, lambda: prime_infinite_memory(args, player))
            result = r or "Done."

        elif name == "brain_search":
            from memory.brain import brain_search
            r = await loop.run_in_executor(None, lambda: brain_search(
                query=args.get("query", ""),
                limit=int(args.get("limit", 10))
            ))
            result = r or "No results."

        elif name == "brain_stats":
            from memory.brain import format_brain_stats
            r = await loop.run_in_executor(None, format_brain_stats)
            result = r or "Done."

        elif name == "brain_store_fact":
            from memory.brain import store_fact
            await loop.run_in_executor(None, lambda: store_fact(
                subject=args.get("subject", ""),
                predicate=args.get("predicate", ""),
                obj=args.get("object", ""),
                source="tool_call"
            ))
            result = f"Fact stored: {args.get('subject')} → {args.get('predicate')} → {args.get('object')}"

        elif name == "brain_store_event":
            from memory.brain import store_timeline_event
            await loop.run_in_executor(None, lambda: store_timeline_event(
                event_date=args.get("event_date", ""),
                summary=args.get("summary", ""),
                event_type=args.get("event_type", "general"),
                importance=int(args.get("importance", 5))
            ))
            result = f"Event recorded: [{args.get('event_date')}] {args.get('summary')}"

        elif name == "prime_energy_dashboard":
            from actions.prime_features import prime_energy_dashboard
            r = await loop.run_in_executor(None, lambda: prime_energy_dashboard(args, player))
            result = r or "Done."

        elif name == "prime_messaging":
            from actions.prime_features import prime_messaging
            r = await loop.run_in_executor(None, lambda: prime_messaging(args, player))
            result = r or "Done."

        elif name == "prime_homelab":
            from actions.prime_features import prime_homelab
            r = await loop.run_in_executor(None, lambda: prime_homelab(args, player))
            result = r or "Done."

        elif name == "prime_media":
            from actions.prime_features import prime_media
            r = await loop.run_in_executor(None, lambda: prime_media(args, player))
            result = r or "Done."

        elif name == "prime_writing":
            from actions.prime_features import prime_writing_tool
            r = await loop.run_in_executor(None, lambda: prime_writing_tool(args, player))
            result = r or "Done."

        elif name == "prime_gesture_control":
            from actions.prime_features import prime_gesture_control
            r = await loop.run_in_executor(None, lambda: prime_gesture_control(args, player))
            result = r or "Done."

        elif name == "prime_dashboard":
            from actions.prime_features import prime_dashboard
            r = await loop.run_in_executor(None, lambda: prime_dashboard(args, player))
            result = r or "Done."

        elif name == "prime_audit":
            from actions.prime_auditor import prime_audit
            r = await loop.run_in_executor(None, lambda: prime_audit(parameters=args, player=player))
            result = r or "Done."

        elif name == "prime_watcher":
            from actions.prime_watcher import prime_watcher
            r = await loop.run_in_executor(None, lambda: prime_watcher(parameters=args, player=player))
            result = r or "Done."

        # ── Premium Feature Suite ─────────────────────────────────────────
        elif name == "pulse_highlight":
            x        = int(args.get("x", 0))
            y        = int(args.get("y", 0))
            color    = args.get("color", "cyan")
            duration = float(args.get("duration_ms", 2500)) / 1000.0
            player.pulse_highlight(x, y, duration, color)
            result = f"Highlighting screen at ({x}, {y}) for {duration}s using color {color}."


        elif name == "in_place_translate":
            target_lang = args.get("target_lang", "Hindi")
            
            # Run OCR translation in a background thread to prevent UI lockup
            def run_translation():
                from actions.screen_overlay import run_ocr_translation_in_background
                run_ocr_translation_in_background(
                    target_lang=target_lang,
                    callback_signal=player._win._ocr_translate_sig
                )
            
            threading.Thread(target=run_translation, daemon=True).start()
            result = f"OCR & translation background process started for target language: {target_lang}."


        elif name == "terminal_doctor":
            from actions.terminal_doctor import diagnose_and_heal_command
            command    = args.get("command", "")
            cwd        = args.get("cwd", None)
            max_rounds = int(args.get("max_rounds", 3))
            r = await loop.run_in_executor(
                None,
                lambda: diagnose_and_heal_command(command, cwd=cwd, max_rounds=max_rounds, ui=player)
            )
            result = r or "Terminal Doctor complete."

        elif name == "ghost_scribe_tutorial":
            from actions.terminal_doctor import ghost_scribe_tutorial
            topic       = args.get("topic", "Tutorial")
            commands    = args.get("commands", [])
            output_path = args.get("output_path", None)
            r = await loop.run_in_executor(
                None,
                lambda: ghost_scribe_tutorial(topic, commands=commands, output_path=output_path, ui=player)
            )
            result = r or "Tutorial generated."

        elif name == "task_planner":
            r = await loop.run_in_executor(None, lambda: task_planner(parameters=args, player=player))
            result = r or "Done."

        elif name == "morning_briefer":
            r = await loop.run_in_executor(None, lambda: morning_briefer(parameters=args, player=player))
            result = r or "Done."

        elif name == "screenshot_code_gen":
            r = await loop.run_in_executor(None, lambda: screenshot_code_gen(parameters=args, player=player))
            result = r or "Done."

        elif name == "live_code_reviewer":
            r = await loop.run_in_executor(None, lambda: live_code_reviewer(parameters=args, player=player))
            result = r or "Done."


        elif name == "spotify_dj_mode":
            from actions.spotify_helper import spotify_dj_mode
            r = await loop.run_in_executor(None, lambda: spotify_dj_mode(mood=args.get("mood", "auto"), player=player))
            result = r or "Done."

        elif name == "mobile_telekinesis":
            r = await loop.run_in_executor(None, lambda: mobile_telekinesis(parameters=args, player=player))
            result = r or "Done."

        elif name == "smart_home_scene":
            r = await loop.run_in_executor(None, lambda: smart_home_enhanced(parameters=args, player=player))
            result = r or "Done."

        elif name == "email_summarizer":
            r = await loop.run_in_executor(None, lambda: email_summarizer(parameters=args, player=player))
            result = r or "Done."

        elif name == "autonomous_cli_helper":
            r = await loop.run_in_executor(None, lambda: autonomous_cli_helper(parameters=args, player=player))
            result = r or "Done."

        elif name == "whatsapp_auto_reply":
            from actions.whatsapp_listener import enable_whatsapp_auto_reply, disable_whatsapp_auto_reply, set_auto_reply_message, get_auto_reply_status
            act = args.get("action", "status").lower().strip()
            msg = args.get("message", "")
            if act == "enable":
                r = await loop.run_in_executor(None, lambda: enable_whatsapp_auto_reply(message=msg, player=player))
            elif act == "disable":
                r = await loop.run_in_executor(None, lambda: disable_whatsapp_auto_reply(player=player))
            elif act == "set_message":
                r = await loop.run_in_executor(None, lambda: set_auto_reply_message(message=msg, player=player))
            else:
                r = await loop.run_in_executor(None, lambda: get_auto_reply_status(player=player))
            result = r or "Done."


        elif name == "file_explorer":
            r = await loop.run_in_executor(None, lambda: file_explorer(parameters=args, player=player))
            result = r or "Done."

        elif name == "hermes_agent":
            r = await loop.run_in_executor(None, lambda: hermes_agent(parameters=args, player=player))
            result = r or "Done."

        elif name == "code_companion":
            r = await loop.run_in_executor(None, lambda: code_companion(parameters=args, player=player))
            result = r or "Done."

        elif name == "git_terminal_companion":
            r = await loop.run_in_executor(None, lambda: git_terminal_companion(parameters=args, player=player))
            result = r or "Done."

        elif name == "project_debug_companion":
            r = await loop.run_in_executor(None, lambda: project_debug_companion(parameters=args, player=player))
            result = r or "Done."

        elif name == "multimodal_perception":
            r = await loop.run_in_executor(None, lambda: multimodal_perception(parameters=args, player=player))
            result = r or "Done."

        elif name == "autonomous_autopilot":
            r = await loop.run_in_executor(None, lambda: autonomous_autopilot(parameters=args, player=player))
            result = r or "Done."

        elif name == "advanced_communicator":
            r = await loop.run_in_executor(None, lambda: advanced_communicator(parameters=args, player=player))
            result = r or "Done."

        elif name == "token_juice":
            r = await loop.run_in_executor(None, lambda: token_juice(parameters=args, player=player))
            result = r or "Done."

        elif name == "predictive_workspace":
            r = await loop.run_in_executor(None, lambda: predictive_workspace(parameters=args, player=player))
            result = r or "Done."

        elif name == "llama_factory":
            r = await loop.run_in_executor(None, lambda: llama_factory(parameters=args, player=player))
            result = r or "Done."

        elif name == "mythos_sentinel":
            r = await loop.run_in_executor(None, lambda: mythos_sentinel(parameters=args, player=player))
            result = r or "Done."

        elif name == "pentagi_engine":
            def run_pentagi_bg():
                try:
                    player.write_log("[PentAGI] Real hacking engine activated.")
                    res = pentagi_engine(parameters=args, player=player)
                    player.write_log("[PentAGI] Scan complete.")
                    speak("Sir, the PentAGI scan is complete. Results are in the terminal.")
                    return res
                except Exception as e:
                    player.write_log(f"[PentAGI] Error: {e}")
                    return f"PentAGI error: {e}"
            import threading as _t
            _t.Thread(target=run_pentagi_bg, daemon=True).start()
            result = "Sir, PentAGI real hacking engine is running in the background. Results will appear shortly."


        elif name == "mythos_internet":
            def run_inet_bg():
                try:
                    player.write_log("[MythosInternet] Live internet query started.")
                    res = mythos_internet(parameters=args, player=player)
                    player.write_log("[MythosInternet] Query complete.")
                    if player:
                        player.write_thought(res)
                    speak("Sir, internet query complete. Results are ready.")
                    return res
                except Exception as e:
                    player.write_log(f"[MythosInternet] Error: {e}")
                    speak(f"Sir, internet query failed: {e}")
                    return f"Error: {e}"
            import threading as _t
            _t.Thread(target=run_inet_bg, daemon=True).start()
            result = "Sir, I am searching the live internet for you. Results will appear in a moment."


        elif name == "wifi_security":
            r = await loop.run_in_executor(None, lambda: wifi_security(parameters=args, player=player))
            result = r or "Done."

        elif name == "local_llm":
            from actions.local_llm import local_llm
            r = await loop.run_in_executor(None, lambda: local_llm(parameters=args, player=player))
            result = r or "Done."

        elif name == "model_switcher":
            from actions.model_switcher import model_switcher
            r = await loop.run_in_executor(None, lambda: model_switcher(parameters=args, player=player))
            result = r or "Done."

        elif name in ["force_nvidia", "force_gemini", "auto_route", "set_coding_model"]:
            from actions.model_switcher import model_switcher
            args_copy = dict(args)
            args_copy["action"] = name
            r = await loop.run_in_executor(None, lambda: model_switcher(parameters=args_copy, player=player))
            result = r or "Done."

        elif name == "habit_tracker":
            from actions.habit_tracker import habit_tracker
            r = await loop.run_in_executor(None, lambda: habit_tracker(parameters=args, player=player))
            result = r or "Done."


        elif name == "email_ai":
            from actions.email_ai import email_ai
            r = await loop.run_in_executor(None, lambda: email_ai(parameters=args, player=player))
            result = r or "Done."

        elif name == "discord_helper":
            from actions.discord_helper import discord_helper
            r = await loop.run_in_executor(None, lambda: discord_helper(parameters=args, player=player))
            result = r or "Done."

        elif name == "telegram_bot":
            from actions.telegram_bot import telegram_bot
            r = await loop.run_in_executor(None, lambda: telegram_bot(parameters=args, player=player))
            result = r or "Done."

        elif name == "live_translator":
            from actions.live_translator import live_translator
            r = await loop.run_in_executor(None, lambda: live_translator(parameters=args, player=player))
            result = r or "Done."

        elif name == "docker_controller":
            from actions.docker_controller import docker_controller
            r = await loop.run_in_executor(None, lambda: docker_controller(parameters=args, player=player))
            result = r or "Done."

        elif name == "clipboard_manager":
            from actions.clipboard_manager import clipboard_manager
            r = await loop.run_in_executor(None, lambda: clipboard_manager(parameters=args, player=player))
            result = r or "Done."

        elif name == "pr_reviewer":
            from actions.pr_reviewer import pr_reviewer
            r = await loop.run_in_executor(None, lambda: pr_reviewer(parameters=args, player=player))
            result = r or "Done."

        elif name == "venv_manager":
            from actions.venv_manager import venv_manager
            r = await loop.run_in_executor(None, lambda: venv_manager(parameters=args, player=player))
            result = r or "Done."

        elif name == "presentation_generator":
            from actions.presentation_generator import presentation_generator
            r = await loop.run_in_executor(None, lambda: presentation_generator(parameters=args, player=player))
            result = r or "Done."

        elif name == "health_monitor":
            from actions.health_monitor import health_monitor
            r = await loop.run_in_executor(None, lambda: health_monitor(parameters=args, player=player))
            result = r or "Done."

        elif name == "journal":
            from actions.journal import journal
            r = await loop.run_in_executor(None, lambda: journal(parameters=args, player=player))
            result = r or "Done."

        elif name == "screen_time":
            from actions.screen_time import screen_time
            r = await loop.run_in_executor(None, lambda: screen_time(parameters=args, player=player))
            result = r or "Done."

        elif name == "health_tracker":
            from actions.health_tracker import health_tracker
            r = await loop.run_in_executor(None, lambda: health_tracker(parameters=args, player=player))
            result = r or "Done."

        elif name == "finance_tracker":
            from actions.finance_tracker import finance_tracker
            r = await loop.run_in_executor(None, lambda: finance_tracker(parameters=args, player=player))
            result = r or "Done."


        elif name == "network_monitor":
            from actions.network_monitor import network_monitor
            r = await loop.run_in_executor(None, lambda: network_monitor(parameters=args, player=player))
            result = r or "Done."


        elif name == "wifi_speed_logger":
            from actions.wifi_speed_logger import wifi_speed_logger
            r = await loop.run_in_executor(None, lambda: wifi_speed_logger(parameters=args, player=player))
            result = r or "Done."

        elif name == "second_monitor_overlay":
            from actions.second_monitor_overlay import second_monitor_overlay
            r = await loop.run_in_executor(None, lambda: second_monitor_overlay(parameters=args, player=player))
            result = r or "Done."



        elif name == "enable_hacker_mode":
            from actions.model_switcher import model_switcher
            args_copy = dict(args)
            args_copy["action"] = "enable_hacker"
            r = await loop.run_in_executor(None, lambda: model_switcher(parameters=args_copy, player=player))
            result = r or "Done."

        elif name == "disable_hacker_mode":
            from actions.model_switcher import model_switcher
            args_copy = dict(args)
            args_copy["action"] = "disable_hacker"
            r = await loop.run_in_executor(None, lambda: model_switcher(parameters=args_copy, player=player))
            result = r or "Done."


        elif name == "password_toolkit":
            from actions.password_tools import password_tools
            r = await loop.run_in_executor(None, lambda: password_tools(parameters=args, player=player))
            result = r or "Done."

        elif name == "encryption_toolkit":
            from actions.encryption_tools import encryption_tools
            r = await loop.run_in_executor(None, lambda: encryption_tools(parameters=args, player=player))
            result = r or "Done."

        elif name == "shutdown_ip_ray":

            player.write_log("SYS: Shutdown requested.")
            speak("Goodbye, sir.")
            def _shutdown():
                import time
                import os
                time.sleep(1)
                os._exit(0)
            threading.Thread(target=_shutdown, daemon=True).start()

        elif name == "auto_update":
            force = args.get("force", False)
            r = await loop.run_in_executor(None, lambda: auto_update(force=force))
            result = r or "Update check complete."

        elif name == "send_daily_report":
            from actions.email_ai import send_daily_digest_email
            summary = args.get("summary", "")
            ok = await loop.run_in_executor(None, lambda: send_daily_digest_email(summary))
            result = "✅ Daily report email sent to your Gmail!" if ok else "❌ Email send failed. Check gmail_app_password in config/api_keys.json"

        elif name == "cmd_control":
            from actions.cmd_control import cmd_control
            r = await loop.run_in_executor(None, lambda: cmd_control(parameters=args, player=player))
            result = r or "Done."

        # ── Batch 3: Multitasking, Browser Shortcuts, App Switcher, Maintenance, Sandbox ──

        elif name == "automate_multitasking":
            action = args.get("action", "")
            r = await loop.run_in_executor(None, lambda: run_automate_multitasking(action))
            result = r or "Multitasking command executed, Sir."

        elif name == "automate_browser":
            browser = args.get("browser", "chrome")
            action = args.get("action", "")
            r = await loop.run_in_executor(None, lambda: run_automate_browser(browser, action))
            result = r or "Browser shortcut executed, Sir."

        elif name == "switch_app":
            app_name = args.get("name", "")
            r = await loop.run_in_executor(None, lambda: run_switch_app(app_name))
            result = r or "Application switched, Sir."

        elif name == "run_system_maintenance":
            r = await loop.run_in_executor(None, run_system_maintenance)
            result = r or "System maintenance complete, Sir."

        elif name == "toggle_sandbox":
            enabled = args.get("enabled", False)
            r = await loop.run_in_executor(None, lambda: run_toggle_sandbox(bool(enabled)))
            result = r or "Network sandbox toggled, Sir."

        # ── SAT Batch 4 — 39 New Tool Dispatchers ────────────────────────────

        elif name == "deep_research":
            query = args.get("query", "")
            depth = args.get("depth", "standard")
            r = await loop.run_in_executor(None, lambda: deep_research(query=query, depth=depth, player=player, speak=speak))
            result = r or "Research complete, Sir."

        elif name == "document_generator":
            r = await loop.run_in_executor(None, lambda: document_generator(parameters=args, player=player, speak=speak))
            result = r or "Document generated, Sir."

        elif name == "email_reader":
            r = await loop.run_in_executor(None, lambda: email_reader(parameters=args, player=player, speak=speak))
            result = r or "Emails retrieved, Sir."

        elif name == "email_sender":
            r = await loop.run_in_executor(None, lambda: send_email(
                to=args.get("to", ""),
                subject=args.get("subject", ""),
                body=args.get("body", ""),
                player=player
            ))
            result = r or "Email sent, Sir."

        elif name == "notion_tool":
            r = await loop.run_in_executor(None, lambda: notion_tool(parameters=args, player=player, speak=speak))
            result = r or "Notion action complete, Sir."

        elif name == "google_drive_tool":
            r = await loop.run_in_executor(None, lambda: google_drive_tool(parameters=args, player=player, speak=speak))
            result = r or "Google Drive action complete, Sir."

        elif name == "huggingface_tool":
            r = await loop.run_in_executor(None, lambda: huggingface_tool(parameters=args, player=player, speak=speak))
            result = r or "HuggingFace action complete, Sir."

        elif name == "security_auditor":
            r = await loop.run_in_executor(None, lambda: security_audit(parameters=args, player=player, speak=speak))
            result = r or "Security audit complete, Sir."

        elif name == "study_mode":
            r = await loop.run_in_executor(None, lambda: study_mode(parameters=args, player=player, speak=speak))
            result = r or "Study mode action complete, Sir."

        elif name == "game_mode":
            action = args.get("action", "status")
            r = await loop.run_in_executor(None, lambda: game_mode(action=action, player=player, speak=speak))
            result = r or "Game mode toggled, Sir."

        elif name == "goals_tracker":
            r = await loop.run_in_executor(None, lambda: goals_tracker(parameters=args, player=player, speak=speak))
            result = r or "Goals updated, Sir."

        elif name == "project_memory":
            r = await loop.run_in_executor(None, lambda: project_memory(parameters=args, player=player, speak=speak))
            result = r or "Project memory updated, Sir."

        elif name == "project_setup":
            r = await loop.run_in_executor(None, lambda: project_setup(parameters=args, player=player, speak=speak))
            result = r or "Project setup complete, Sir."

        elif name == "plugin_creator":
            r = await loop.run_in_executor(None, lambda: plugin_creator(parameters=args, player=player, speak=speak))
            result = r or "Plugin created and registered, Sir."

        elif name == "error_detective":
            error = args.get("error", "")
            context = args.get("context", "")
            r = await loop.run_in_executor(None, lambda: error_detective(error=error, context=context, player=player, speak=speak))
            result = r or "Error analysis complete, Sir."

        elif name == "explorer_control":
            action = args.get("action", "open")
            path = args.get("path", "")
            if action == "open":
                r = await loop.run_in_executor(None, lambda: open_folder(path))
            else:
                r = await loop.run_in_executor(None, lambda: navigate_active(path))
            result = r or "Explorer action complete, Sir."

        elif name == "export_conversation":
            fmt = args.get("format", "txt")
            filename = args.get("filename", "")
            r = await loop.run_in_executor(None, lambda: export_conversation(format=fmt, filename=filename, player=player, speak=speak))
            result = r or "Conversation exported, Sir."

        elif name == "focus_mode":
            r = await loop.run_in_executor(None, lambda: sat_focus_mode(parameters=args, player=player, speak=speak))
            result = r or "Focus mode toggled, Sir."

        elif name == "git_copilot":
            r = await loop.run_in_executor(None, lambda: git_copilot(parameters=args, player=player, speak=speak))
            result = r or "Git action complete, Sir."

        elif name == "github_tool":
            r = await loop.run_in_executor(None, lambda: github_tool(parameters=args, player=player, speak=speak))
            result = r or "GitHub action complete, Sir."

        elif name == "github_action":
            r = await loop.run_in_executor(None, lambda: github_action(parameters=args, player=player, speak=speak))
            result = r or "GitHub action triggered, Sir."

        elif name == "hacker_tools":
            r = await loop.run_in_executor(None, lambda: hacker_action(parameters=args, player=player, speak=speak))
            result = r or "Hacker tool action complete, Sir."

        elif name == "local_ingester":
            path = args.get("path", "")
            collection = args.get("collection", "prime_kb")
            r = await loop.run_in_executor(None, lambda: local_ingester(path=path, collection=collection, player=player, speak=speak))
            result = r or "Files ingested into memory, Sir."

        elif name == "local_search":
            query = args.get("query", "")
            collection = args.get("collection", "prime_kb")
            top_k = args.get("top_k", 5)
            r = await loop.run_in_executor(None, lambda: local_search(query=query, collection=collection, top_k=top_k, player=player, speak=speak))
            result = r or "Local search complete, Sir."

        elif name == "music_control":
            action = args.get("action", "play")
            r = await loop.run_in_executor(None, lambda: music_control(action=action, player=player))
            result = r or "Music controlled, Sir."

        elif name == "obsidian_organizer":
            r = await loop.run_in_executor(None, lambda: obsidian_action(parameters=args, player=player, speak=speak))
            result = r or "Obsidian vault organized, Sir."

        elif name == "auto_code_explainer":
            detail = args.get("detail", "detailed")
            r = await loop.run_in_executor(None, lambda: auto_code_explainer(detail=detail, player=player, speak=speak))
            result = r or "Code explained, Sir."

        elif name == "auto_code_helper":
            r = await loop.run_in_executor(None, lambda: auto_code_helper(parameters=args, player=player, speak=speak))
            result = r or "Code assistance complete, Sir."

        elif name == "voice_to_code":
            code = args.get("code", "")
            r = await loop.run_in_executor(None, lambda: voice_to_code(code=code, player=player))
            result = r or "Code typed into editor, Sir."

        elif name == "content_creator":
            r = await loop.run_in_executor(None, lambda: content_creator(parameters=args, player=player, speak=speak))
            result = r or "Content created, Sir."

        elif name == "browser_agent":
            r = await loop.run_in_executor(None, lambda: browser_agent(parameters=args, player=player, speak=speak))
            result = r or "Browser task complete, Sir."

        elif name == "calendar_tool":
            r = await loop.run_in_executor(None, lambda: calendar_tool(parameters=args, player=player, speak=speak))
            result = r or "Calendar action complete, Sir."

        elif name == "scheduled_task":
            r = await loop.run_in_executor(None, lambda: scheduled_task(parameters=args, player=player, speak=speak))
            result = r or "Task scheduled, Sir."

        elif name == "system_monitor":
            metric = args.get("metric", "all")
            r = await loop.run_in_executor(None, lambda: system_monitor(metric=metric, player=player))
            result = r or "System stats retrieved, Sir."

        elif name == "translate_text":
            text = args.get("text", "")
            target = args.get("target_language", "English")
            source = args.get("source_language", "auto")
            r = await loop.run_in_executor(None, lambda: translate_text(text=text, target_language=target, source_language=source, player=player))
            result = r or "Translation complete, Sir."

        elif name == "query_visual_timeline":
            query = args.get("query", "")
            time_ago = args.get("time_ago", "1 hour")
            r = await loop.run_in_executor(None, lambda: query_visual_timeline(query=query, time_ago=time_ago, player=player, speak=speak))
            result = r or "Visual timeline queried, Sir."

        elif name == "quick_briefing":
            btype = args.get("type", "quick")
            r = await loop.run_in_executor(None, lambda: get_morning_briefing(briefing_type=btype, player=player, speak=speak))
            result = r or "Briefing delivered, Sir."

        elif name == "web_search_quick":
            query = args.get("query", "")
            r = await loop.run_in_executor(None, lambda: quick_web_search(query=query, player=player))
            result = r or "Search complete, Sir."

        elif name == "autonomy_engine":
            r = await loop.run_in_executor(None, lambda: autonomy_engine_action(parameters=args, player=player))
            result = r or "Done, sir."

        else:
            result = f"Unknown tool: {name}"

    except Exception as e:
        result = f"Tool '{name}' failed: {e}"
        traceback.print_exc()
        speak(f"Sir, tool execution failed: {e}")
        
    return result

import asyncio
import threading
import traceback
import sys

# ── Action Imports ────────────────────────────────────────────────────────────
from actions.file_processor import file_processor
from actions.flight_finder     import flight_finder
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
from actions import ghost_coder
from actions import smart_drop_zone
from actions.ask_antigravity import ask_antigravity

# Premium Actions Suite 2026
from actions.task_planner import task_planner
from actions.morning_briefer import morning_briefer
from actions.screenshot_code_gen import screenshot_code_gen
from actions.live_code_reviewer import live_code_reviewer
from actions.webcam_mood import webcam_mood
from actions.email_summarizer import email_summarizer
from actions.mobile_telekinesis import mobile_telekinesis
from actions.smart_home import smart_home_enhanced
from actions.autonomous_shell_helper import autonomous_cli_helper
from actions.soap2soap_helper import soap2soap_remaker
from actions.file_explorer import file_explorer
from actions.hermes_agent import hermes_agent
from actions.code_companion import code_companion
from actions.git_terminal_companion import git_terminal_companion
from actions.project_debug_companion import project_debug_companion
from actions.multimodal_perception import multimodal_perception
from actions.autonomous_autopilot import autonomous_autopilot
from actions.advanced_communicator import advanced_communicator
from actions.token_juice import token_juice
from actions.predictive_workspace import predictive_workspace
from actions.llama_factory_helper import llama_factory
from actions.mythos_sentinel import mythos_sentinel
from actions.pentagi_engine import pentagi_engine
from actions.antidrone_defense import antidrone_defense
from actions.mythos_internet import mythos_internet
from actions.dos_toolkit import dos_toolkit


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

        elif name == "computer_control":
            r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=player))
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

        elif name == "flight_finder":
            r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=player))
            result = r or "Done."

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
                player=self.player
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

        elif name == "pascal_3d_designer":
            from actions.pascal_3d_designer import pascal_3d_designer
            r = await loop.run_in_executor(None, lambda: pascal_3d_designer(
                goal=args.get("goal"),
                player=player
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

        elif name == "webcam_mood":
            r = await loop.run_in_executor(None, lambda: webcam_mood(parameters=args, player=player))
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

        elif name == "soap2soap_remaker":
            r = await loop.run_in_executor(None, lambda: soap2soap_remaker(parameters=args, player=player))
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


        elif name == "antidrone_defense":
            act = args.get("action", "scan").lower()
            if act == "monitor":
                def run_drone_monitor():
                    try:
                        player.write_log("[AntiDrone] Continuous monitoring started.")
                        res = antidrone_defense(parameters=args, player=player)
                        player.write_log(f"[AntiDrone] {res[:80]}")
                        speak("Sir, anti-drone monitoring is now active. I will alert you if any drone is detected.")
                    except Exception as e:
                        player.write_log(f"[AntiDrone] Error: {e}")
                        speak(f"Sir, anti-drone monitor error: {e}")
                import threading as _t
                _t.Thread(target=run_drone_monitor, daemon=True).start()
                result = "Sir, anti-drone monitoring system is now active in background. You will receive an alert if any drone WiFi is detected."
            else:
                r = await loop.run_in_executor(None, lambda: antidrone_defense(parameters=args, player=player))
                result = r or "Done."

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

        elif name == "dos_toolkit":
            r = await loop.run_in_executor(None, lambda: dos_toolkit(parameters=args, player=player))
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

        elif name == "emotion_detector":
            from actions.emotion_detector import emotion_detector
            r = await loop.run_in_executor(None, lambda: emotion_detector(parameters=args, player=player))
            result = r or "Done."

        elif name == "tutor_mode":
            from actions.tutor_mode import tutor_mode
            r = await loop.run_in_executor(None, lambda: tutor_mode(parameters=args, player=player))
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

        elif name == "order_tracker":
            from actions.order_tracker import order_tracker
            r = await loop.run_in_executor(None, lambda: order_tracker(parameters=args, player=player))
            result = r or "Done."

        elif name == "bill_splitter":
            from actions.bill_splitter import bill_splitter
            r = await loop.run_in_executor(None, lambda: bill_splitter(parameters=args, player=player))
            result = r or "Done."

        elif name == "network_monitor":
            from actions.network_monitor import network_monitor
            r = await loop.run_in_executor(None, lambda: network_monitor(parameters=args, player=player))
            result = r or "Done."

        elif name == "face_recognition":
            from actions.face_recognition import face_recognition
            r = await loop.run_in_executor(None, lambda: face_recognition(parameters=args, player=player))
            result = r or "Done."

        elif name == "wifi_speed_logger":
            from actions.wifi_speed_logger import wifi_speed_logger
            r = await loop.run_in_executor(None, lambda: wifi_speed_logger(parameters=args, player=player))
            result = r or "Done."

        elif name == "second_monitor_overlay":
            from actions.second_monitor_overlay import second_monitor_overlay
            r = await loop.run_in_executor(None, lambda: second_monitor_overlay(parameters=args, player=player))
            result = r or "Done."

        elif name == "deepfake_detector":
            from actions.deepfake_detector import deepfake_detector
            r = await loop.run_in_executor(None, lambda: deepfake_detector(parameters=args, player=player))
            result = r or "Done."

        elif name == "printer_3d_controller":
            from actions.printer_3d_controller import printer_3d_controller
            r = await loop.run_in_executor(None, lambda: printer_3d_controller(parameters=args, player=player))
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

        elif name == "cyber_tutor":
            from actions.cyber_tutor import cyber_tutor
            r = await loop.run_in_executor(None, lambda: cyber_tutor(parameters=args, player=player))
            result = r or "Done."

        elif name == "ctf_helper":
            from actions.ctf_helper import ctf_helper
            r = await loop.run_in_executor(None, lambda: ctf_helper(parameters=args, player=player))
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
                import time, os
                time.sleep(1)
                os._exit(0)
            threading.Thread(target=_shutdown, daemon=True).start()

        else:
            result = f"Unknown tool: {name}"

    except Exception as e:
        result = f"Tool '{name}' failed: {e}"
        traceback.print_exc()
        speak(f"Sir, tool execution failed: {e}")
        
    return result

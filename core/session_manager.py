import logging
import asyncio
import queue
import threading
import json
import sys
import time
import traceback
from pathlib import Path
import sounddevice as sd
import numpy as np
from google import genai
from google.genai import types

# Global helpers
def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR         = get_base_dir()
API_CONFIG_PATH  = BASE_DIR / "config" / "api_keys.json"
SETTINGS_PATH    = BASE_DIR / "config" / "settings.json"
PROMPT_PATH      = BASE_DIR / "core" / "prompt.txt"

CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024

MAX_RETRY_ATTEMPTS  = 5
AUDIO_QUEUE_MAXSIZE = 150

class SessionIdleTimeout(Exception):
    pass

def _load_volume_multiplier() -> float:
    try:
        if not SETTINGS_PATH.exists():
            return 2.0
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        val = float(data.get("volume_multiplier", 2.0))
        return max(0.5, min(val, 4.0))
    except Exception as e:
        print(f"[WARN] Failed to load volume: {e}")
        return 2.0

def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]

# System prompt caching
_CACHED_PROMPT = None

def clear_prompt_cache():
    global _CACHED_PROMPT
    _CACHED_PROMPT = None
    print("[SATURDAY] 🧠 Prompt cache cleared.")

def _load_system_prompt() -> str:
    global _CACHED_PROMPT
    if _CACHED_PROMPT is not None:
        return _CACHED_PROMPT

    try:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[WARN] Failed to read PROMPT_PATH: {e}")
        prompt = (
            "You are SATURDAY, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )
    try:
        import ui
        ui_inst = ui.get_ui()
        if ui_inst and ui_inst.hacker_mode:
            prompt += (
                "\n\n[HACKER MODE ACTIVE]\n"
                "You are now acting as a cybersecurity expert and hacking tutor. "
                "Incorporate technical security terms, explain cryptographic or networking concepts when asked, "
                "and guide the user through security best practices. Maintain a slightly mysterious, sharp, "
                "and elite hacker persona (still Hinglish, but prefixing responses with hacker tutor style comments)."
            )
    except Exception as e:
        print(f"[WARN] Failed to parse hacker mode: {e}")
    try:
        notes_path = BASE_DIR / "memory" / "sticky_notes.txt"
        if notes_path.exists():
            content = notes_path.read_text(encoding="utf-8").strip()
            if content:
                prompt += f"\n\n[USER STICKY NOTES]\nHere are your current active notes/reminders. Reference or modify them if the user asks:\n{content}"
    except Exception as e:
        print(f"[WARN] Failed to read sticky notes: {e}")

    _CACHED_PROMPT = prompt
    return prompt

# Memory batching & debounce
_pending_memory_turns = []
_memory_turn_lock = threading.Lock()
_memory_lock = threading.Lock() # legacy backward compatibility lock
_last_memory_turn_time = 0.0

def _process_memory_turns(turns_to_process: list) -> None:
    if not turns_to_process:
        return
    try:
        combined_text = "\n".join([f"User: {t['user']}\nSaturday: {t['saturday']}" for t in turns_to_process])
        from memory.semantic import add_semantic_memory
        add_semantic_memory(combined_text)

        from memory.memory_manager import should_extract_memory, extract_memory, update_memory
        api_key = _get_api_key()

        max_retries = 3
        backoff = 2.0
        for attempt in range(max_retries):
            try:
                if should_extract_memory(combined_text, "", api_key):
                    data = extract_memory(combined_text, "", api_key)
                    if data:
                        update_memory(data)
                        print(f"[Memory] ✅ Batched update: {list(data.keys())}")
                break
            except Exception as e:
                if "429" in str(e):
                    print(f"[Memory] ⚠️ Rate limited (attempt {attempt+1}/{max_retries}). Retrying in {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    print(f"[Memory] ⚠️ API Error: {e}")
                    break
    except Exception as e:
        print(f"[Memory] ⚠️ Batch update failed: {e}")

def _update_memory_async(user_text: str, saturday_text: str) -> None:
    global _pending_memory_turns, _last_memory_turn_time

    user_text     = (user_text     or "").strip()
    saturday_text = (saturday_text or "").strip()

    if len(user_text) < 5:
        return

    with _memory_turn_lock:
        _pending_memory_turns.append({"user": user_text, "saturday": saturday_text})
        _last_memory_turn_time = time.time()
        if len(_pending_memory_turns) < 5:
            return
        turns_to_process = list(_pending_memory_turns)
        _pending_memory_turns.clear()

    _process_memory_turns(turns_to_process)

def flush_pending_memories() -> None:
    global _pending_memory_turns
    with _memory_turn_lock:
        if not _pending_memory_turns:
            return
        turns_to_process = list(_pending_memory_turns)
        _pending_memory_turns.clear()

    _process_memory_turns(turns_to_process)


class SaturdayLive:

    def __init__(self, ui):
        global _saturday_instance
        _saturday_instance = self
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = queue.Queue(maxsize=AUDIO_QUEUE_MAXSIZE)
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self._server_turn_active = False
        self._playing_chunk      = False
        self._welcomed           = False
        self._tool_executing     = False
        self._last_speak_time    = 0.0
        self._speaking_start_time = 0.0
        self.quiet_mode          = False
        self._last_user_activity = time.time()
        self.ui.on_text_command = self._on_text_command
        self._current_emotion    = "neutral"
        self._last_user_language = "English"
        self._ignore_server_response = False
        self._audio_out_stream   = None
        
        # Start play audio in a dedicated thread to prevent asyncio lag
        threading.Thread(target=self._play_audio, daemon=True, name="SaturdayPlayThread").start()

        # Proactive Watcher Initialization
        try:
            from agent.watcher import ProactiveWatcher
            self.watcher = ProactiveWatcher(speak_func=self.speak)
        except Exception as e:
            print(f"[WARN] Watcher failed to init: {e}")
            
        # Start Life Engine background thoughts
        try:
            from core.life_engine import life_engine
            life_engine.start(self)
        except Exception as e:
            print(f"[WARN] Failed to start Life Engine: {e}")
            
        # Start Autonomy Core planning loop
        try:
            from core.autonomy_engine import autonomy_core
            autonomy_core.start(
                session_mgr=self,
                interval=90,
                idle_required=True,
                idle_threshold=300,
                autonomy_level="supervised",
            )
            print("[IP PRIME] Autonomy core successfully started.")
        except Exception as e:
            print(f"[WARN] Failed to start Autonomy Core: {e}")
            self.watcher.add_reminder("Bhai, meeting start hone wali hai!", "09:00")
            self.watcher.start()
            self.ui.write_log("SYS: Proactive reminder watcher started.")
        except Exception as e:
            print(f"[SATURDAY] Watcher start failed: {e}")

    def _has_wake_word(self, text: str) -> bool:
        if not text:
            return False
        txt_lower = text.lower()
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
            ww_str = settings.get("wake_words", "sat, saturday, buddy, dost")
        except Exception:
            ww_str = "sat, saturday, buddy, dost"
            
        wake_words = [w.strip().lower() for w in ww_str.split(",") if w.strip()]
        if not wake_words:
            wake_words = ["sat", "saturday", "buddy", "dost"]
        return any(word in txt_lower for word in wake_words)

    def _intercept_user_command(self, text: str) -> str:
        """
        Intercepts and processes user text commands with translation, RAG context,
        GitHub triggers, web search triggers, and emotion detection.
        """
        if not text or not text.strip():
            return text

        # 1. Real-time Translation
        try:
            from actions.translate import translate_text, detect_language
            user_lang = detect_language(text)
            self._last_user_language = user_lang
            translated = translate_text(text, target_lang="English")
            self.ui.write_log(f"Detected Lang: {user_lang} | Translated: {translated}")
        except Exception as e:
            print(f"Translation failed: {e}")

        # 2. RAG Knowledge Search
        try:
            from memory.knowledge import search_knowledge
            rag_context = search_knowledge(text)
            if rag_context:
                text = f"Additional Knowledge Context:\n{rag_context}\n\nUser query: {text}"
                self.ui.write_log("SYS: RAG Context injected.")
        except Exception as e:
            print(f"RAG context query failed: {e}")

        # 3. GitHub Action Trigger
        if "github" in text.lower() or "issue" in text.lower() or "commit" in text.lower():
            try:
                from actions.github_control import github_action
                git_res = github_action(text)
                self.ui.write_log(f"GitHub: {git_res}")
                self.speak(git_res)
                return ""
            except Exception as e:
                print(f"GitHub action execution failed: {e}")

        # 4. Live Web Search Trigger
        if "search" in text.lower() or "find" in text.lower():
            try:
                from actions.search import web_search
                results = web_search(text)
                text = f"Search results:\n{results}\n\nUser asked: {text}\nAnswer based on results."
                self.ui.write_log("SYS: Web search results injected.")
            except Exception as e:
                print(f"Web search failed: {e}")

        # 5. Emotion Detection (Non-blocking)
        def detect_and_set():
            try:
                from core.emotion import detect_emotion
                self._current_emotion = detect_emotion(text)
            except Exception as e:
                print(f"[WARN] Emotion detection failed: {e}")
        threading.Thread(target=detect_and_set, daemon=True).start()

        return text

    def _on_text_command(self, text: str):
        """Triggered when the user submits a text command through the console."""
        if not text.strip():
            return
            
        self._last_user_activity = time.time()
        
        # Prompt Moderation Check
        from core.moderation import moderate_prompt
        blocked_reason = moderate_prompt(text)
        if blocked_reason:
            refusal = "I cannot assist with that request as it violates safety guidelines, sir."
            self.ui.set_last_response(refusal)
            self.ui.write_log(f"SYS: BLOCKED (Moderation): {blocked_reason}")
            self.speak(refusal)
            return

        if self._ww_enabled and not self._has_wake_word(text):
            self.ui.write_log(f"User: {text} [Ignored - No wake word]")
            return
        intercepted_text = self._intercept_user_command(text)
        if not intercepted_text:
            return

        from core.offline_fallback import is_internet_available, query_ollama
        if not is_internet_available() or not self.session:
            self.ui.set_state("THINKING")
            self.ui.set_activity("OLLAMA THINKING")
            self.ui.write_log(f"User (Offline): {intercepted_text}")
            
            def run_offline():
                sys_prompt = _load_system_prompt()
                resp = query_ollama(intercepted_text, sys_prompt)
                
                # Adapt response for emotion if detected
                try:
                    from core.emotion import adapt_response_for_emotion
                    emotion = getattr(self, "_current_emotion", "neutral")
                    resp = adapt_response_for_emotion(emotion, resp)
                    self._current_emotion = "neutral"
                except Exception as e:
                    print(f"[WARN] Failed to adapt response for emotion: {e}")

                self.ui.set_last_response(resp)
                self.ui.write_log(f"Saturday (Offline): {resp}")
                self.speak(resp)
                self.ui.set_state("LISTENING")
                self.ui.set_activity("SYSTEM IDLE (OFFLINE)")
                
            threading.Thread(target=run_offline, daemon=True).start()
            return

        if not self._loop or not self.session:
            return

        def run_in_loop():
            self._server_turn_active = True
            self.update_speaking_state()

        self._loop.call_soon_threadsafe(run_in_loop)

        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": intercepted_text}]},
                turn_complete=True
            ),
            self._loop
        )

    async def _run_offline_loop(self):
        from core.offline_fallback import is_internet_available, is_ollama_available, get_first_available_ollama_model
        from core.local_stt import listen_and_transcribe_local
        
        self.ui.write_log("SYS: Saturday is now running offline.")
        self.ui.set_state("LISTENING")
        self.ui.set_activity("SYSTEM IDLE (OFFLINE)")
        
        # Check if Ollama is available
        if is_ollama_available():
            model = get_first_available_ollama_model()
            self.ui.write_log(f"SYS: Local Ollama detected (Active Model: {model}).")
        else:
            self.ui.write_log("SYS: WARNING: Local Ollama is not running.")
            
        old_cb = self.ui.on_text_command
        
        def offline_text_cb(text: str):
            self._on_text_command(text)
            
        self.ui.on_text_command = offline_text_cb
        
        try:
            while not is_internet_available():
                settings = self.ui._load_settings()
                if settings.get("local_stt_enabled", True):
                    text = await asyncio.to_thread(listen_and_transcribe_local)
                    if text:
                        if text.startswith("ERROR_"):
                            if not text.startswith("ERROR_TIMEOUT"):
                                self.ui.write_log(f"STT: {text}")
                        else:
                            self.ui.write_log(f"User (Voice/Offline): {text}")
                            self._on_text_command(text)
                else:
                    await asyncio.sleep(2.0)
        except Exception as e:
            print(f"[Offline Loop] Exception: {e}")
        finally:
            self.ui.on_text_command = old_cb
            self.ui.write_log("SYS: Internet detected. Reconnecting online...")

    def toggle_hacker_mode(self, enabled: bool):
        if self.session and self._loop:
            async def force_reconnect():
                print("[SATURDAY] 💀 Hacker Mode toggled. Forcing reconnect...")
                self.ui.write_log("SYS: Reloading session with Hacker Persona...")
                await self.session.close()
            asyncio.run_coroutine_threadsafe(force_reconnect(), self._loop)

    def change_voice_persona(self, voice_name: str) -> str:
        valid_voices = ["Charon", "Fenrir", "Puck", "Aoede", "Kore"]
        normalized = voice_name.capitalize().strip()
        if normalized not in valid_voices:
            return f"Invalid voice name '{voice_name}'. Supported: {', '.join(valid_voices)}"
            
        self.ui._save_settings({"voice_name": normalized})
        
        if self.session and self._loop:
            async def force_reconnect():
                print(f"[SATURDAY] Voice changed to {normalized}. Forcing reconnect...")
                self.ui.write_log(f"SYS: Voice changed to {normalized}. Reconnecting...")
                await self.session.close()
            asyncio.run_coroutine_threadsafe(force_reconnect(), self._loop)
            
        return f"Switched voice persona to {normalized}."

    def change_system_mood(self, mood: str) -> str:
        valid_moods = ["focus", "relax", "energized", "normal"]
        normalized = mood.lower().strip()
        if normalized not in valid_moods:
            return f"Invalid mood '{mood}'. Supported: {', '.join(valid_moods)}"
            
        self.ui._save_settings({"mood": normalized})
        
        if self.ui and self.ui._win:
            if hasattr(self.ui._win, "hud") and self.ui._win.hud:
                self.ui._win.hud.set_mood(normalized)
            if hasattr(self.ui._win, "_refresh_theme_styles"):
                self.ui._win._refresh_theme_styles()
                
        if self.session and self._loop:
            async def force_reconnect():
                print(f"[SATURDAY] System mood changed to {normalized}. Forcing reconnect...")
                self.ui.write_log(f"SYS: Mood changed to {normalized}. Reconnecting...")
                await self.session.close()
            asyncio.run_coroutine_threadsafe(force_reconnect(), self._loop)
            
        return f"System mood changed to {normalized}."

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            if value and not self._is_speaking:
                self._speaking_start_time = time.time()
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            if getattr(self, "_tool_executing", False):
                self.ui.set_state("PROCESSING")
            else:
                self.ui.set_state("LISTENING")

    def update_speaking_state(self):
        is_speaking = self._playing_chunk
        self.set_speaking(is_speaking)

    def speak(self, text: str):
        # Translate response back to the user's language if not English/Hinglish
        target_lang = getattr(self, "_last_user_language", "English")
        if target_lang != "English":
            try:
                from actions.translate import translate_text
                text = translate_text(text, target_lang=target_lang)
            except Exception as e:
                print(f"[WARN] Failed to translate back to {target_lang}: {e}")

        self.ui.set_last_response(text)

        if not self._loop or not self.session:
            import threading
            threading.Thread(target=self._speak_offline, args=(text,), daemon=True).start()
            return

        def run_in_loop():
            self._server_turn_active = True
            self.update_speaking_state()

        self._loop.call_soon_threadsafe(run_in_loop)

        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def _speak_offline(self, text: str):
        try:
            import comtypes.client
            comtypes.CoInitialize()
            voice = comtypes.client.CreateObject("SAPI.SpVoice")
            self.ui.set_state("SPEAKING")
            voice.Speak(text)
        except Exception as e:
            print(f"[Offline Speak] Error: {e}")
        finally:
            self.ui.set_state("LISTENING")
            try:
                comtypes.CoUninitialize()
            except Exception as _exc:  # noqa: BLE001
                logging.debug("[%s] Suppressed: %s", __name__, _exc)

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime
        from memory.memory_manager import load_memory, format_memory_for_prompt
        from core.tool_dispatcher import TOOL_DECLARATIONS

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        mood = "normal"
        try:
            settings = self.ui._load_settings()
            mood = settings.get("mood", "normal").lower().strip()
        except Exception as e:
            print(f"[WARN] Failed to load mood settings: {e}")

        mood_ctx = f"[ACTIVE SYSTEM MOOD: {mood.upper()}]\n"
        if mood == "focus":
            mood_ctx += "Tone/Vibe: Be extremely concise, direct, and encourage Pratik to stay focused. Minimize talk and do exactly what is asked.\n\n"
        elif mood == "relax":
            mood_ctx += "Tone/Vibe: Be very calm, warm, and soothing. Speak slightly slower and more comfortably.\n\n"
        elif mood == "energized":
            mood_ctx += "Tone/Vibe: Be highly energetic, enthusiastic, and motivating. Keep the energy and excitement high!\n\n"
        else:
            mood_ctx += "Tone/Vibe: Normal helpful, warm, friendly Hinglish assistant tone.\n\n"

        parts = [time_ctx, mood_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        active_declarations = list(TOOL_DECLARATIONS)
        custom_tools_path = BASE_DIR / "config" / "custom_tools.json"
        if custom_tools_path.exists():
            try:
                import json
                custom_tools = json.loads(custom_tools_path.read_text(encoding="utf-8"))
                for tool_schema in custom_tools.values():
                    if not any(t["name"] == tool_schema["name"] for t in active_declarations):
                        active_declarations.append(tool_schema)
            except Exception as e:
                print(f"[WARN] Failed to load custom tools: {e}")

        voice_name = "Charon"
        try:
            settings = self.ui._load_settings()
            voice_name = settings.get("voice_name", "Charon")
        except Exception as e:
            print(f"[WARN] Failed to load voice config: {e}")

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": active_declarations}],
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        from core.tool_dispatcher import execute_tool_dispatch
        return await execute_tool_dispatch(self, fc)

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        print("[SATURDAY] 🎤 Mic started")
        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            if self.ui.muted:
                return
            now = time.time()
            with self._speaking_lock:
                saturday_speaking = self._is_speaking
                last_speak = getattr(self, "_last_speak_time", 0.0)
            if saturday_speaking or (now - last_speak < 1.0):
                return
            data = indata.tobytes()

            try:
                # Calculate root-mean-square (RMS) of input audio data, casting to float32 to prevent overflow
                rms = np.sqrt(np.mean(indata.astype(np.float32)**2))
                # Normalize typical voice peak to 0.0-1.0
                volume = min(1.0, rms / 4500.0)
                self.ui.set_audio_level(volume)
            except Exception as _exc:  # noqa: BLE001
                logging.debug("[%s] Suppressed: %s", __name__, _exc)
            
            def safe_put():
                if self.out_queue.full():
                    try:
                        self.out_queue.get_nowait()
                    except Exception as _exc:  # noqa: BLE001
                        logging.debug("[%s] Suppressed: %s", __name__, _exc)
                try:
                    self.out_queue.put_nowait({"data": data, "mime_type": "audio/pcm"})
                except asyncio.QueueFull:
                    pass

            loop.call_soon_threadsafe(safe_put)

        while True:
            try:
                try:
                    stream = sd.InputStream(
                        samplerate=SEND_SAMPLE_RATE,
                        channels=CHANNELS,
                        dtype="int16",
                        blocksize=CHUNK_SIZE,
                        latency="low",
                        callback=callback,
                    )
                except Exception:
                    device_info = sd.query_devices(kind='input')
                    default_rate = int(device_info.get('default_samplerate', 16000))
                    print(f"[SATURDAY] 🎤 16000Hz failed. Trying default device rate: {default_rate}Hz")
                    stream = sd.InputStream(
                        samplerate=default_rate,
                        channels=CHANNELS,
                        dtype="int16",
                        blocksize=CHUNK_SIZE,
                        latency="low",
                        callback=callback,
                    )
                with stream:
                    print("[SATURDAY] 🎤 Mic stream open")
                    self.ui.write_log("SYS: Microphone stream opened successfully.")
                    while True:
                        await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[SATURDAY] ❌ Mic stream open failed: {e}")
                self.ui.write_log("SYS: Microphone error. Retrying in 5s...")
                await asyncio.sleep(5)

    async def _receive_audio(self):
        print("[SATURDAY] 👂 Recv started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        if getattr(self, "quiet_mode", False) or getattr(self, "_ignore_server_response", False):
                            continue
                        self._server_turn_active = True
                        # Ring-buffer: drop oldest chunk if queue is at capacity
                        if self.audio_in_queue.full():
                            current_max = self.audio_in_queue.maxsize
                            new_max = current_max + 50
                            print(f"[SATURDAY] ⚠️ Audio queue full ({current_max} chunks). Dropping oldest chunk and scaling queue maxsize to {new_max}...")
                            self.audio_in_queue.maxsize = new_max
                            try:
                                self.audio_in_queue.get_nowait()
                            except Exception as _exc:  # noqa: BLE001
                                logging.debug("[%s] Suppressed: %s", __name__, _exc)
                        self.audio_in_queue.put_nowait(response.data)
                        self.update_speaking_state()

                    if response.server_content:
                        sc = response.server_content

                        # Handle user interruption immediately (clearing queue to stop audio playback immediately)
                        if getattr(sc, "interrupted", False):
                            print("[SATURDAY] 🛑 Server turn interrupted! Clearing audio queue...")
                            while not self.audio_in_queue.empty():
                                try:
                                    self.audio_in_queue.get_nowait()
                                except Exception:
                                    break
                            self._playing_chunk = False
                            self._server_turn_active = False
                            self.update_speaking_state()

                        if sc.output_transcription and sc.output_transcription.text:
                            self._last_user_activity = time.time()
                            self._server_turn_active = True
                            self.update_speaking_state()
                            txt = sc.output_transcription.text.strip()
                            if txt:
                                out_buf.append(txt)
                                current_out = " ".join(out_buf).strip()
                                try:
                                    from core.emotion import adapt_response_for_emotion
                                    emotion = getattr(self, "_current_emotion", "neutral")
                                    current_out = adapt_response_for_emotion(emotion, current_out)
                                except Exception as _exc:  # noqa: BLE001
                                    logging.debug("[%s] Suppressed: %s", __name__, _exc)
                                self.ui.set_last_response(current_out)

                        if sc.input_transcription and sc.input_transcription.text:
                            self._ignore_server_response = False
                            self._last_user_activity = time.time()
                            txt = sc.input_transcription.text.strip()
                            if txt:
                                if not in_buf:
                                    self.ui.set_last_response("")
                                in_buf.append(txt)
                                
                                # Quiet mode toggle detection
                                txt_lower = txt.lower()

                                # Clipboard AI Voice Triggers
                                clip_triggers = ["explain this", "clipboard explain", "kya hai yeh", "what is this", "explain clipboard"]
                                if any(trigger in txt_lower for trigger in clip_triggers):
                                    self.ui.write_log("SYS: Clipboard AI triggered via voice.")
                                    self._loop.call_soon_threadsafe(lambda: getattr(self.ui._win, "_toggle_clipboard_ai", lambda: None)())

                                sleep_cmds = ["shant ho jao", "shant ho ja", "bou shaant", "bou shant", "keep quiet", "keep tc", "keep tk", "go to sleep"]
                                wake_cmds = ["uth jao", "wake up", "wake up sat", "wake up buddy", "uth ja"]
                                
                                if getattr(self, "quiet_mode", False):
                                    if any(cmd in txt_lower for cmd in wake_cmds):
                                        self.quiet_mode = False
                                        self.ui.write_log("SYS: Saturday woke up from Quiet Mode.")
                                        self.speak("I'm awake, sir. Online and ready.")
                                else:
                                    if any(cmd in txt_lower for cmd in sleep_cmds) or txt_lower == "quiet":
                                        self.quiet_mode = True
                                        self.ui.write_log("SYS: Saturday entered Quiet/Sleep Mode.")
                                        self.speak("Going silent, sir. Speak when you need me.")

                        if sc.turn_complete:
                            self._server_turn_active = False
                            self.update_speaking_state()

                            full_in = " ".join(in_buf).strip()
                            self._ignore_server_response = False
                            if full_in:
                                self._last_user_activity = time.time()
                                if not self._has_wake_word(full_in):
                                    self.ui.write_log(f"You: {full_in} [Ignored - No wake word]")
                                    while not self.audio_in_queue.empty():
                                        try:
                                            self.audio_in_queue.get_nowait()
                                        except Exception:
                                            break
                                    self._playing_chunk = False
                                    self._ignore_server_response = True
                                    in_buf = []
                                    out_buf = []
                                    continue
                                
                                # Voice prompt moderation check
                                from core.moderation import moderate_prompt
                                blocked_reason = moderate_prompt(full_in)
                                if blocked_reason:
                                    refusal = "I cannot assist with that request as it violates safety guidelines, sir."
                                    self.ui.set_last_response(refusal)
                                    self.ui.write_log(f"SYS: BLOCKED (Moderation): {blocked_reason}")
                                    self.speak(refusal)
                                    self._ignore_server_response = True
                                    in_buf = []
                                    out_buf = []
                                    continue

                                self.ui.write_log(f"You: {full_in}")
                                
                                # 1. Translate voice input
                                try:
                                    from actions.translate import translate_text, detect_language
                                    user_lang = detect_language(full_in)
                                    self._last_user_language = user_lang
                                    translated = translate_text(full_in, target_lang="English")
                                    self.ui.write_log(f"Detected Lang: {user_lang} | Translated: {translated}")
                                except Exception as e:
                                    print(f"[WARN] Translation failed: {e}")

                                # 2. Detect emotion
                                def detect_and_set_voice():
                                    try:
                                        from core.emotion import detect_emotion
                                        self._current_emotion = detect_emotion(full_in)
                                    except Exception as e:
                                        print(f"[WARN] Voice emotion detection failed: {e}")
                                threading.Thread(target=detect_and_set_voice, daemon=True).start()

                                # 3. Query RAG context
                                rag_context = ""
                                try:
                                    from memory.knowledge import search_knowledge
                                    rag_context = search_knowledge(full_in)
                                except Exception as e:
                                    print(f"[WARN] Voice RAG context fetch failed: {e}")

                                # 4. GitHub and Web Search Triggers for voice
                                is_git = "github" in full_in.lower() or "issue" in full_in.lower() or "commit" in full_in.lower()
                                is_search = "search" in full_in.lower() or "find" in full_in.lower()

                                if is_git:
                                    try:
                                        from actions.github_control import github_action
                                        git_res = github_action(full_in)
                                        self.ui.write_log(f"GitHub: {git_res}")
                                        self.speak(git_res)
                                    except Exception as e:
                                        print(f"Voice GitHub failed: {e}")
                                elif is_search or rag_context:
                                    try:
                                        from actions.search import web_search
                                        results = web_search(full_in) if is_search else ""
                                        
                                        # Assemble final prompt
                                        prompt_parts = []
                                        if results:
                                            prompt_parts.append(f"Search results:\n{results}")
                                        if rag_context:
                                            prompt_parts.append(f"Additional Knowledge Context:\n{rag_context}")
                                        prompt_parts.append(f"User asked: {full_in}\nAnswer based on this context.")
                                        
                                        final_prompt = "\n\n".join(prompt_parts)
                                        self.ui.write_log("SYS: Voice context injection triggered.")
                                        self.speak(final_prompt)
                                    except Exception as e:
                                        print(f"Voice search/RAG execution failed: {e}")

                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                # Apply emotion adaptation prefix
                                try:
                                    from core.emotion import adapt_response_for_emotion
                                    emotion = getattr(self, "_current_emotion", "neutral")
                                    full_out = adapt_response_for_emotion(emotion, full_out)
                                    self._current_emotion = "neutral"
                                except Exception as e:
                                    print(f"[WARN] Emotion adaptation failed: {e}")
                                    
                                self.ui.write_log(f"Saturday: {full_out}")
                                self.ui.set_last_response(full_out)
                            out_buf = []

                            if full_in and len(full_in) > 5:
                                threading.Thread(
                                    target=_update_memory_async,
                                    args=(full_in, full_out),
                                    daemon=True
                                ).start()

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            if getattr(self, "quiet_mode", False):
                                print(f"[SATURDAY] 📞 {fc.name} (Quiet mode active - suspended)")
                                fn_responses.append(
                                    types.FunctionResponse(
                                        name=fc.name,
                                        id=fc.id,
                                        response={"result": "Saturday is in Quiet/Sleep Mode. Tool execution is suspended."}
                                    )
                                )
                            else:
                                print(f"[SATURDAY] 📞 {fc.name}")
                                fr = await self._execute_tool(fc)
                                fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )

                    # Log any unhandled response types to aid debugging
                    handled_fields = [
                        "data", "server_content", "tool_call", "setup_complete",
                        "session_resumption_update", "voice_activity_detection_signal",
                        "voice_activity", "go_away", "tool_call_cancellation", "usage_metadata"
                    ]
                    handled = any(getattr(response, field, None) is not None for field in handled_fields)
                    if not handled:
                        print(f"[SATURDAY] ⚠️ Unhandled response type: {response}")

        except Exception as e:
            print(f"[SATURDAY] ❌ Recv: {e}")
            self._server_turn_active = False
            self._playing_chunk = False
            self.update_speaking_state()
            traceback.print_exc()
            raise

    def _play_audio(self):
        import queue
        print("[SATURDAY] 🔊 Play thread started")
        stream = None
        current_volume = 2.0
        
        while True:
            try:
                if stream is None:
                    try:
                        stream = sd.RawOutputStream(
                            samplerate=RECEIVE_SAMPLE_RATE,
                            channels=CHANNELS,
                            dtype="int16",
                            blocksize=0,
                            latency=0.25,
                        )
                        stream.start()
                        self._audio_out_stream = stream
                        if self._loop:
                            self._loop.call_soon_threadsafe(self.ui.write_log, "SYS: Speaker stream opened successfully.")
                    except Exception as first_err:
                        try:
                            device_info = sd.query_devices(kind='output')
                            default_rate = int(device_info.get('default_samplerate', 24000))
                            print(f"[SATURDAY] 🔊 24000Hz failed. Trying default output device rate: {default_rate}Hz (Err: {first_err})")
                            stream = sd.RawOutputStream(
                                samplerate=default_rate,
                                channels=CHANNELS,
                                dtype="int16",
                                blocksize=0,
                                latency=0.25,
                            )
                            stream.start()
                            self._audio_out_stream = stream
                            if self._loop:
                                self._loop.call_soon_threadsafe(self.ui.write_log, f"SYS: Speaker stream opened at default rate {default_rate}Hz.")
                        except Exception as se:
                            print(f"[SATURDAY] ❌ Audio output device open failed: {se}")
                            if self._loop:
                                self._loop.call_soon_threadsafe(self.ui.write_log, "SYS: Speaker stream error. Retrying in 5s...")
                            time.sleep(5)
                            continue

                try:
                    if not self._playing_chunk:
                        current_volume = _load_volume_multiplier()
                        # Only buffer if the server is actively generating/sending audio
                        if self._server_turn_active and self.audio_in_queue.qsize() < 4:
                            for _ in range(8):
                                if self.audio_in_queue.qsize() >= 4 or not self._server_turn_active:
                                    break
                                time.sleep(0.05)

                    if self.audio_in_queue.qsize() == 0 and self._server_turn_active:
                        print("[SATURDAY] 🔊 Queue underflow, buffering to prevent cracking...")
                        for _ in range(10):
                            if self.audio_in_queue.qsize() >= 4 or not self._server_turn_active:
                                break
                            time.sleep(0.05)

                    try:
                        chunk = self.audio_in_queue.get(timeout=0.5)
                    except queue.Empty:
                        if self._playing_chunk:
                            self._playing_chunk = False
                            if self._loop:
                                self._loop.call_soon_threadsafe(self.update_speaking_state)
                                if not self._tool_executing:
                                    self._loop.call_soon_threadsafe(self.ui.set_activity, "SYSTEM IDLE")
                        continue

                    if chunk is None:
                        self._playing_chunk = False
                        if self._loop:
                            self._loop.call_soon_threadsafe(self.update_speaking_state)
                        continue

                    self._playing_chunk = True
                    if self._loop:
                        self._loop.call_soon_threadsafe(self.update_speaking_state)
                        if not self._tool_executing:
                            self._loop.call_soon_threadsafe(self.ui.set_activity, "SPEAKING RESPONSE")

                    if chunk and len(chunk) > 0:
                        audio_data = np.frombuffer(chunk, dtype=np.int16)
                        amplified = np.clip(audio_data * current_volume, -32768, 32767).astype(np.int16)
                        chunk = amplified.tobytes()

                        try:
                            # Calculate RMS volume of played AI voice audio, casting to float32 to prevent overflow
                            rms = np.sqrt(np.mean(amplified.astype(np.float32)**2))
                            # Normalize typical peak to 0.0-1.0
                            volume = min(1.0, rms / 5500.0)
                            if self._loop:
                                self._loop.call_soon_threadsafe(self.ui.set_audio_level, volume)
                        except Exception as e:
                            print(f"[WARN] Audio level calculation error: {e}")

                    # Write synchronously directly in the thread
                    stream.write(chunk)
                    self._last_speak_time = time.time()

                except Exception as write_err:
                    print(f"[SATURDAY] ❌ Stream write error: {write_err}")
                    if self._loop:
                        self._loop.call_soon_threadsafe(self.ui.write_log, "SYS: Audio output device disconnected. Reconnecting stream...")
                    try:
                        stream.stop()
                        stream.close()
                    except Exception as e:
                        print(f"[WARN] Error closing audio output stream: {e}")
                    stream = None
                    self._audio_out_stream = None
                    time.sleep(1)

            except Exception as e:
                print(f"[SATURDAY] ❌ Play main loop: {e}")
                time.sleep(2)

        self._playing_chunk = False
        if self._loop:
            self._loop.call_soon_threadsafe(self.update_speaking_state)
        if stream:
            try:
                stream.stop()
                stream.close()
            except Exception as e:
                print(f"[WARN] Error closing audio stream: {e}")
        self._audio_out_stream = None

    def _wait_for_wake_word(self):
        import speech_recognition as sr
        
        self.ui.set_state("STANDBY")
        self.ui.set_activity("STANDBY")
        
        self.ui.show_custom_alert(
            "Standby Mode", 
            "Saturday is now in Standby Mode to save data and resources.\n\nSpeak 'Hey Saturday' or 'Sat' to wake me up.", 
            "wake"
        )
        
        try:
            r = sr.Recognizer()
            r.energy_threshold = 300
            r.dynamic_energy_threshold = True
            mic = sr.Microphone()
            with mic as source:
                pass
        except Exception as mic_err:
            print(f"[SATURDAY] 🎙️ Microphone init failed: {mic_err}")
            self.ui.write_log(f"SYS: Microphone initialization failed: {mic_err}. Disabling wake-word standby.")
            self.ui.show_custom_alert("Voice Input Error", f"Failed to initialize microphone: {mic_err}", "error")
            try:
                settings = self.ui._load_settings()
                settings["wake_word_enabled"] = False
                self.ui._save_settings(settings)
            except Exception as e:
                print(f"[WARN] Failed to disable wake_word_enabled in settings: {e}")
            return

        print("[SATURDAY] 🎙️ Standing by. Listening locally for wake-word...")
        
        with mic as source:
            while True:
                # If user unchecks enable wake word in settings, break and connect directly
                settings = self.ui._load_settings()
                if not settings.get("wake_word_enabled", False):
                    print("[SATURDAY] Wake word disabled in settings. Connecting immediately.")
                    break
                    
                try:
                    audio = r.listen(source, timeout=1.0, phrase_time_limit=3.0)
                    
                    from core.offline_fallback import is_internet_available
                    if not is_internet_available():
                        from core.local_stt import transcribe_audio_locally
                        text = transcribe_audio_locally(audio)
                        if text.startswith("ERROR_"):
                            if not text.startswith("ERROR_TIMEOUT"):
                                self.ui.write_log(f"STT: {text}")
                            text = ""
                    else:
                        text = r.recognize_google(audio, language="en-IN")
                        
                    text = text.lower().strip()
                    print(f"[WAKE WORD SEARCH] Heard: {text}")
                    
                    if "saturday" in text or "sat" in text or "satar" in text:
                        print("[SATURDAY] 🎉 Wake word detected!")
                        self.ui.show_custom_alert(
                            "Waking Up", 
                            "Saturday has detected the wake word and is now connecting online.", 
                            "wake"
                        )
                        break
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except Exception as e:
                    print(f"[WARN] Wake-word listening exception: {e}")
                    time.sleep(0.5)
                    continue

    async def _monitor_idle(self):
        self._last_user_activity = time.time()
        while True:
            await asyncio.sleep(1)
            settings = self.ui._load_settings()

            # Flush pending memories if idle for >15s since last turn
            global _pending_memory_turns, _last_memory_turn_time
            if len(_pending_memory_turns) > 0 and (time.time() - _last_memory_turn_time > 15.0):
                print("[Memory] 🕒 Idle memory flush triggered...")
                threading.Thread(target=flush_pending_memories, daemon=True).start()

            # Watchdog for stuck speaking state
            with self._speaking_lock:
                is_sp = self._is_speaking
            ui_state = "UNKNOWN"
            try:
                if self.ui and self.ui._win and self.ui._win.hud:
                    ui_state = self.ui._win.hud.state
            except Exception:
                pass

            if is_sp or ui_state == "SPEAKING":
                last_speak = getattr(self, "_last_speak_time", 0.0)
                start_time = getattr(self, "_speaking_start_time", 0.0)
                ref_time = max(last_speak, start_time)
                if ref_time > 0.0 and (time.time() - ref_time > 1.8):
                    print("[SATURDAY] 🐕 Speaking watchdog triggered! Resetting stuck speaking state...")
                    self._playing_chunk = False
                    self._server_turn_active = False
                    
                    stream_to_close = getattr(self, "_audio_out_stream", None)
                    if stream_to_close:
                        try:
                            print("[SATURDAY] 🐕 Stuck audio stream detected. Closing and resetting...")
                            stream_to_close.stop()
                            stream_to_close.close()
                        except Exception as se:
                            print(f"[SATURDAY] Error closing stuck stream: {se}")
                        self._audio_out_stream = None

                    self.update_speaking_state()
                    try:
                        self.ui.set_state("LISTENING")
                    except Exception:
                        pass
                    if not self._tool_executing:
                        self.ui.set_activity("SYSTEM IDLE")

            if settings.get("continuous_listening_24h", True) or not settings.get("wake_word_enabled", False):
                self._last_user_activity = time.time()
                continue

            # If speaking, reset idle timer
            with self._speaking_lock:
                is_sp = self._is_speaking
            if is_sp or self._playing_chunk:
                self._last_user_activity = time.time()
                
            elapsed = time.time() - self._last_user_activity
            if elapsed >= 45.0:
                print("[SATURDAY] 💤 Idle timeout reached. Disconnecting...")
                self.ui.write_log("SYS: Idle timeout reached. Going to standby.")
                self.speak("सर, मैं अब स्टैंडबाई मोड में जा रही हूँ। ज़रूरत हो तो आवाज़ दीजिएगा।")
                await asyncio.sleep(4)
                raise SessionIdleTimeout()

    async def run(self):
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        retry_count = 0

        while True:
            try:
                # 1. Wake word standby check
                settings = self.ui._load_settings()
                if settings.get("wake_word_enabled", False):
                    # Wait for wake word in separate thread
                    await asyncio.to_thread(self._wait_for_wake_word)

                print(f"[SATURDAY] 🔌 Connecting... (attempt {retry_count + 1})")
                self.ui.write_log("SYS: Connecting to Gemini API...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                try:
                    async with (
                        client.aio.live.connect(model=self.ui._load_settings().get('live_model', 'models/gemini-2.5-flash-native-audio-preview-12-2025'), config=config) as session,
                        asyncio.TaskGroup() as tg,
                    ):
                        self.session             = session
                        self._loop               = asyncio.get_event_loop()
                        self._last_user_activity = time.time()
                        
                        # Clear any leftover chunks on reconnect
                        while not self.audio_in_queue.empty():
                            try:
                                self.audio_in_queue.get_nowait()
                            except Exception:
                                break
                        self.out_queue           = asyncio.Queue(maxsize=300)
                        self._server_turn_active = False
                        self._playing_chunk      = False

                        # Successful connection — reset retry counter
                        retry_count = 0

                        print("[SATURDAY] ✅ Connected.")
                        self.ui.set_state("LISTENING")
                        self.ui.set_activity("SYSTEM IDLE")

                        if self._welcomed:
                            self.ui.write_log("SYS: SATURDAY reconnected.")
                        else:
                            self.ui.write_log("SYS: SATURDAY online.")

                        async def _send_welcome():
                            if self._welcomed:
                                return
                            await asyncio.sleep(1)
                            from actions.briefing import get_morning_briefing
                            self.ui.write_log("SYS: Fetching morning briefing for Malegaon...")
                            try:
                                # Run morning briefing in a background thread to prevent event loop blocking
                                briefing = await asyncio.to_thread(get_morning_briefing, "Malegaon")
                                self.speak(briefing)
                            except Exception as briefing_err:
                                print(f"[SATURDAY] Morning briefing failed: {briefing_err}")
                                self.speak("सिस्टम इनिशियलाइज्ड। प्रतीक सर, सैटरडे ऑनलाइन है।")
                            self._welcomed = True

                        tg.create_task(self._send_realtime())
                        tg.create_task(self._listen_audio())
                        tg.create_task(self._receive_audio())
                        tg.create_task(self._monitor_idle())
                        tg.create_task(_send_welcome())
                finally:
                    # Flush pending memories on disconnect
                    print("[Memory] 🔌 Session ended. Flushing pending memories...")
                    threading.Thread(target=flush_pending_memories, daemon=True).start()

            except SessionIdleTimeout:
                print("[SATURDAY] Session idle timeout. Returning to standby.")
                retry_count = 0
            except Exception as e:
                is_idle = False
                if isinstance(e, SessionIdleTimeout):
                    is_idle = True
                elif type(e).__name__ == 'ExceptionGroup':
                    for ie in getattr(e, "exceptions", []):
                        if isinstance(ie, SessionIdleTimeout):
                            is_idle = True
                            break
                
                if is_idle:
                    print("[SATURDAY] Session idle timeout. Returning to standby.")
                    retry_count = 0
                else:
                    from core.offline_fallback import is_internet_available
                    if not is_internet_available():
                        await self._run_offline_loop()
                        retry_count = 0
                    else:
                        retry_count += 1
                        err_msg = str(e)
                        if hasattr(e, "exceptions") and e.exceptions:
                            inner_errs = [str(ie) for ie in e.exceptions]
                            err_msg = "; ".join(inner_errs)
                        print(f"[SATURDAY] ⚠️ Attempt {retry_count}/{MAX_RETRY_ATTEMPTS}: {err_msg}")
                        traceback.print_exc()
                        self.ui.write_log(f"SYS: Connection failed ({retry_count}/{MAX_RETRY_ATTEMPTS}): {err_msg[:55]}")

            self._server_turn_active = False
            self._playing_chunk      = False
            self.update_speaking_state()
            self.ui.set_state("THINKING")

            if retry_count >= MAX_RETRY_ATTEMPTS:
                # Give up temporarily — notify user and wait 60s before resetting
                msg = (
                    f"Sir, I have failed to connect {MAX_RETRY_ATTEMPTS} times in a row. "
                    "Please check your internet connection. "
                    "I will try again in one minute."
                )
                print(f"[SATURDAY] 🚫 Max retries reached. Pausing 60s.")
                self.ui.write_log("SYS: Max retries reached. Pausing 60 seconds...")
                retry_count = 0
                await asyncio.sleep(60)
            else:
                # Check settings: if wake word is active, don't sleep 3s as we want to go straight to standby!
                settings = self.ui._load_settings()
                if not settings.get("wake_word_enabled", False):
                    print("[SATURDAY] 🔄 Reconnecting in 3s...")
                    self.ui.write_log("SYS: Reconnecting in 3 seconds...")
                    await asyncio.sleep(3)

import asyncio
import threading
import sys
import traceback
import warnings
import logging
import queue
import re
import time
from pathlib import Path
import numpy as np

logger = logging.getLogger("ip_prime.main")

warnings.filterwarnings("ignore", category=FutureWarning, module="google")

# Force console streams to use UTF-8 to prevent charmap Unicode crashes on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import sounddevice as sd
from google import genai
from google.genai import types
from ui import IPRayUI
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
    append_session_turn, format_session_for_prompt,
    save_shutdown_summary, format_last_session_for_prompt,
)

from agent.autonomous_core import AutonomousCore


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


LIVE_MODEL          = "gemini-2.5-flash-native-audio-latest"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 2048   # smaller = lower mic→API latency (~64ms @ 16kHz)
PLAY_BUFFER_SAMPLES = 1024   # smaller = voice starts sooner (~43ms @ 24kHz)
VOICE_OUTPUT_GAIN   = 1.2
LOW_LATENCY_PLAYBACK = True  # stream TTS chunks immediately (overridden by config)

from core.session import _get_api_key, _load_system_prompt, _clean_transcript



from core.tool_registry import TOOL_DECLARATIONS



def play_sfx(sfx_type: str):
    def play_thread():
        try:
            import numpy as np
            import sounddevice as sd
            import json
            from pathlib import Path
            sample_rate = 16000
            
            sound_pack = "cyberpunk"
            config_file = Path("config/api_keys.json")
            if config_file.exists():
                try:
                    data = json.loads(config_file.read_text(encoding="utf-8"))
                    sound_pack = data.get("sound_pack", "cyberpunk").lower()
                except Exception:
                    pass

            snd = None
            if sfx_type == "alarm":
                duration = 5.0  # 5 seconds
                t = np.linspace(0, duration, int(sample_rate * duration), False)
                freq = 950 + 350 * np.sin(2 * np.pi * 2.0 * t)
                phase = 2 * np.pi * np.cumsum(freq) / sample_rate
                siren = np.sign(np.sin(phase))
                pulse = 0.5 * (1.0 + np.sign(np.sin(2 * np.pi * 4.0 * t)))
                snd = 0.6 * siren * pulse
            elif sound_pack == "cyberpunk":
                if sfx_type == "startup":
                    t = np.linspace(0, 0.5, int(sample_rate * 0.5), False)
                    f = np.linspace(80, 220, len(t))
                    glitch = np.sign(np.sin(2 * np.pi * f * t))
                    snd = 0.15 * glitch * np.exp(-4 * t)
                    t_high = np.linspace(0, 0.1, int(sample_rate * 0.1), False)
                    high_chirp = 0.1 * np.sin(2 * np.pi * np.linspace(2000, 4000, len(t_high)) * t_high) * np.exp(-30 * t_high)
                    snd[:len(high_chirp)] += high_chirp
                elif sfx_type == "wake":
                    t = np.linspace(0, 0.15, int(sample_rate * 0.15), False)
                    f = np.linspace(150, 450, len(t))
                    snd = 0.2 * np.sign(np.sin(2 * np.pi * f * t)) * np.exp(-12 * t)
                elif sfx_type == "tool_start":
                    t = np.linspace(0, 0.08, int(sample_rate * 0.08), False)
                    snd = 0.15 * np.sign(np.sin(2 * np.pi * 300 * t)) * np.exp(-40 * t)
                elif sfx_type == "tool_done":
                    t = np.linspace(0, 0.3, int(sample_rate * 0.3), False)
                    f = np.linspace(400, 900, len(t))
                    snd = 0.18 * np.sign(np.sin(2 * np.pi * f * t)) * np.exp(-15 * t)

            elif sound_pack == "lcars":
                if sfx_type == "startup":
                    t = np.linspace(0, 0.45, int(sample_rate * 0.45), False)
                    f1 = np.linspace(350, 700, len(t))
                    snd = 0.25 * np.sin(2 * np.pi * f1 * t) * (np.linspace(1, 0, len(t)) ** 1.5)
                elif sfx_type == "wake":
                    t1 = np.linspace(0, 0.08, int(sample_rate * 0.08), False)
                    t2 = np.linspace(0, 0.12, int(sample_rate * 0.12), False)
                    snd1 = 0.22 * np.sin(2 * np.pi * 880 * t1)
                    snd2 = 0.22 * np.sin(2 * np.pi * 1046 * t2)
                    gap = np.zeros(int(sample_rate * 0.02))
                    snd = np.concatenate([snd1, gap, snd2])
                    snd = snd * np.concatenate([np.ones(len(snd1) + len(gap)), np.linspace(1, 0, len(snd2))])
                elif sfx_type == "tool_start":
                    t = np.linspace(0, 0.06, int(sample_rate * 0.06), False)
                    snd = 0.18 * np.sin(2 * np.pi * 500 * t) * np.exp(-40 * t)
                elif sfx_type == "tool_done":
                    t1 = np.linspace(0, 0.06, int(sample_rate * 0.06), False)
                    t2 = np.linspace(0, 0.12, int(sample_rate * 0.12), False)
                    snd1 = 0.2 * np.sin(2 * np.pi * 660 * t1)
                    snd2 = 0.2 * np.sin(2 * np.pi * 880 * t2)
                    gap = np.zeros(int(sample_rate * 0.015))
                    snd = np.concatenate([snd1, gap, snd2])
                    snd = snd * np.concatenate([np.ones(len(snd1) + len(gap)), np.linspace(1, 0, len(snd2))])

            elif sound_pack == "glass":
                if sfx_type == "startup":
                    t = np.linspace(0, 0.5, int(sample_rate * 0.5), False)
                    snd = 0.2 * np.sin(2 * np.pi * 1800 * t) * np.exp(-12 * t) + \
                          0.1 * np.sin(2 * np.pi * 2400 * t) * np.exp(-18 * t)
                elif sfx_type == "wake":
                    t = np.linspace(0, 0.25, int(sample_rate * 0.25), False)
                    snd = 0.22 * np.sin(2 * np.pi * 1500 * t) * np.exp(-22 * t)
                elif sfx_type == "tool_start":
                    t = np.linspace(0, 0.04, int(sample_rate * 0.04), False)
                    snd = 0.18 * np.sin(2 * np.pi * 1200 * t) * np.exp(-80 * t)
                elif sfx_type == "tool_done":
                    t = np.linspace(0, 0.35, int(sample_rate * 0.35), False)
                    snd = 0.2 * np.sin(2 * np.pi * 1320 * t) * np.exp(-15 * t) + \
                          0.15 * np.sin(2 * np.pi * 1650 * t) * np.exp(-25 * t) + \
                          0.1 * np.sin(2 * np.pi * 1980 * t) * np.exp(-35 * t)

            elif sound_pack == "arcade":
                if sfx_type == "startup":
                    t = np.linspace(0, 0.08, int(sample_rate * 0.08), False)
                    snd1 = np.sign(np.sin(2 * np.pi * 261.63 * t))
                    snd2 = np.sign(np.sin(2 * np.pi * 329.63 * t))
                    snd3 = np.sign(np.sin(2 * np.pi * 392.00 * t))
                    snd4 = np.sign(np.sin(2 * np.pi * 523.25 * t))
                    snd = 0.1 * np.concatenate([snd1, snd2, snd3, snd4])
                elif sfx_type == "wake":
                    t1 = np.linspace(0, 0.07, int(sample_rate * 0.07), False)
                    t2 = np.linspace(0, 0.2, int(sample_rate * 0.2), False)
                    snd1 = 0.18 * np.sign(np.sin(2 * np.pi * 987.77 * t1))
                    snd2 = 0.18 * np.sign(np.sin(2 * np.pi * 1318.51 * t2))
                    snd = np.concatenate([snd1, snd2])
                elif sfx_type == "tool_start":
                    t = np.linspace(0, 0.1, int(sample_rate * 0.1), False)
                    f = np.linspace(150, 600, len(t))
                    snd = 0.15 * np.sign(np.sin(2 * np.pi * f * t))
                elif sfx_type == "tool_done":
                    t = np.linspace(0, 0.25, int(sample_rate * 0.25), False)
                    f = np.linspace(523, 1046, len(t))
                    snd = 0.12 * np.sign(np.sin(2 * np.pi * f * t)) * np.linspace(1, 0, len(t))

            else:
                if sfx_type == "startup":
                    t = np.linspace(0, 0.4, int(sample_rate * 0.4), False)
                    f1 = np.linspace(220, 440, len(t))
                    f2 = np.linspace(330, 660, len(t))
                    snd = 0.3 * (np.sin(2 * np.pi * f1 * t) + np.sin(2 * np.pi * f2 * t))
                    fade = np.linspace(1, 0, len(t)) ** 2
                    snd = snd * fade
                elif sfx_type == "wake":
                    t1 = np.linspace(0, 0.08, int(sample_rate * 0.08), False)
                    t2 = np.linspace(0, 0.12, int(sample_rate * 0.12), False)
                    snd1 = 0.25 * np.sin(2 * np.pi * 880 * t1)
                    snd2 = 0.25 * np.sin(2 * np.pi * 1200 * t2)
                    gap = np.zeros(int(sample_rate * 0.02))
                    snd = np.concatenate([snd1, gap, snd2])
                    snd = snd * np.concatenate([np.ones(len(snd1) + len(gap)), np.linspace(1, 0, len(snd2))])
                elif sfx_type == "tool_start":
                    t = np.linspace(0, 0.05, int(sample_rate * 0.05), False)
                    snd = 0.15 * np.sin(2 * np.pi * 600 * t) * np.exp(-50 * t)
                elif sfx_type == "tool_done":
                    t1 = np.linspace(0, 0.06, int(sample_rate * 0.06), False)
                    t2 = np.linspace(0, 0.1, int(sample_rate * 0.1), False)
                    snd1 = 0.2 * np.sin(2 * np.pi * 523.25 * t1)
                    snd2 = 0.2 * np.sin(2 * np.pi * 659.25 * t2)
                    gap = np.zeros(int(sample_rate * 0.01))
                    snd = np.concatenate([snd1, gap, snd2])
                    snd = snd * np.concatenate([np.ones(len(snd1) + len(gap)), np.linspace(1, 0, len(snd2))])

            if snd is not None:
                sd.play(snd.astype(np.float32), sample_rate)
                sd.wait()
        except Exception as e:
            print(f"[SFX] Failed to play {sfx_type}: {e}")

    import threading
    threading.Thread(target=play_thread, daemon=True).start()


class IPRayLive:

    def __init__(self, ui: IPRayUI):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        import queue
        self.audio_playback_queue = queue.Queue()
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self.ui.on_text_command = self._on_text_command
        self._turn_done_event: asyncio.Event | None = None
        self._tool_active = False
        self._mic_interruption_buffer = []
        self._text_interruption_buffer = []
        self._buffering_interruption = False
        self._connect_count = 0
        self._force_welcome = False
        self._play_buffer = bytearray()
        self._mcp_tools_cache: list | None = None
        self._prompt_cache: tuple[float, types.LiveConnectConfig] | None = None
        self._quiet_mode = False
        self._has_greeted_on_startup = False
        
        # Set up TTS streaming queue
        self.tts_queue = queue.Queue()
        self._tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self._tts_thread.start()

        # Initialize MCP Client Manager (deferred slightly to reduce startup lag)
        def _init_mcp():
            try:
                from actions.mcp_client import MCPClientManager
                MCPClientManager().initialize(player=self.ui)
            except Exception as e:
                print(f"[IP PRIME] Failed to initialize MCP Client: {e}")
        threading.Timer(2.0, _init_mcp).start()

        # Initialize Wake Word Spotter Thread (deferred to avoid startup stutter)
        self._wake_word_spotter = None
        def _init_wake_word():
            try:
                self._start_wake_word_spotter()
            except Exception as e:
                print(f"[IP PRIME] Failed to initialize Wake Word: {e}")
        threading.Timer(3.0, _init_wake_word).start()

        if hasattr(self.ui, "_win") and self.ui._win:
            self.ui._win.ip_ray = self

        # Initialize 100% Autonomous AI Core in background
        def _start_autonomous_core():
            try:
                self.autonomous_core = AutonomousCore()
                # Run the heartbeat loop
                self.autonomous_core.run_forever()
            except Exception as e:
                print(f"[IP PRIME] Failed to start Autonomous Core: {e}")
        
        self._autonomous_thread = threading.Thread(target=_start_autonomous_core, daemon=True, name="AutonomousCoreThread")
        self._autonomous_thread.start()

    def _tts_worker(self):
        while True:
            text = self.tts_queue.get()
            if text is None: break
            # Lower-latency chunk-based TTS streaming simulation logic here
            # In a real impl, this would break text into sentences and stream
            # to a low-latency TTS engine like pyttsx3 or similar.
            pass

    def _start_wake_word_spotter(self):
        try:
            if hasattr(self, "_wake_word_spotter") and self._wake_word_spotter:
                self._wake_word_spotter.stop()
            from actions.wake_word import WakeWordSpotterThread
            self._wake_word_spotter = WakeWordSpotterThread(
                on_wake_callback=self._on_wake_word_spotted,
                ui=self.ui
            )
            self._wake_word_spotter.start()
        except Exception as e:
            print(f"[IP PRIME] Error starting wake word spotter thread: {e}")

    def _on_wake_word_spotted(self):
        # Play elegant wake word chime
        play_sfx("startup")
        
        # Unmute the UI state safely in thread-safe manner
        def _unmute_ui():
            self.ui.muted = False
            self._muted_cache = False
            self.ui.write_log("✨ [Wake Word] 'Hey Prime' spotted! Active and listening...")
            
        if self._loop:
            self._loop.call_soon_threadsafe(_unmute_ui)
        else:
            _unmute_ui()
            
        # Speak a short and crisp "Hi" on wake word detection
        if self._loop and self.session:
            self.speak("Hi")

    def trigger_personality_reload_and_greeting(self):
        self.ui.write_log("SYS: Rebooting AI Core with new personality matrix...")
        self._prompt_cache = None
        self._has_greeted_on_startup = False
        if self._loop and self.session:
            asyncio.run_coroutine_threadsafe(self._send_startup_welcome(), self._loop)
        else:
            self._force_welcome = True
            self.session = None

    async def _send_startup_welcome(self) -> None:
        await asyncio.sleep(1.2)
        if not self.session:
            return
        if self._has_greeted_on_startup:
            return
        self._has_greeted_on_startup = True
        self.ui.write_log("SYS: Startup greeting queued.")
        self.ui.write_thought("Online — welcome")
        
        # Check if hacker mode is active
        hacker_mode = False
        try:
            from actions.model_switcher import load_model_preference
            hacker_mode = load_model_preference().get("hacker_mode", False)
        except Exception:
            pass
            
        disclaimer_prefix = ""
        if hacker_mode:
            disclaimer_text = (
                "Hacker Mode active. All tools are for educational use and testing on "
                "systems you own or have explicit permission to test. Unauthorized access "
                "to computer systems is a criminal offence under the IT Act 2000 (India) "
                "and similar laws worldwide."
            )
            disclaimer_prefix = f"Speak the following mandatory security disclaimer FIRST: '{disclaimer_text}'. Then, "
            self.ui.write_log(f"⚠️ {disclaimer_text}")

        import random
        sweet_samples = [
            "System initialized, bhai! Main IP Prime online aa chuka hoon. Cockpit visualizers stable hain. Batao aaj kya build karein? Let's rule the day, bro!",
            "Yo Pratik! Core system fully operational hai, dost. Space nebulae and stardust are synchronized. Batao bhai, aaj code me kya aag lagani hai?",
            "All visual systems and semantic stores are online, bhai! Antigravity AI completely ready hai. Sab set hai, batao aaj kis command par kaam karna hai, bro!",
            "Hey Pratik! Startup calibration complete! OLED cockpit is fully illuminated. Welcome back, bhai. Main ready hoon, tell me what's the plan today!",
            "Online and operational, dost! Your custom-built Second Brain is loaded and habits tracker is live. Boliye, aaj kya fodna hai, bhai!"
        ]
        sample_greeting = random.choice(sweet_samples)
        
        self.speak(
            f"[SYSTEM_EVENT] System online. {disclaimer_prefix}Greet Pratik in natural friendly Hinglish. "
            f"Speak only this exact welcoming phrase and nothing else: '{sample_greeting}'"
        )

    def _amplify_pcm(self, block: bytes, gain: float = 1.8) -> bytes:
        try:
            audio = np.frombuffer(block, dtype=np.int16)
            loud = np.clip(audio.astype(np.float32) * gain, -32768, 32767)
            return loud.astype(np.int16).tobytes()
        except Exception:
            return block


    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return

        if self._tool_active:
            self.ui.write_log("SYS: Pratik Sir, ek activity currently running hai. Please wait karein, sir.")
            return

        txt_l = text.lower().strip()
        
        # Quiet mode controls for text input
        if "prime quiet" in txt_l or "prime quite" in txt_l or "chup ho jao" in txt_l or "chup hojao" in txt_l:
            self._quiet_mode = True
            self.ui.write_log("SYS: Quiet Mode activated.")
            self.speak("Entering quiet mode, sir. I will remain silent until you say 'prime wakeup'.")
            return
        elif "prime wakeup" in txt_l or "prime wake up" in txt_l or "wake up prime" in txt_l:
            if self._quiet_mode:
                self._quiet_mode = False
                self.ui.write_log("SYS: Quiet Mode deactivated.")
                play_sfx("startup")
                self.speak("I am awake and listening, sir!")
                return

        if self._quiet_mode:
            self.ui.write_log("SYS: [Quiet Mode Active] Command ignored. Type 'prime wakeup' to resume.")
            return

        if txt_l in ["full screen", "fullscreen"]:
            self.ui.write_log("SYS: Intercepted 'full screen' command.")
            self.ui.set_fullscreen(True)
            self.speak("Going fullscreen now, sir.")
            return
        elif txt_l == "exit":
            self.ui.write_log("SYS: Intercepted 'exit' command.")
            self.ui.set_fullscreen(False)
            self.speak("Exiting fullscreen mode, sir.")
            return

        if text.lower().strip() == "go to sleep":
            self.ui.write_log("SYS: Intercepted 'go to sleep' command.")
            self.speak("Going to sleep now, sir. Good night.")
            def _shutdown():
                import time, os
                save_shutdown_summary()
                time.sleep(1.5)
                os._exit(0)
            threading.Thread(target=_shutdown, daemon=True).start()
            return
        with self._speaking_lock:
            is_speaking = self._is_speaking

        if is_speaking:
            self._text_interruption_buffer.append(text)
            self.ui.write_log("SYS: Pratik Sir, aapka text message queue kar liya hai. IP Prime ke bolne ke baad response milega.")
            return

        self.route_user_message(text, is_voice=False)

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def speak(self, text: str):
        # Chunk-based streaming: Use tts_queue for lower latency
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            if sentence.strip():
                self.tts_queue.put(sentence.strip())
        
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_realtime_input(text=text),
            self._loop
        )

    def route_user_message(self, user_message: str, is_voice: bool = False):
        """
        Smart intent router that routes coding tasks to NVIDIA NIM API and general tasks to Gemini.
        """
        try:
            from core.intent_router import is_coding_task
            from core.nvidia_client import ask_nvidia
            from actions.model_switcher import load_model_preference
            
            pref = load_model_preference()
            routing_mode = pref.get("routing_mode", "auto")
            
            is_code = False
            if routing_mode == "nvidia":
                is_code = True
            elif routing_mode == "gemini":
                is_code = False
            else:  # auto
                is_code = is_coding_task(user_message)
                
            if is_code:
                source = "NVIDIA"
                if hasattr(self.ui, "set_router_badge"):
                    self.ui.set_router_badge("NVIDIA")
                    
                print(f"[Router] '{user_message[:40]}...' -> handled by {source}")
                logger.info("[Router] '%s...' -> handled by %s", user_message[:40], source)
                
                # Interrupt Gemini if vocal query
                if is_voice:
                    self._trigger_immediate_interruption()
                    
                # Run NVIDIA client in background thread to keep event loop responsive
                def run_nvidia():
                    try:
                        resp = ask_nvidia(
                            prompt=user_message,
                            system_prompt="You are IP Prime's coding engine. Give clean, well-commented code with brief explanations."
                        )
                        self.ui.write_log(f"IP Prime (NVIDIA): {resp}")
                        self.speak(resp)
                    except Exception as err:
                        logger.error("NVIDIA NIM query failed: %s", err)
                        self.ui.write_log(f"SYS: NVIDIA routing failure: {err}")
                        self.speak(f"NVIDIA API request failed, sir. {err}")
                
                threading.Thread(target=run_nvidia, daemon=True, name="NvidiaQueryThread").start()
                
            else:
                source = "Gemini"
                if hasattr(self.ui, "set_router_badge"):
                    self.ui.set_router_badge("Gemini")
                    
                print(f"[Router] '{user_message[:40]}...' -> handled by {source}")
                logger.info("[Router] '%s...' -> handled by %s", user_message[:40], source)
                
                if not is_voice:
                    # For text, send to the new 6-Layer Brain
                    try:
                        if hasattr(self, "autonomous_core") and hasattr(self.autonomous_core, "brain"):
                            brain_response = self.autonomous_core.brain.process_input(user_message)
                            self.ui.write_log(f"IP Prime (Brain): {brain_response}")
                            self.speak(brain_response)
                        else:
                            # Fallback if brain isn't loaded
                            asyncio.run_coroutine_threadsafe(
                                self.session.send_realtime_input(text=user_message),
                                self._loop
                            )
                    except Exception as e:
                        logger.error(f"Brain processing failed: {e}")
                        self.ui.write_log(f"SYS: Brain processing failure: {e}")
                else:
                    # For voice, Gemini has already processed the audio, so do nothing.
                    pass
                    
        except Exception as e:
            logger.error("Error in intent routing pipeline: %s", e)
            if not is_voice:
                asyncio.run_coroutine_threadsafe(
                    self.session.send_realtime_input(text=user_message),
                    self._loop
                )

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def _convert_to_gemini_schema(self, schema):
        if not isinstance(schema, dict):
            return schema
        res = {}
        for k, v in schema.items():
            if k.startswith("$") or k == "additionalProperties":
                continue
            if k == "type" and isinstance(v, str):
                res[k] = v.upper()
            elif isinstance(v, dict):
                res[k] = self._convert_to_gemini_schema(v)
            elif isinstance(v, list):
                res[k] = [self._convert_to_gemini_schema(item) if isinstance(item, dict) else item for item in v]
            else:
                res[k] = v
        return res

    def _realtime_settings(self) -> dict:
        try:
            from prime_platform.config import load_prime_config
            return load_prime_config().get("realtime", {}) or {}
        except Exception:
            return {}

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        rt = self._realtime_settings()
        lean = bool(rt.get("lean_prompt", True))
        session_turns = int(rt.get("session_turns_in_prompt", 6 if lean else 12))

        cache_ttl = 45.0
        now_ts = time.time()
        if self._prompt_cache and (now_ts - self._prompt_cache[0]) < cache_ttl:
            return self._prompt_cache[1]

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        session_str = format_session_for_prompt(max_turns=session_turns)
        sys_prompt = _load_system_prompt()

        try:
            from actions.humanoid_brain import get_rolling_mood
            current_mood = get_rolling_mood()
            if current_mood != "neutral":
                mood_prompt = (
                    f"\n==================================================\n"
                    f"❤️ [HUMANOID EMOTION ENGINE ACTIVE]\n"
                    f"Pratik Sir is currently feeling: {current_mood.upper()}.\n"
                )
                if current_mood == "tired":
                    mood_prompt += (
                        "He is tired/stressed right now. Be extremely empathetic, warm, supportive, and kind. "
                        "Keep your voice low-key, calm, and offer to take load off him. Suggest "
                        "breaks naturally. Use Hinglish fillers like 'Hmm Sir...', 'Arey koi baat nahi Sir...'."
                    )
                elif current_mood == "happy":
                    mood_prompt += (
                        "He is happy/excited. Match his high energy and enthusiasm! Use enthusiastic "
                        "expressions like 'Arey waah Sir!', 'Wah, kya baat hai!' to celebrate with him."
                    )
                elif current_mood == "sad":
                    mood_prompt += (
                        "He is sad/down. Show deep concern, be comforting, supportive, and tell him "
                        "that you are there to help him. Be a true buddy."
                    )
                elif current_mood == "energetic":
                    mood_prompt += (
                        "He is in a high-energy building/coding state! Be crisp, highly productive, "
                        "collaborative, fast, and excited to get things done. Use 'Chalo Sir, fatfat karte hain!'."
                    )
                mood_prompt += "\n==================================================\n"
                sys_prompt = mood_prompt + sys_prompt
        except Exception as me_err:
            print(f"[HumanoidBrain] Prompt emotion integration error: {me_err}")

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        if session_str:
            parts.append(session_str)
        last_sess = format_last_session_for_prompt()
        if last_sess:
            parts.append(last_sess)
        try:
            from prime_platform.infinite_memory import format_infinite_context_for_prompt
            inf = format_infinite_context_for_prompt()
            if inf:
                parts.append(inf)
        except Exception:
            pass
        parts.append(sys_prompt)

        # MCP tools (cached once — reconnect was re-scanning servers every time)
        if self._mcp_tools_cache is None:
            mcp_declarations = []
            try:
                from actions.mcp_client import MCPClientManager
                mcp_mgr = MCPClientManager()
                for t in mcp_mgr.get_all_tools():
                    s_name = t.get("server_name")
                    t_name = t.get("name").replace("-", "_")
                    desc = t.get("description", "")
                    params = t.get("inputSchema", {})
                    gemini_params = self._convert_to_gemini_schema(params)
                    mcp_declarations.append({
                        "name": f"mcp__{s_name}__{t_name}",
                        "description": f"[MCP Server: {s_name}] {desc}",
                        "parameters": gemini_params,
                    })
            except Exception as e:
                print(f"[IP PRIME] Error formatting MCP tool declarations: {e}")
            self._mcp_tools_cache = mcp_declarations

        all_declarations = TOOL_DECLARATIONS + (self._mcp_tools_cache or [])

        connect_config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": all_declarations}],
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Charon"
                    )
                )
            ),
        )
        self._prompt_cache = (now_ts, connect_config)
        return connect_config

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[IP PRIME] 🔧 {name}  {args}")
        self.ui.set_state("PROCESSING")

        try:
            from prime_platform.energy_metrics import record_tool_call
            record_tool_call(name)
        except Exception:
            pass

        # Route MCP tool calls
        if name.startswith("mcp__"):
            parts = name.split("__")
            if len(parts) >= 3:
                server_name = parts[1]
                actual_tool_name = parts[2]
                
                # Check for original tool name (mapping back underscores to hyphens if needed)
                try:
                    from actions.mcp_client import MCPClientManager
                    mcp_mgr = MCPClientManager()
                    conn = mcp_mgr.connections.get(server_name)
                    if conn:
                        for t in conn.tools:
                            orig = t.get("name")
                            if orig.replace("-", "_") == actual_tool_name:
                                actual_tool_name = orig
                                break
                except Exception:
                    pass

                _thought_msg = f"Routing request to MCP server '{server_name}' using tool '{actual_tool_name}'..."
                if hasattr(self.ui, "write_thought"):
                    self.ui.write_thought(_thought_msg)
                self.ui.write_log(f"SYS: {_thought_msg}")

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: MCPClientManager().execute_tool(server_name, actual_tool_name, args)
                )

                if not self.ui.muted:
                    self.ui.set_state("LISTENING")

                print(f"[IP PRIME] 📤 {name} → {str(result)[:80]}")
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": result}
                )

        print(f"[IP PRIME] 🔧 {name}  {args}")
        self.ui.set_state("PROCESSING")
        # NLA Thought Stream: broadcast tool initiation to HUD
        _thought_labels = {
            "browser_control":   "Initialising stealth browser neural pathway...",
            "computer_control":  "Activating visual desktop control interface...",
            "orchestrated_coder":"Engaging parallel coder orchestration engine...",
            "code_helper":       "Synthesising code solution from knowledge base...",
            "dev_agent":         "Autonomous developer agent online...",
            "file_controller":   "Navigating file system structure...",
            "file_processor":    "Processing document through neural pipeline...",
            "web_search":        "Routing query through deep web search vectors...",
            "design_extractor":  "Extracting design language tokens and packaging AI skill...",
            "screen_process":    "Visual perception module scanning screen state...",
            "desktop_control":   "Desktop interaction pathway engaged...",
            "agent_task":        "Dispatching autonomous background task agent...",
            "send_message":      "Composing and routing communication payload...",
            "prime_local_first": "Scanning local-first neural pathways (Ollama)...",
            "prime_infinite_memory": "Querying infinite memory archive...",
            "prime_energy_dashboard": "Loading energy and cost telemetry...",
            "prime_messaging": "Routing message across comms hub...",
            "prime_homelab": "Interfacing with homelab Docker grid...",
            "prime_media": "Scanning media discovery vectors...",
            "prime_writing": "Engaging advanced writing synthesis...",
            "prime_gesture_control": "Activating hand motion gesture interface...",
            "prime_dashboard": "Launching advanced monitoring dashboard...",
            "prime_audit":     "Running deep security and quality audit scan...",
            "prime_watcher":   "Activating live file watcher daemon...",
        }
        _thought_text = _thought_labels.get(name, f"Neural pathway activated for task: '{name}'")
        if hasattr(self.ui, "write_thought"):
            self.ui.write_thought(_thought_text)

        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
                try:
                    import pyperclip
                    pyperclip.copy(value)
                    print(f"[Clipboard] 📋 Note copied to clipboard: {value}")
                except Exception as ce:
                    print(f"[Clipboard] Failed to copy note to clipboard: {ce}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        loop   = asyncio.get_event_loop()
        result = "Done."

        from core.tool_dispatcher import dispatch_tool
        result = await dispatch_tool(name, args, self.ui, self.speak, loop)
        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[IP PRIME] 📤 {name} → {str(result)[:80]}")
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    def _trigger_immediate_interruption(self):
        if hasattr(self, "audio_playback_queue") and self.audio_playback_queue:
            while not self.audio_playback_queue.empty():
                try:
                    self.audio_playback_queue.get_nowait()
                except Exception:
                    break
        self.set_speaking(False)
        self._buffering_interruption = True
        self.ui.write_log("SYS: Vocal interruption detected. Stopped speaking.")

    async def _listen_audio(self):
        print("[IP PRIME] 🎤 Mic started")
        loop = asyncio.get_event_loop()
        self._muted_cache = False

        # Cache interruption settings ONCE here — NOT inside the audio callback
        # (callback fires 16,000x/sec; reading config file there caused stutter)
        _rt = self._realtime_settings()
        _disable_interruption = bool(_rt.get("disable_voice_interruption", True))
        _threshold = int(_rt.get("interruption_threshold", 2500))
        mic_block = int(_rt.get("mic_chunk_size", CHUNK_SIZE))

        def callback(indata, frames, time_info, status):
            if self._tool_active:
                return
            with self._speaking_lock:
                ip_ray_speaking = self._is_speaking
            if ip_ray_speaking:
                if not self._muted_cache:
                    if not _disable_interruption:
                        audio_samples = indata.flatten()
                        rms = np.sqrt(np.mean(audio_samples.astype(np.float64) ** 2))
                        if rms > _threshold:
                            loop.call_soon_threadsafe(self._trigger_immediate_interruption)
                    if self._buffering_interruption:
                        if not self.out_queue.full():
                            data = indata.tobytes()
                            loop.call_soon_threadsafe(
                                self.out_queue.put_nowait,
                                {"data": data, "mime_type": "audio/pcm"}
                            )
            elif not self._muted_cache:
                if not self.out_queue.full():
                    data = indata.tobytes()
                    loop.call_soon_threadsafe(
                        self.out_queue.put_nowait,
                        {"data": data, "mime_type": "audio/pcm"}
                    )
        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=mic_block,
                callback=callback,
            ):
                print("[IP PRIME] 🎤 Mic stream open")
                while True:
                    try:
                        is_muted = self.ui.muted
                        if is_muted != self._muted_cache:
                            self._muted_cache = is_muted
                            if self._wake_word_spotter:
                                if is_muted:
                                    self._wake_word_spotter.resume_listening()
                                else:
                                    self._wake_word_spotter.pause_listening()
                    except Exception:
                        pass
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[IP PRIME] ❌ Mic: {e}")
            raise

    async def _receive_audio(self):
        print("[IP PRIME] 👂 Recv started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        if not self._quiet_mode and not getattr(self, "_buffering_interruption", False):
                            if self._turn_done_event and self._turn_done_event.is_set():
                                self._turn_done_event.clear()
                            self.audio_playback_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt:
                                out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                in_buf.append(txt)
                                txt_l = txt.lower()
                                
                                # Check quiet/wakeup vocal triggers
                                if "prime quiet" in txt_l or "prime quite" in txt_l or "chup ho jao" in txt_l or "chup hojao" in txt_l:
                                    self._quiet_mode = True
                                    self.ui.write_log("SYS: Quiet Mode activated via voice.")
                                    self.speak("Entering quiet mode, sir. I will remain silent until you say 'prime wakeup'.")
                                elif "prime wakeup" in txt_l or "prime wake up" in txt_l or "wake up prime" in txt_l:
                                    if self._quiet_mode:
                                        self._quiet_mode = False
                                        self.ui.write_log("SYS: Quiet Mode deactivated via voice.")
                                        play_sfx("startup")
                                        self.speak("I am awake and listening, sir!")
                                
                                if "full screen" in txt_l or "fullscreen" in txt_l:
                                    self.ui.write_log("SYS: Vocal fullscreen trigger detected.")
                                    self.ui.set_fullscreen(True)
                                elif "exit" in txt_l:
                                    self.ui.write_log("SYS: Vocal exit fullscreen trigger detected.")
                                    self.ui.set_fullscreen(False)

                        if sc.turn_complete:
                            if self._turn_done_event:
                                self._turn_done_event.set()

                            full_in = " ".join(in_buf).strip()
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            out_buf = []

                            self.audio_playback_queue.put_nowait(None)
                            if not self._quiet_mode:
                                if full_in:
                                    self.ui.write_log(f"You: {full_in}")
                                    self.route_user_message(full_in, is_voice=True)
                                if full_out:
                                    self.ui.write_log(f"IP Prime: {full_out}")
                                if full_in or full_out:
                                    u, a = full_in, full_out
                                    def run_logs_and_mood():
                                        append_session_turn(u, a)
                                        if u:
                                            try:
                                                from actions.humanoid_brain import track_user_mood
                                                track_user_mood(u)
                                            except Exception:
                                                pass
                                    threading.Thread(
                                        target=run_logs_and_mood,
                                        daemon=True,
                                    ).start()

                    if response.tool_call:
                        self._tool_active = True
                        while not self.out_queue.empty():
                            try: self.out_queue.get_nowait()
                            except asyncio.QueueEmpty: break
                        try:
                            play_sfx("tool_start")
                            tasks = [self._execute_tool(fc) for fc in response.tool_call.function_calls]
                            fn_responses = await asyncio.gather(*tasks)
                            play_sfx("tool_done")
                            await self.session.send_tool_response(
                                function_responses=list(fn_responses)
                            )
                        finally:
                            self._tool_active = False
        except Exception as e:
            print(f"[IP PRIME] ❌ Recv: {e}")
            traceback.print_exc()
            raise

    def _play_audio(self):
        print("[IP PRIME] Play thread started")
        # Cache settings ONCE at thread start — NOT per chunk
        rt = self._realtime_settings()
        play_block = int(rt.get("play_buffer_samples", PLAY_BUFFER_SAMPLES))
        gain = float(rt.get("voice_gain", 1.8))

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=play_block,
        )
        stream.start()

        try:
            while True:
                chunk = self.audio_playback_queue.get()
                if chunk is None:
                    self.set_speaking(False)
                    if self._turn_done_event:
                        self._loop.call_soon_threadsafe(self._turn_done_event.clear)

                    # Flush deferred text commands
                    if self._text_interruption_buffer:
                        combined_text = " ".join(self._text_interruption_buffer)
                        self._text_interruption_buffer.clear()
                        print(f"[IP PRIME] 📝 Flushing buffered text: '{combined_text}'")
                        coro = self.session.send_realtime_input(text=combined_text)
                        asyncio.run_coroutine_threadsafe(coro, self._loop)

                    self._buffering_interruption = False
                    continue

                self.set_speaking(True)
                stream.write(self._amplify_pcm(chunk, gain))
        except Exception as e:
            print(f"[IP PRIME] ❌ Play thread error: {e}")
        finally:
            self.set_speaking(False)
            self._buffering_interruption = False
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    async def run(self):
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        while True:
            try:
                print("[IP PRIME] 🔌 Connecting...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    import queue
                    self.audio_playback_queue = queue.Queue()
                    self.out_queue      = asyncio.Queue(maxsize=100)
                    self._turn_done_event = asyncio.Event()

                    print("[IP PRIME] ✅ Connected.")
                    self._force_welcome = False
                    self._connect_count += 1

                    play_sfx("startup")
                    self.ui.write_log("SYS: IP PRIME online — listening.")
                    self.ui.write_thought("Ready — speak anytime")
                    self.ui.set_state("LISTENING")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    threading.Thread(target=self._play_audio, daemon=True).start()
                    
                    try:
                        from actions.chronos_routines import ChronosRoutines
                        ChronosRoutines.instance().start(player=self)
                    except Exception as err:
                        print(f"[IP PRIME] Chronos startup error: {err}")
                        
                    tg.create_task(self._send_startup_welcome())

            except Exception as e:
                print(f"[IP PRIME] ⚠️ {e}")
                traceback.print_exc()
            self.set_speaking(False)
            self.ui.set_state("THINKING")
            print("[IP PRIME] 🔄 Reconnecting in 3s...")
            await asyncio.sleep(3)

def _alarm_checker_loop(ui):
    import json
    import time
    
    base_dir = get_base_dir()
    alarm_file = base_dir / "config" / "alarms.json"
    
    print("[IP PRIME] ⏰ Alarm checker loop online.")
    last_triggered_minute = ""
    
    while True:
        try:
            now_min = time.strftime("%H:%M")
            if now_min != last_triggered_minute:
                if alarm_file.exists():
                    try:
                        alarms = json.loads(alarm_file.read_text(encoding="utf-8"))
                    except Exception:
                        alarms = {}
                    
                    changed = False
                    for aid, details in list(alarms.items()):
                        if details.get("active", True) and details.get("time") == now_min:
                            print(f"[Alarm] ⏰ Triggered: {details.get('message')}")
                            ui.write_log(f"⏰ ALARM TRIGGERED: {details.get('message')}")
                            play_sfx("alarm")
                            
                            details["active"] = False
                            changed = True
                            last_triggered_minute = now_min
                            
                    if changed:
                        alarm_file.write_text(json.dumps(alarms, indent=4), encoding="utf-8")
        except Exception as e:
            print(f"[Alarm Checker Error] {e}")
            
        time.sleep(10)

def main():
    import atexit

    try:
        from prime_platform.ip_given_workspace import ensure_workspace, persist_root_to_config
        ensure_workspace()
        persist_root_to_config()
        print("[IP PRIME] Workspace ready: C:\\Users\\thora\\Downloads\\IP Given")
    except Exception as e:
        print(f"[IP PRIME] Workspace init: {e}")

    atexit.register(save_shutdown_summary)
    ui = IPRayUI("assets/logo.png")

    def runner():
        ui.wait_for_api_key()
        
        # Start IRIS-AI background capabilities after UI is ready (reduces startup lag)
        def _start_background():
            try:
                from actions import ghost_coder, smart_drop_zone
                ghost_coder.run_in_background()
                smart_drop_zone.run_in_background()
            except ImportError as e:
                ui.write_log(f"SYS WARNING: Background agents failed to load - {e}")
            try:
                from actions.auto_indexer import AutoIndexerThread
                indexer = AutoIndexerThread(interval_seconds=300)
                indexer.start()
                ui.write_log("SYS: Automated background semantic indexer online.")
            except Exception as e:
                print(f"[IP PRIME] Failed to start AutoIndexerThread: {e}")
            try:
                from actions.file_classifier import FileClassifierThread
                classifier = FileClassifierThread(check_interval_seconds=15)
                classifier.start()
                ui.write_log("SYS: Automated downloads file classifier online.")
            except Exception as e:
                print(f"[IP PRIME] Failed to start FileClassifierThread: {e}")
        threading.Timer(8.0, _start_background).start()
        
        ip_ray = IPRayLive(ui)
        try:
            asyncio.run(ip_ray.run())
        except KeyboardInterrupt:
            print("\n🔴 Shutting down...")
        finally:
            save_shutdown_summary()

    threading.Thread(target=runner, daemon=True).start()
    threading.Thread(target=lambda: _alarm_checker_loop(ui), daemon=True, name="AlarmCheckerThread").start()
    ui.root.mainloop()
    save_shutdown_summary()

if __name__ == "__main__":
    main()

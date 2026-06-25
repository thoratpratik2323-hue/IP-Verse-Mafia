import os
import sys
import speech_recognition as sr
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def transcribe_audio_locally(audio_source) -> str:
    """
    Transcribes audio data locally using OpenAI Whisper (tiny model).
    Takes a speech_recognition AudioData object or a path to a WAV file.
    """
    r = sr.Recognizer()
    audio_data = None
    
    if isinstance(audio_source, (str, Path)):
        p = Path(audio_source)
        if not p.exists():
            return f"Audio file not found: {p}"
        with sr.AudioFile(str(p)) as source:
            audio_data = r.record(source)
    else:
        # Assume it is already an AudioData object
        audio_data = audio_source

    if not audio_data:
        return "No audio data to transcribe, sir."

    try:
        # recognize_whisper runs Whisper locally.
        # It downloads the 'tiny' model (~70MB) automatically on first run to ~/.cache/whisper.
        print("[Local STT] Transcribing audio using local Whisper (tiny)...")
        text = r.recognize_whisper(audio_data, model="tiny")
        return text.strip()
    except ImportError:
        print("[Local STT] ImportError: openai-whisper or torch is not installed. Trying Google Web Speech API as fallback...")
        try:
            text = r.recognize_google(audio_data)
            return text.strip()
        except Exception as ex:
            return f"ERROR_DEPENDENCY: Local Whisper STT requires openai-whisper. Please run 'pip install openai-whisper torch'. Google fallback also failed: {ex}"
    except Exception as e:
        print(f"[Local STT] Local Whisper transcription failed: {e}. Trying Google Web Speech API as fallback...")
        try:
            text = r.recognize_google(audio_data)
            return text.strip()
        except Exception as ex:
            return f"ERROR_FAILED: Local Whisper transcription failed: {e}. Google fallback also failed: {ex}"

def listen_and_transcribe_local() -> str:
    """Listens to microphone and transcribes locally using Whisper."""
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    
    with sr.Microphone() as source:
        print("[Local STT] Listening from microphone...")
        try:
            audio = r.listen(source, timeout=5.0, phrase_time_limit=10.0)
            return transcribe_audio_locally(audio)
        except sr.WaitTimeoutError:
            return "ERROR_TIMEOUT: Listening timed out."
        except Exception as e:
            return f"ERROR_FAILED: Failed to record microphone audio: {e}"

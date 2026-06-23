import os
import re
import time
import asyncio
import edge_tts

def clean_old_voices(static_dir):
    """Keep storage at 0MB by deleting voice caches older than 30 seconds."""
    try:
        now = time.time()
        if os.path.exists(static_dir):
            for f in os.listdir(static_dir):
                fpath = os.path.join(static_dir, f)
                is_target = f.startswith("voice_") or f.startswith("ip_prime_edge_") or f.startswith("ip_prime_tts_")
                if os.path.isfile(fpath) and is_target and os.stat(fpath).st_mtime < now - 30:
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
    except Exception:
        pass

async def _synthesize(text: str, voice_name: str, filepath: str):
    communicate = edge_tts.Communicate(text, voice_name, rate="+10%", volume="+100%", pitch="+0Hz")
    await communicate.save(filepath)

def generate_speech(text: str, voice_name: str = "en-GB-RyanNeural", filepath: str = None) -> bool:
    """Synthesize speech using Microsoft Cognitive edge-tts voice."""
    if not filepath:
        return False
        
    temp_filepath = filepath + ".tmp"
    
    # Remove markdown code blocks (``` ... ```) so speech doesn't read code out loud
    clean_text = re.sub(r'```.*?```', ' [Code block omitted] ', text, flags=re.DOTALL)
    # Remove emojis and special markers
    clean_text = re.sub(r'[\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDC00-\uDFFF]', '', clean_text)
    
    try:
        asyncio.run(_synthesize(clean_text, voice_name, temp_filepath))
        if os.path.exists(temp_filepath):
            if os.path.exists(filepath):
                try: os.remove(filepath)
                except: pass
            os.rename(temp_filepath, filepath)
            return True
    except Exception as e:
        print(f"[edge-tts Helper Error] {e}")
        if os.path.exists(temp_filepath):
            try: os.remove(temp_filepath)
            except: pass
    return False

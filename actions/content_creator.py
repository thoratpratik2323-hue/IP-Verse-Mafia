import logging
import json
import time
import mss
import shutil
from pathlib import Path
from PIL import Image
from google import genai
from memory.encryption import encrypt_string, decrypt_string
from actions.model_switcher import get_preferred_model

BASE_DIR = Path(__file__).resolve().parent.parent
IDEAS_PATH = BASE_DIR / "data" / "content_ideas.enc"
TUTORIAL_SESSION_PATH = BASE_DIR / "data" / "tutorial_session.enc"
OUTPUT_DIR = Path.home() / "Downloads" / "sat output" / "Tutorials"

def _load_session() -> dict:
    if not TUTORIAL_SESSION_PATH.exists():
        return {}
    try:
        raw = TUTORIAL_SESSION_PATH.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        dec = decrypt_string(raw)
        return json.loads(dec)
    except Exception:
        return {}

def _save_session(data: dict):
    TUTORIAL_SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        raw_json = json.dumps(data, indent=2, ensure_ascii=False)
        TUTORIAL_SESSION_PATH.write_text(encrypt_string(raw_json), encoding="utf-8")
    except Exception as _exc:  # noqa: BLE001
        logging.debug("[%s] Suppressed: %s", __name__, _exc)

def content_creator(parameters: dict, player=None) -> str:
    action = parameters.get("action", "generate_ideas").lower().strip()
    topic = parameters.get("topic", "").strip()
    step_desc = parameters.get("step_description", "").strip()
    
    try:
        from main import _get_api_key
        api_key = _get_api_key()
    except Exception:
        return "I need a Gemini API key to run content creator tools, sir."
        
    client = genai.Client(api_key=api_key)
    
    if action == "generate_ideas":
        if not topic:
            return "Please provide a topic for content generation, sir."
            
        prompt = (
            f"Generate a list of 10 highly engaging, viral YouTube video ideas about '{topic}'. "
            "For each idea, include a catchy clickbait-style title, a 2-sentence description/hook, "
            "and three suggested tags. Answer in developer-friendly Hinglish style."
        )
        try:
            model = get_preferred_model("fast")
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )
            
            ideas_text = response.text.strip()
            
            # Save encrypted ideas
            existing_ideas = []
            if IDEAS_PATH.exists():
                try:
                    dec = decrypt_string(IDEAS_PATH.read_text(encoding="utf-8"))
                    existing_ideas = json.loads(dec)
                except Exception as _exc:  # noqa: BLE001
                    logging.debug("[%s] Suppressed: %s", __name__, _exc)
            
            existing_ideas.append({
                "topic": topic,
                "timestamp": time.time(),
                "ideas": ideas_text
            })
            
            IDEAS_PATH.parent.mkdir(parents=True, exist_ok=True)
            IDEAS_PATH.write_text(encrypt_string(json.dumps(existing_ideas, indent=2)), encoding="utf-8")
            
            # Also save a human-readable copy in sat output/Ideas
            readable_dir = Path.home() / "Downloads" / "sat output" / "Ideas"
            readable_dir.mkdir(parents=True, exist_ok=True)
            slug = "".join(c for c in topic if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_")
            readable_file = readable_dir / f"ideas_{slug}.txt"
            readable_file.write_text(ideas_text, encoding="utf-8")
            
            return (
                f"### 🎬 [CONTENT IDEAS] Topic: {topic}\n\n"
                f"{ideas_text}\n\n"
                f"*(Ideas have been saved to your Downloads/sat output/Ideas folder and encrypted on disk, sir!)*"
            )
        except Exception as e:
            return f"Failed to generate ideas: {e}, sir."
            
    elif action == "start_tutorial":
        if not topic:
            return "Please specify a topic or title for the tutorial, sir."
            
        session = {
            "topic": topic,
            "steps": [],
            "start_time": time.time()
        }
        _save_session(session)
        return f"Started tutorial builder for: '{topic}'. Use action='add_tutorial_step' to document each step, sir."
        
    elif action == "add_tutorial_step":
        session = _load_session()
        if not session:
            return "No active tutorial session found, sir. Start one with action='start_tutorial'."
            
        if not step_desc:
            return "Please provide a description of this step, sir."
            
        step_num = len(session["steps"]) + 1
        
        # Capture screenshot for this step
        screenshots_dir = BASE_DIR / "data" / "tutorial_screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        img_path = screenshots_dir / f"step_{step_num}_{int(time.time())}.png"
        
        try:
            with mss.MSS() as sct:
                sct.shot(output=str(img_path))
        except Exception as e:
            img_path = None
            
        session["steps"].append({
            "step_number": step_num,
            "description": step_desc,
            "screenshot_path": str(img_path) if img_path else None
        })
        _save_session(session)
        
        return f"Successfully added Step {step_num}: '{step_desc}' (with screenshot), sir."
        
    elif action == "finish_tutorial":
        session = _load_session()
        if not session or not session.get("steps"):
            return "No active tutorial steps found to compile, sir."
            
        topic = session["topic"]
        steps = session["steps"]
        
        # Build prompt for Gemini combining steps and images
        contents = [
            "You are a professional technical writer and screen-to-tutorial builder. "
            "Compile these recorded user steps into a beautiful, complete, professional step-by-step markdown tutorial. "
            "Write it in helpful, developer-friendly Hinglish. "
            "In corporate headings, code blocks, alerts, and reference screenshots using markdown image links pointing to their local image files. "
            f"The tutorial topic is: {topic}\n\n"
        ]
        
        # Set up output directories
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        slug = "".join(c for c in topic if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_")
        tutorial_images_dir = OUTPUT_DIR / "images" / slug
        tutorial_images_dir.mkdir(parents=True, exist_ok=True)
        
        for s in steps:
            s_num = s["step_number"]
            s_desc = s["description"]
            s_img = s.get("screenshot_path")
            
            contents.append(f"Recorded Step {s_num} Description: {s_desc}\n")
            
            if s_img and Path(s_img).exists():
                # Copy to output images folder
                dest_img = tutorial_images_dir / f"step_{s_num}.png"
                shutil.copy(s_img, dest_img)
                # Pass PIL image to Gemini
                try:
                    pil_img = Image.open(s_img)
                    contents.append(pil_img)
                except Exception as _exc:  # noqa: BLE001
                    logging.debug("[%s] Suppressed: %s", __name__, _exc)
                contents.append(f"Screenshot for step {s_num} is referenced as: ./images/{slug}/step_{s_num}.png\n")
        
        try:
            model = get_preferred_model("vision")
            response = client.models.generate_content(
                model=model,
                contents=contents
            )
            
            tutorial_md = response.text.strip()
            
            output_file = OUTPUT_DIR / f"{slug}.md"
            output_file.write_text(tutorial_md, encoding="utf-8")
            
            # Clean up session files and temp screenshots
            try:
                TUTORIAL_SESSION_PATH.unlink(missing_ok=True)
                temp_screenshots_dir = BASE_DIR / "data" / "tutorial_screenshots"
                if temp_screenshots_dir.exists():
                    shutil.rmtree(temp_screenshots_dir)
            except Exception as _exc:  # noqa: BLE001
                logging.debug("[%s] Suppressed: %s", __name__, _exc)
                
            return (
                f"### 📝 [TUTORIAL COMPILED] Title: {topic}\n"
                f"Successfully compiled step-by-step tutorial, sir!\n"
                f"Saved to: [Downloads/sat output/Tutorials/{slug}.md](file:///{output_file.as_posix()})"
            )
        except Exception as e:
            return f"Failed to compile tutorial: {e}, sir."
            
    else:
        return "Unknown content creator action, sir."

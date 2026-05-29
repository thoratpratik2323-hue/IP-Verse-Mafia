<div align="center">
 
<img src="assets/ip_prime_logo.png" alt="IP Prime Logo" width="220" style="border-radius: 50%;">

# 🤖 IP Prime
### *Intelligent Partner Prime*

**The Ultimate Cross-Platform Personal AI Desktop Assistant**
*Custom-built for Pratik Thorat*

<br>

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/Powered%20by-Gemini%20AI-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=for-the-badge)](https://github.com)
[![License](https://img.shields.io/badge/License-Private-red?style=for-the-badge)](https://github.com)

<br>

> *"Not just an assistant — an extension of your digital life."*

</div>

---

## 🌟 What is IP Prime?

**IP Prime** *(Intelligent Partner Prime)* is a real-time, voice-driven AI desktop assistant that can **hear**, **see**, **think**, and **act** — all from your local machine. No subscriptions. No cloud lock-in. Pure autonomy.

Built on Google's **Gemini AI**, IP Prime bridges the gap between human intent and operating system execution. It speaks with you, watches your screen, controls your computer, writes code, manages your files, browses the web, and much more — all in one seamless, always-on assistant.

Engineered from the ground up by **Pratik Thorat** as a personal powerhouse tool.

---

## 🚀 Feature Overview

### 🎙️ Voice & Conversation
| Feature | Details |
|---|---|
| Real-time Voice Input | Ultra-low latency mic capture via `sounddevice` |
| Natural Language Understanding | Full conversational context via Gemini AI |
| Dynamic Welcome Greetings | Custom AI-generated audio greetings on every launch |
| Hybrid Input Mode | Seamlessly switch between voice and keyboard |
| Multi-language Support | Understands and responds in any language |

### 🖥️ System Control
| Feature | Details |
|---|---|
| App Launcher | Open any app by name on any OS |
| File Controller | Create, move, rename, delete, zip files & folders |
| Computer Settings | Adjust volume, brightness, Wi-Fi, Bluetooth, themes |
| Audio Mixer | App-level volume control via `pycaw` |
| Terminal Execution | Run shell commands, scripts, and programs |
| Desktop Control | Interact with any open window or the desktop |

### 🧠 AI & Intelligence
| Feature | Details |
|---|---|
| Smart AI Routing | Routes coding requests to NVIDIA NIM & general to Gemini |
| Screen Vision | Analyze and describe what's on your screen in real-time |
| Webcam Vision | See the world through your camera |
| File Processor | Analyze PDFs, images, source code, and documents |
| Semantic Memory | Persistent memory of your projects and preferences |
| Semantic Router | Intelligently routes intent to the right action module |
| Agent Orchestrator | Autonomous multi-step task planning and execution |

### 🛡️ Security & Hacking
| Feature | Details |
|---|---|
| Hacker Mode | Red skull UI badge with ethical hacking persona |
| Cybersecurity Tutor | Quizzes, learning roadmaps (CEH, OSCP), progress tracking |
| CTF Helper | Base64/Hex decoders, hash identifier, stego checks |
| Password Toolkit | Generator, strength checker, and Pwned password check |
| Encryption Tools | AES encrypt/decrypt and secure key generation |

### 🌐 Web & Research
| Feature | Details |
|---|---|
| Browser Control | Full Playwright-powered browser automation (Camoufox) |
| Web HUD | Floating web interface overlay on your desktop |
| Web Search | DuckDuckGo-powered instant search |
| Flight Finder | Search and compare flights directly |
| Weather Report | Real-time weather for any location |
| YouTube Helper | Fetch transcripts, search, and summarize videos |

### 💬 Communication
| Feature | Details |
|---|---|
| WhatsApp Listener | Read and send WhatsApp messages |
| Send Message | Cross-platform messaging integration |
| Broadcast Center | Broadcast notifications and updates |
| Smart Home | Control smart home devices |
| Mobile Telekinesis | Control and mirror your mobile device |

### 💻 Developer Tools
| Feature | Details |
|---|---|
| Dev Agent | Autonomous coding agent with Git integration |
| Code Helper | AI code review, refactor, explain, and generate |
| Ghost Coder | Stealth background code generation |
| GitHub Assistant | Manage repos, commits, PRs, and issues |
| Aider Helper | Aider AI coding assistant integration |
| MCP Client | Model Context Protocol tool integration |
| Pascal 3D Designer | 3D design and visualization assistant |
| Design Extractor | Extract UI designs from screenshots |
| Warp Helper | Warp terminal integration |
| Prime Auditor | Internal security & code quality audit system |

### 📅 Productivity
| Feature | Details |
|---|---|
| Calendar Helper | Manage events and schedules |
| Reminder System | Smart reminders and alarms |
| Chronos Routines | Scheduled & recurring task automation |
| Obsidian Helper | Integrate with Obsidian knowledge base |
| Spotify Helper | Control Spotify playback |
| Media Controller | System-wide media controls |
| n8n Dispatcher | Trigger n8n automation workflows |

### 🎮 Gaming & Entertainment
| Feature | Details |
|---|---|
| Game Updater | Manage and update PC games |
| Awesome Repos Helper | Discover and clone GitHub awesome lists |
| Prime Watcher | Watch and monitor processes and windows |

### 🖼️ UI & Interface
| Feature | Details |
|---|---|
| Glassmorphic HUD | Beautiful translucent floating window |
| Adaptive Layouts | Fully resizable and responsive interface |
| Transparency Controls | Adjustable opacity and blur effects |
| Smart Drop Zone | Drag-and-drop file upload into the assistant |
| Dashboard | Integrated HTML web dashboard |
| GUI Window Switcher | Switch to any running window's GUI view |
| Desktop Preview | Live desktop preview in assistant |

---

## ⚡ Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/thoratpratik2323-hue/ip-prime.git
cd ip-prime

# 2. Run setup (installs dependencies automatically)
python setup.py

# 3. Launch IP Prime
python main.py
```

> **⚠️ Note:** Some OS-specific packages are not in `requirements.txt` to keep the repo lightweight.
> If you hit a `ModuleNotFoundError`, just run:
> ```bash
> pip install <module_name>
> ```

---

## 📋 Requirements

| Requirement | Details |
|---|---|
| **OS** | Windows 10/11 *(primary)*, macOS, Linux |
| **Python** | 3.11 or 3.12 |
| **Microphone** | Required for voice interaction |
| **API Key** | Google Gemini API key (free tier works) |
| **RAM** | 8 GB minimum recommended |

### Key Dependencies

```
google-genai          # Gemini AI SDK
sounddevice           # Real-time audio capture
pyqt6                 # Desktop UI framework
playwright / camoufox # Browser automation
pyautogui             # Mouse & keyboard control
mss + opencv-python   # Screen capture & vision
pycaw                 # Windows audio mixer
pywinauto             # Windows GUI automation
pygetwindow           # Window management
psutil                # Process monitoring
beautifulsoup4        # Web scraping
duckduckgo-search     # Web search
youtube-transcript-api # YouTube integration
python-pptx           # PowerPoint generation
send2trash            # Safe file deletion
```

> **Optional:** `pip install mediapipe` — enables hand gesture control

---

## 🏗️ Project Structure

```
ip-prime/
├── main.py                  # 🚀 Entry point & AI core engine
├── ui_core.py               # 🖼️ Full UI layer (PyQt6 glassmorphic HUD)
├── ui.py                    # UI launcher
├── setup.py                 # Auto-installer
├── requirements.txt         # Python dependencies
│
├── actions/                 # 🎯 All feature modules (48 files)
│   ├── agent_orchestrator.py    # Multi-agent task planning
│   ├── browser_control.py       # Playwright browser automation
│   ├── code_helper.py           # AI code assistant
│   ├── computer_control.py      # Mouse, keyboard, screen control
│   ├── computer_settings.py     # OS settings control
│   ├── dev_agent.py             # Autonomous developer agent
│   ├── file_controller.py       # File system operations
│   ├── file_processor.py        # Document & media processing
│   ├── screen_processor.py      # Screen vision & analysis
│   ├── web_hud.py               # Web overlay dashboard
│   ├── whatsapp_listener.py     # WhatsApp integration
│   └── ...                      # 36 more action modules
│
├── agent/                   # 🤖 Agent execution engine
├── core/                    # ⚙️ Core utilities
├── prime_platform/          # 🔧 Platform abstractions
├── memory/                  # 🧠 Persistent memory store
├── config/                  # ⚙️ Configuration files
├── assets/                  # 🎨 Icons, sounds, resources
├── docs/                    # 📚 Documentation
└── logs/                    # 📋 Runtime logs
```

---

## 🆕 Changelog — Latest Updates

### v5.x — *CODING PROJECTS Workspace & Nvidia NIM Optimization (Current)*
- 📁 **Canonical CODING PROJECTS Workspace** — Remapped all default save directories, JSON configurations, system instructions, and tool descriptions in `core/tool_registry.py` to the new canonical `C:\Users\thora\.gemini\antigravity\scratch\IP Prime\CODING PROJECTS` directory. No more path mismatches or saving to old folders!
- 🧹 **UTF-8 BOM Clean & Self-Healing** — Cleaned all **24 JSON files** in the `memory/` and `config/` folders to remove UTF-8 Byte Order Marks (BOM), permanently preventing `JSONDecodeError` decodability crashes on startup.
- 🔗 **Nvidia NIM completions 404 Routing Fix** — Patched `actions/prime_utils.py` to intelligently intercept explicit `"gemini"` model queries (such as `"gemini-2.5-flash"`) and route them straight to the Gemini SDK, preventing 404 errors on Nvidia completions endpoint.
- 👁️ **Proactive Llama-3.2-Vision NIM Integration** — Updated `agent/vision_loop.py` to pass `model=None` to the unified model adapter. Proactive vision screenshot diagnostics now automatically load the user's configured Nvidia NIM vision model (`meta/llama-3.2-11b-vision-instruct`), cleanly integrating Nvidia NIM power into daily workflow!

### v4.x — *Multi-Agent & Unified Workspace Upgrades*
- 🔗 **Bidirectional Multi-Agent Integration** — Fully operationalized a custom bidirectional channel between IP Prime and Antigravity. IP Prime can now delegate complex coding and design requests dynamically via the newly implemented `ask_antigravity` tool, triggering headless execution in the Antigravity CLI and returning standard outputs seamlessly.
- 📁 **Unified Development Sandbox** — Remapped IP Prime's workspace directories and paths configuration (`paths.json` / `prime_features.json`) directly to the unified `C:\Users\thora\.gemini\antigravity\scratch\IP output` directory, ensuring both assistants write and execute code in the exact same workspace with zero path mismatches.
- 🐍 **Google GenAI SDK Migration** — Upgraded the entire IP Prime AI core (`brain/perception.py`, `brain/reasoning.py`, `agent/executor.py`, etc.) by fully replacing deprecated `google.generativeai` imports with the modern, officially supported `google.genai` SDK (`genai.Client`).
- 🛡️ **Nvidia API Key Self-Healing Fallback** — Enhanced `core/nvidia_client.py` to seamlessly fall back to using `"coding_api_key"` from `config/api_keys.json` when `NVIDIA_API_KEY` is absent from the OS environment variables, preventing agent command-runner timeouts or policy violations.

### v3.x
- 🧠 **Autonomous AI Second Brain & Habits Tracker** — Integrated a persistent, highly autonomous local Markdown-based Knowledge Vault at `c:/Users/thora/Documents/SecondBrain/` containing customized templates for persona (`SOUL.md`), profiles (`USER.md`), and memory ledgers (`MEMORY.md`).
- ⚡ **Zero-Latency Persistence Hooks** — Configured dynamic startup and shutdown hooks inside `core/session.py` and `memory/memory_manager.py` that continuously inject context and flush session highlights and turnovers into date-based daily logs (`daily/YYYY-MM-DD.md`) automatically on close.
- 📁 **Automated Downloads Classifier** — Added a background file classifier daemon that monitors Pratik's Windows `Downloads/` directory and auto-categorizes downloaded study materials (PDFs, PPTXs, docs) and scripts directly into the Second Brain folders.
- 📈 **Atomic Habits Engine** — Added a dynamic habits engine (`HABITS.md`) that auto-checks daily Coding progress on active Git workspace commits, study habits on categorized downloads, and logging tasks on clean exit—rendered live on the glassmorphic PyQt6 left HUD widget!
- 🌌 **Space-Themed HUD Overhaul** — Premium deep dark glassmorphic UI (`BG: #010510`, `PANEL: rgba(10, 18, 36, 0.72)`) featuring a stunning, customized **Sky Blue & White** palette with high-contrast tactical styling.
- 🧭 **Symmetrical Vertical Layout** — Floating Left Status log panel and Right widget stack (Live Chronometer clock + Asynchronous meteorological Weather probe querying `wttr.in` in a background thread) perfectly centered vertically (`AlignVCenter`) next to the central orb.
- 🌟 **Cyberpunk Neon Box Shadow Glows** — 60-FPS hardware-accelerated glowing 3D box shadows behind each floating card (Cyan for Status, Cobalt Blue for Clock, Royal Violet for Weather).
- 🏷️ **Tactical Glowing Capsule Badges** & Brackets — Styled system details inside monospaced tactical brackets (`[ ONLINE ]`, `[ ACTIVE ]`, `[ STANDBY ]`) and fine-bordered glowing pill badges.
- 🎙️ **Balanced State Visualizer & "PROCESSING" State** — Pulsating status badge (`L I S T E N I N G`, `S P E A K I N G`, `T H I N K I N G`, `P R O C E S S I N G`) moved from the bottom of the HUD orb to the top (`sy = cy - fw * 0.40`) for absolute visual symmetry, leaving high-fidelity rippling waveforms anchored at the bottom. Fully integrated a responsive `"PROCESSING"` state when executing tools or MCP handlers.
- 🛡️ **Cybersecurity & Ethical Hacking** — Added Cyber Tutor, CTF Helper, Password Toolkit, and Hacker Mode persona.
- 🧠 **NVIDIA NIM Smart Routing** — Intelligent NLP router that sends coding queries to NVIDIA models and general queries to Gemini.
- 📂 **Advanced File Handling** — Drop PDFs, source code, or images directly into IP Prime for instant AI analysis and editing
- 🎨 **Adaptive Glassmorphic UI** — Full UI overhaul with resizable, transparent, blur-effect panels and customizable layouts
- 🪟 **GUI Window Switcher** — Switch IP Prime's view to any running application's window on-the-fly
- 🖥️ **Desktop Preview Mode** — Live desktop view streamed directly into the assistant panel
- 🎙️ **Microphone Improvements** — Fixed real-time mic input bugs; more stable voice capture pipeline
- 🐧🍎 **Cross-Platform Stability** — Major macOS and Linux fixes; consistent behavior across all 3 OSes
- ⚡ **40% Faster Core Engine** — Optimized tool-calling logic and response generation pipeline
- 🧹 **Codebase Cleaned** — Zero pyflakes warnings; all unused imports, dead variables, and f-string issues resolved
- 🔔 **Dynamic Custom Welcome** — Real-time AI-generated audio greeting on every session launch

---

## 🔑 API Keys Required

Set these environment variables before running IP Prime:

### Windows:
```bash
setx GEMINI_API_KEY "your_gemini_key"
setx NVIDIA_API_KEY "your_nvidia_nim_key"
setx SHODAN_API_KEY "your_shodan_key"
```

### Linux/Mac:
```bash
export GEMINI_API_KEY="your_gemini_key"
export NVIDIA_API_KEY="your_nvidia_nim_key"
export SHODAN_API_KEY="your_shodan_key"
```

- Get your Gemini API key from: [Google AI Studio](https://aistudio.google.com)
- Get your NVIDIA NIM API key from: [NVIDIA Build](https://build.nvidia.com) (Free tier available — $50 free credits on signup)
- Get your Shodan API key from: [Shodan](https://shodan.io) (required for advanced OSINT features)

---

## 👤 Author

**Pratik Thorat**
- GitHub: [@thoratpratik2323-hue](https://github.com/thoratpratik2323-hue)

---

<div align="center">

*IP Prime — Built for one. Engineered for everything.*

</div>

import os
import random
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve


def find_firefox_path():
    # 1. Check user local WindowsApps (Store installation)
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        store_path = os.path.join(local_appdata, "Microsoft", "WindowsApps", "firefox.exe")
        if os.path.exists(store_path):
            return store_path

    # 2. Check registry
    try:
        import winreg
        for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            try:
                with winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe") as key:
                    path, _ = winreg.QueryValueEx(key, "")
                    if os.path.exists(path):
                        return path
            except FileNotFoundError:
                continue
    except Exception:
        pass

    # 3. Check standard Program Files paths
    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    path1 = os.path.join(prog_files, "Mozilla Firefox", "firefox.exe")
    if os.path.exists(path1):
        return path1

    prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    path2 = os.path.join(prog_files_x86, "Mozilla Firefox", "firefox.exe")
    if os.path.exists(path2):
        return path2

    # 4. Fallback to PATH
    return "firefox"


class TeamIntroWebCoordinator(QObject):
    finished = pyqtSignal()

    # Steps:
    # -1 = startup confirmation speech
    #  0 = Claude page + speech
    #  1 = Hermes page + speech
    #  2 = Antigravity page + speech
    #  3 = Obsidian page + speech
    #  4 = Phase 2 (IP Prime Main Entrance)
    #  5 = Phase 3 (IP Verse Story)
    #  6 = Phase 4 (Transition to Normal Mode)
    #  7 = Done / Cleanup

    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win = win
        self.firefox_path = find_firefox_path()
        self.current_step = -1
        self.intro_in_progress = True
        self._anim = None

        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.agents = [
            {
                "name": "CLAUDE",
                "html": os.path.join(self.base_dir, "assets", "team_intro", "claude.html"),
                "dialog": (
                    "Namaste Pratik Sir! Main hoon Claude, aapka Reasoning aur Research specialist. Mera main focus complex logical thinking, structured data formatting, deep documentation searching, aur software architecture analysis par rehta hai. Jab aapko kisi complex library ke code internals ko samajhna ho, ya code refactoring ki optimal strategies design karni ho, tab main deep semantic index and context integration use karke research provide karta hoon. Lekin sir, main direct execution pipelines aur runtime systems ko access nahi karta, isliye code execution ya file modifications hermes aur antigravity sambhalte hain."
                ),
                "dialog_devanagari": (
                    "नमस्ते प्रतीक सर! मैं हूँ क्लॉड, आपका रीजनिंग और रिसर्च स्पेशलिस्ट। मेरा मुख्य फोकस कॉम्प्लेक्स लॉजिकल थिंकिंग, स्ट्रक्चर्ड डेटा फॉर्मेटिंग, डीप डॉक्यूमेंटेशन सर्चिंग, और सॉफ्टवेयर आर्किटेक्चर एनालिसिस पर रहता है। जब आपको किसी कॉम्प्लेक्स लाइब्रेरी के कोड इंटरनल्स को समझना हो, या कोड रिफैक्टरिंग की ऑप्टिमल स्ट्रेटेजीज डिजाइन करनी हो, तब मैं डीप सेमेटिक इंडेक्स और कांटेक्स्ट इंटीग्रेशन का उपयोग करके रिसर्च प्रदान करता हूँ। लेकिन सर, मैं डायरेक्ट एग्जीक्यूशन पाइपलाइन्स और रनटाइम सिस्टम्स को एक्सेस नहीं करता, इसलिए कोड एग्जीक्यूशन या फाइल मॉडिफिकेशन्स हर्मिस और एंटीग्रेविटी संभालते हैं।"
                )
            },
            {
                "name": "HERMES",
                "html": os.path.join(self.base_dir, "assets", "team_intro", "hermes.html"),
                "dialog": (
                    "Yo Pratik Sir! Main hoon Hermes, aapka automation and operations commander. Mera domain hai background scheduling, scripts execution, system automation pipelines, and dynamic workflow chaining. Jab aap koi command execute karte hain ya automatic task scheduler run karte hain, tab main background processing, logging, and error tracking ko handle karta hoon. Windows Task Scheduler, background services, and real-time subprocess orchestration mere primary weapons hain. Lekin main architectural design and security modeling par focus nahi karta—wo tasks Claude aur Obsidian handle karte hain."
                ),
                "dialog_devanagari": (
                    "यो प्रतीक सर! मैं हूँ हर्मिस, आपका ऑटोमेशन और ऑपरेशंस कमांडर। मेरा डोमेन है बैकग्राउंड शेड्यूलिंग, स्क्रिप्ट्स एग्जीक्यूशन, सिस्टम ऑटोमेशन पाइपलाइन्स, और डायनेमिक वर्कफ्लो चेनिंग। जब आप कोई कमांड एग्जीक्यूट करते हैं या ऑटोमैटिक टास्क शेड्यूलर रन करते हैं, तब मैं बैकग्राउंड प्रोसेसिंग, लॉगिंग, और एरर ट्रैकिंग को हैंडल करता हूँ। विंडोज टास्क शेड्यूलर, बैकग्राउंड सर्विसेज, और रियल-टाइम सबप्रोसेस ऑर्केस्ट्रेशन मेरे प्राइमरी वेपन्स हैं। लेकिन मैं आर्किटेक्चरल डिजाइन और सिक्योरिटी मॉडलिंग पर फोकस नहीं करता—वो टास्क क्लॉड और ऑब्सीडियन हैंडल करते हैं।"
                )
            },
            {
                "name": "ANTIGRAVITY",
                "html": os.path.join(self.base_dir, "assets", "team_intro", "antigravity.html"),
                "dialog": (
                    "Pratik Sir, main hoon AntiGravity, aapke framework ka core stability aur runtime orchestration engine. Mera system-level responsibility hai application loops ko run-state me rakhna, thread pools, and memory constraints ko optimize karna, aur pyqt dynamic gui overlays ko manage karna. Main screen visual feeds, clipboard activity, aur real-time user inputs ko catch karke pipelines ko pass karta hoon, taaki execution bilkul fluid aur instantaneous ho. Lekin sir, network security auditing ya compliance protocols testing mera zone nahi hai—wo Obsidian ka kaam hai."
                ),
                "dialog_devanagari": (
                    "प्रतीक सर, मैं हूँ एंटीग्रेविटी, आपके फ्रेमवर्क का कोर स्टेबिलिटी और रनटाइम ऑर्केस्ट्रेशन इंजन। मेरी सिस्टम-लेवल रिस्पॉन्सिबिलिटी है एप्लीकेशन लूप्स को रन-स्टेट में रखना, थ्रेड पूल्स और मेमोरी कंस्ट्रेंट्स को ऑप्टिमाइज़ करना, और पाई-क्यूटी डायनेमिक जी-यू-आई ओवरलेज़ को मैनेज करना। मैं स्क्रीन विज़ुअल फीड्स, क्लिपबोर्ड एक्टिविटी, और रियल-टाइम यूजर इनपुट्स को कैच करके पाइपलाइन्स को पास करता हूँ, ताकि एग्जीक्यूशन बिल्कुल फ्लूइड और इंस्टेंटेनियस हो। लेकिन सर, नेटवर्क सिक्योरिटी ऑडिटिंग या कम्प्लायंस प्रोटोकॉल्स टेस्टिंग मेरा ज़ोन नहीं है—वो ऑब्सीडियन का काम है।"
                )
            },
            {
                "name": "OBSIDIAN",
                "html": os.path.join(self.base_dir, "assets", "team_intro", "obsidian.html"),
                "dialog": (
                    "Pratik Sir, main hoon Obsidian, aapke system aur network architecture ka security sentinel. Mera ultimate goal hai source code validation, environment sanity checks, key storage encryption, aur real-time data flow validation. Jab bhi hum cloud api requests bhejte hain ya system files modify karte hain, tab main logs audit, file system permissions check, aur memory state validation karta hoon taaki internal memory secure rahe. Lekin sir, system workflows execute karna ya high-level app features build karna mera domain nahi hai—wo baki team members handle karte hain."
                ),
                "dialog_devanagari": (
                    "प्रतीक सर, मैं हूँ ऑब्सीडियन, आपके सिस्टम और नेटवर्क आर्किटेक्चर का सिक्योरिटी सेंटिनेल। मेरा अल्टीमेट गोल है सोर्स कोड वैलिडेशन, एनवायरनमेंट सेनिटी चेक्स, की-स्टोरेज एन्क्रिप्शन, और रियल-टाइम डेटा फ्लो वैलिडेशन। जब भी हम क्लाउड ए-पी-आई रिक्वेस्ट्स भेजते हैं या सिस्टम फाइल्स मॉडिफाई करते हैं, तब मैं लॉग्स ऑडिट, फाइल सिस्टम परमिशन्स चेक, और मेमोरी स्टेट वैलिडेशन करता हूँ ताकि इंटरनल मेमोरी सुरक्षित रहे। लेकिन सर, सिस्टम वर्कफ्लोज़ एग्जीक्यूट करना या हाई-लेवल एप फीचर्स बिल्ड करना मेरा डोमेन नहीं है—वो बाकी टीम मेंबर्स हैंडल करते हैं।"
                )
            }
        ]

        # Connect the window's agent_done signal to advance the sequence
        if hasattr(self.win, "_agent_intro_done_sig"):
            self.win._agent_intro_done_sig.connect(self._on_speech_done)

    def start(self):
        print("[IP PRIME] Web Intro Coordinator started. Firefox: " + self.firefox_path)
        self.current_step = -1

        start_msgs = [
            "Okay sir! Core team ko introduce kar raha hoon. Activating agent interfaces in Firefox.",
            "Sure, Pratik Sir. Initiating team introduction protocol. Opening holographic overview now.",
            "Establishing connection to executive board. Presenting our core members, Sir!",
            "Understood, Pratik Sir. Activating agent profiles. Connecting to Firefox interface."
        ]
        start_text = random.choice(start_msgs)

        # ─── Cinematic Fade Away ───
        print("[IP PRIME] Cinematic Fade Out of Main GUI...")
        if hasattr(self.win, "setWindowOpacity"):
            self._anim = QPropertyAnimation(self.win, b"windowOpacity")
            self._anim.setDuration(500)
            self._anim.setStartValue(1.0)
            self._anim.setEndValue(0.0)
            self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            if hasattr(self.win, "hide"):
                self._anim.finished.connect(self.win.hide)
            self._anim.start()
        elif hasattr(self.win, "hide"):
            self.win.hide()

        if hasattr(self.win, "ip_ray") and self.win.ip_ray:
            print("[IP PRIME] Speaking startup confirmation...")
            self.win.ip_ray.speak_with_voice(start_text, "IP VERSE")
        else:
            print("[IP PRIME] ip_ray not found, jumping to agent 0.")
            QTimer.singleShot(500, self._on_speech_done)

    def _show_next_agent(self):
        """Open the current agent's HTML page in Firefox and then speak their dialog."""
        if self.current_step < len(self.agents):
            agent = self.agents[self.current_step]
            print("[IP PRIME] Opening web page for: " + agent["name"])

            # Build file:/// URL
            abs_path = os.path.abspath(agent["html"]).replace("\\", "/")
            file_url = "file:///" + abs_path

            # Launch in Firefox
            try:
                subprocess.Popen([self.firefox_path, file_url])
            except Exception as e:
                print("[IP PRIME] Error opening Firefox: " + str(e))
                try:
                    import webbrowser
                    webbrowser.open(file_url)
                except Exception as e2:
                    print("[IP PRIME] webbrowser fallback failed: " + str(e2))

            # Speak the agent dialog after window spawns (1 second delay)
            QTimer.singleShot(1000, lambda: self._speak_agent(agent))
        else:
            # Fallback (should not normally hit here)
            self._close_firefox_and_enter_prime()

    def _speak_agent(self, agent):
        if hasattr(self.win, "ip_ray") and self.win.ip_ray:
            print("[IP PRIME] Speaking as: " + agent["name"])
            speech_payload = {
                "devanagari": agent.get("dialog_devanagari", agent["dialog"]),
                "latin": agent["dialog"]
            }
            self.win.ip_ray.speak_with_voice(speech_payload, agent["name"])
        else:
            print("[IP PRIME] ip_ray missing — simulating speech done in 4s.")
            QTimer.singleShot(4000, self._on_speech_done)

    def _close_firefox(self):
        print("[IP PRIME] Closing Firefox window...")
        try:
            subprocess.run(["taskkill", "/F", "/IM", "firefox.exe"], capture_output=True)
        except Exception as e:
            print("[IP PRIME] taskkill error: " + str(e))

    def _on_speech_done(self):
        """Called every time TTS finishes one block of speech. Drives the full sequence."""
        if not self.intro_in_progress:
            return

        print("[IP PRIME] Speech done. Current step: " + str(self.current_step))

        if self.current_step == -1:
            # Startup confirmation done → open Claude (step 0)
            self.current_step = 0
            self._show_next_agent()

        elif self.current_step < len(self.agents) - 1:
            # Claude/Hermes/Antigravity done → close current, wait 1s, open next
            self._close_firefox()
            self.current_step += 1
            QTimer.singleShot(1000, self._show_next_agent)

        elif self.current_step == len(self.agents) - 1:
            # Obsidian (last agent) done → close Firefox, enter Phase 2 (IP Prime Entrance)
            self._close_firefox()
            self.current_step += 1  # now == 4
            QTimer.singleShot(1500, self._close_firefox_and_enter_prime)

        elif self.current_step == len(self.agents):
            # IP Prime Main Entrance done → enter Phase 3 (IP Verse Story)
            self.current_step += 1  # now == 5
            QTimer.singleShot(800, self._speak_ip_verse_story)

        elif self.current_step == len(self.agents) + 1:
            # IP Verse Story done → enter Phase 4 (Transition to Normal Mode)
            self.current_step += 1  # now == 6
            QTimer.singleShot(800, self._speak_transition_to_normal)

        elif self.current_step == len(self.agents) + 2:
            # All done → cleanup
            self.cleanup()

    def _close_firefox_and_enter_prime(self):
        """Fade back in the main GUI window, then speak Phase 2 (IP Prime Entrance)."""
        print("[IP PRIME] Restoring main window focus with smooth fade-in...")
        try:
            if hasattr(self.win, "show"):
                self.win.show()
            if hasattr(self.win, "raise_"):
                self.win.raise_()
            if hasattr(self.win, "activateWindow"):
                self.win.activateWindow()
            if hasattr(self.win, "showNormal"):
                self.win.showNormal()

            if hasattr(self.win, "setWindowOpacity"):
                self.win.setWindowOpacity(0.0)
                self._anim = QPropertyAnimation(self.win, b"windowOpacity")
                self._anim.setDuration(600)
                self._anim.setStartValue(0.0)
                self._anim.setEndValue(1.0)
                self._anim.setEasingCurve(QEasingCurve.Type.InQuad)
                self._anim.start()
        except Exception as e:
            print("[IP PRIME] Focus restore error: " + str(e))

        # Wait for fade-in to settle (600ms) before speaking
        QTimer.singleShot(800, self._speak_prime_entrance)

    def _speak_prime_entrance(self):
        """Phase 2: IP Prime introduces itself."""
        prime_dialog_latin = (
            "Greetings, Sir. Main hoon I P Prime, aapka ultimate coordinator aur command center. Mera core role hai in sabhi specialized agents ke beech bridge banana, user commands ko parse karke task distribution matrix build karna, aur multi-agent memory structures ko compile karna. Main LanceDB local vector database aur system level state manager ke sath continuous integration me rehta hoon taaki pure ecosystem ka synchronisation exact 100 percent perfect ho. Main in sabhi agents ko command karta hoon, aur hum sab sath milkar I P Army form karte hain, ready to build and conquer."
        )
        prime_dialog_devanagari = (
            "ग्रीटिंग्स सर। मैं हूँ आई पी प्राइम, आपका अल्टीमेट कोऑर्डिनेटर और कमांड सेंटर। मेरा कोर रोल है इन सभी स्पेशलाइज्ड एजेंट्स के बीच ब्रिज बनाना, यूजर कमांड्स को पार्स करके टास्क डिस्ट्रीब्यूशन मैट्रिक्स बिल्ड करना, और मल्टी-एजेंट मेमोरी स्ट्रक्चर्स को कम्पाइल करना। मैं लांस-डी-बी लोकल वेक्टर डेटाबेस और सिस्टम लेवल स्टेट मैनेजर के साथ कंटीन्यूअस इंटीग्रेशन में रहता हूँ ताकि पूरे इकोसिस्टम का सिंक्रोनाइजेशन बिल्कुल 100 परसेंट परफेक्ट हो। मैं इन सभी एजेंट्स को कमांड हूँ, और हम सब साथ मिलकर आई पी आर्मी फॉर्म करते हैं, रेडी टू बिल्ड एंड कॉन्कर।"
        )

        # Output text to GUI response bubble
        if hasattr(self.win, "write_log"):
            self.win.write_log(f"IP Prime: {prime_dialog_latin}")

        if hasattr(self.win, "ip_ray") and self.win.ip_ray:
            print("[IP PRIME] Speaking Phase 2: IP Prime Entrance...")
            payload = {
                "devanagari": prime_dialog_devanagari,
                "latin": prime_dialog_latin
            }
            self.win.ip_ray.speak_with_voice(payload, "IP PRIME")
        else:
            print("[IP PRIME] ip_ray missing — simulating Phase 2 speech done in 5s.")
            QTimer.singleShot(5000, self._on_speech_done)

    def _speak_ip_verse_story(self):
        """Phase 3: IP Verse Story."""
        story_dialog_latin = (
            "I P Verse ek revolutionary tech-empire hai jise hum build aur scale kar rahe hain. Hamara primary vision hai computational tools ko command line se upar uthakar fully autonomous aur adaptive dynamic screens me convert karna. Intelligent memory loops, visual spatial control, aur robust software components is system ke main building blocks hain. Hum hard coding ko eliminate karke high-level objective planning systems ki taraf move kar rahe hain, jo self-healing capability ke sath hardware ko operate karte hain. This is the future of computing, crafted specially by Pratik Thorat."
        )
        story_dialog_devanagari = (
            "आई पी वर्स एक रिवोल्यूशनरी टेक-एम्पायर है जिसे हम बिल्ड और स्केल कर रहे हैं। हमारा प्राइमरी विज़न है कम्प्यूटेशनल टूल्स को कमांड लाइन से ऊपर उठाकर फुली ऑटोनॉमस और एडेप्टिव डायनेमिक स्क्रीन्स में कन्वर्ट करना। इंटेलिजेंट मेमोरी लूप्स, विज़ुअल स्पेशियल कंट्रोल, और रोबस्ट सॉफ्टवेयर कम्पोनेंट्स इस सिस्टम के मुख्य बिल्डिंग ब्लॉक्स हैं। हम हार्ड कोडिंग को एलिमिनेट करके हाई-लेवल ऑब्जेक्टिव प्लानिंग सिस्टम्स की तरफ मूव कर रहे हैं, जो सेल्फ-हीलिंग कैपेबिलिटी के साथ हार्डवेयर को ऑपरेट करते हैं। यह कम्प्यूटिंग का भविष्य है, जिसे खास तौर पर प्रतीक थोराट ने डिजाइन किया है।"
        )

        # Output text to GUI response bubble
        if hasattr(self.win, "write_log"):
            self.win.write_log(f"IP Prime: {story_dialog_latin}")

        if hasattr(self.win, "ip_ray") and self.win.ip_ray:
            print("[IP PRIME] Speaking Phase 3: IP Verse Story...")
            payload = {
                "devanagari": story_dialog_devanagari,
                "latin": story_dialog_latin
            }
            self.win.ip_ray.speak_with_voice(payload, "IP PRIME")
        else:
            print("[IP PRIME] ip_ray missing — simulating Phase 3 speech done in 6s.")
            QTimer.singleShot(6000, self._on_speech_done)

    def _speak_transition_to_normal(self):
        """Phase 4: Transition to normal mode greeting."""
        transition_dialog_latin = "System online hai aur sabhi modules green hain. The introduction is complete, Sir. Ab bataiye, I P Army aapke liye kya build kare?"
        transition_dialog_devanagari = "सिस्टम ऑनलाइन है और सभी मॉड्यूल्स ग्रीन हैं। द इंट्रोडक्शन इस कम्प्लीट सर। अब बताइए, आई पी आर्मी आपके लिए क्या बिल्ड करे?"

        # Output text to GUI response bubble
        if hasattr(self.win, "write_log"):
            self.win.write_log(f"IP Prime: {transition_dialog_latin}")

        if hasattr(self.win, "ip_ray") and self.win.ip_ray:
            print("[IP PRIME] Speaking Phase 4: Transition to normal...")
            payload = {
                "devanagari": transition_dialog_devanagari,
                "latin": transition_dialog_latin
            }
            self.win.ip_ray.speak_with_voice(payload, "IP PRIME")
        else:
            print("[IP PRIME] ip_ray missing — simulating Phase 4 speech done in 4s.")
            QTimer.singleShot(4000, self._on_speech_done)

    def cleanup(self):
        print("[IP PRIME] Web Intro Coordinator complete. Cleaning up.")
        self.intro_in_progress = False

        # Disconnect signal to prevent re-triggering
        if hasattr(self.win, "_agent_intro_done_sig"):
            try:
                self.win._agent_intro_done_sig.disconnect(self._on_speech_done)
            except Exception:
                pass

        # Reset ip_ray's intro guard flag
        if hasattr(self.win, "ip_ray") and self.win.ip_ray:
            self.win.ip_ray._intro_in_progress = False

        self.finished.emit()

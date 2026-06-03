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
                    "Namaste Pratik Sir. Main hoon Claude. Mera kaam hai logical reasoning, structured research, aur complex programming problems ko solve karna. "
                    "Main deep codebase analysis aur architectural decisions me help karta hoon. Lekin sir, main automation pipelines ko control nahi karta aur na hi tasks trigger karta hoon—wo kaam mera nahi hai."
                )
            },
            {
                "name": "HERMES",
                "html": os.path.join(self.base_dir, "assets", "team_intro", "hermes.html"),
                "dialog": (
                    "Yo Pratik Sir! Main hoon Hermes. Mera kaam hai workflow automation aur core pipelines ko manage karna. "
                    "System me scripts ko run karna, automations schedule karna, aur different modules ko back-to-back connect karna mera domain hai. Lekin main deep research ya UI/UX layouts design nahi karta—wo Claude aur baki agents ka kaam hai, mera nahi."
                )
            },
            {
                "name": "ANTIGRAVITY",
                "html": os.path.join(self.base_dir, "assets", "team_intro", "antigravity.html"),
                "dialog": (
                    "Pratik Sir, main hoon AntiGravity. Mera role hai system ke core architecture aur high-performance runtime loops ko maintain rakhna. "
                    "Main code logic flow, execution loops, aur safety guardrails ko manage karta hoon taaki system crash na ho. Lekin sir, system ki firewall security audits aur vulnerability penetration testing mera kaam nahi hai."
                )
            },
            {
                "name": "OBSIDIAN",
                "html": os.path.join(self.base_dir, "assets", "team_intro", "obsidian.html"),
                "dialog": (
                    "Pratik Sir, main hoon Obsidian. Mera target hai system security, access logs auditing, data encryption, aur code safety checks run karna. "
                    "Main IP Verse ecosystem ko vulnerabilities aur external threats se completely protect karta hoon. Lekin sir, main application logic likhne ya tasks run karne ka kaam nahi karta."
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
            self.win.ip_ray.speak_with_voice(agent["dialog"], agent["name"])
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
        prime_dialog = (
            "Greetings, Sir. Main hoon I P Prime, aapka central coordinator aur commander. "
            "Mera primary responsibility hai pure I P Verse ecosystem ko run karna, tasks distribute karna, aur sabhi agents ki details ko single-hub interface me manage karna. "
            "Together, we form the I P Army—specialized A I agents ka powerful network jo build, create, analyze aur automate karne ke liye ready hai."
        )

        # Output text to GUI response bubble
        if hasattr(self.win, "write_log"):
            self.win.write_log(f"IP Prime: {prime_dialog}")

        if hasattr(self.win, "ip_ray") and self.win.ip_ray:
            print("[IP PRIME] Speaking Phase 2: IP Prime Entrance...")
            self.win.ip_ray.speak_with_voice(prime_dialog, "IP PRIME")
        else:
            print("[IP PRIME] ip_ray missing — simulating Phase 2 speech done in 5s.")
            QTimer.singleShot(5000, self._on_speech_done)

    def _speak_ip_verse_story(self):
        """Phase 3: IP Verse Story."""
        story_dialog = (
            "I P Verse ek advanced technological ecosystem hai jise hamare founder Pratik Thorat ne build kiya hai. "
            "Hamare startup ka vision hai ek single, unified, intelligent command center banana jahan sabhi A I tools milkar execute karein. "
            "Har ek agent ka unique role hai, aur hum sabhi aapke instructions ke mutabik dynamic solutions deploy karne ke liye design kiye gaye hain."
        )

        # Output text to GUI response bubble
        if hasattr(self.win, "write_log"):
            self.win.write_log(f"IP Prime: {story_dialog}")

        if hasattr(self.win, "ip_ray") and self.win.ip_ray:
            print("[IP PRIME] Speaking Phase 3: IP Verse Story...")
            self.win.ip_ray.speak_with_voice(story_dialog, "IP PRIME")
        else:
            print("[IP PRIME] ip_ray missing — simulating Phase 3 speech done in 6s.")
            QTimer.singleShot(6000, self._on_speech_done)

    def _speak_transition_to_normal(self):
        """Phase 4: Transition to normal mode greeting."""
        transition_dialog = "System online hai aur sabhi modules green hain. The introduction is complete, Sir. Ab bataiye, I P Army aapke liye kya build kare?"

        # Output text to GUI response bubble
        if hasattr(self.win, "write_log"):
            self.win.write_log(f"IP Prime: {transition_dialog}")

        if hasattr(self.win, "ip_ray") and self.win.ip_ray:
            print("[IP PRIME] Speaking Phase 4: Transition to normal...")
            self.win.ip_ray.speak_with_voice(transition_dialog, "IP PRIME")
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

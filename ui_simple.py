"""
ui_simple.py — IP Prime Clean Minimal HUD
A lean, beautiful alternative to ui_core.py.
Same public API — drop-in replacement via ui.py.
"""
from __future__ import annotations

import json
import math
import random
import sys
import threading
import time
from pathlib import Path

import psutil

from PyQt6.QtCore import (
    QRectF, Qt, QTimer, QPointF, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter,
    QPainterPath, QPen, QRadialGradient, QIcon,
)
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget, QSystemTrayIcon, QMenu,
)


# ─────────────────────────── Paths ───────────────────────────────────────────
def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"


# ─────────────────────────── Colour palette ──────────────────────────────────
class C:
    BG       = "#040810"
    PANEL    = "rgba(8, 14, 28, 0.94)"
    BORDER   = "rgba(39, 200, 245, 0.16)"
    PRI      = "#27C8F5"
    PRI_DIM  = "#0e8fb5"
    PRI_GHO  = "rgba(39, 200, 245, 0.09)"
    ACC      = "#8B5CF6"
    ACC2     = "#a78bfa"
    CYAN     = "#27C8F5"
    GREEN    = "#10B981"
    RED      = "#EF4444"
    MUTED_C  = "#F43F5E"
    TEXT     = "#F0F4F8"
    TEXT_DIM = "#3D4E66"
    TEXT_MED = "#8899A6"
    WHITE    = "#FFFFFF"
    DARK     = "#020617"
    BAR_BG   = "#141C30"


_THEMES = [
    # 0 Cyan (default)
    {"BG": "#040810", "PRI": "#27C8F5", "PRI_DIM": "#0e8fb5",
     "BORDER": "rgba(39,200,245,0.16)", "ACC": "#8B5CF6", "CYAN": "#27C8F5", "GREEN": "#10B981"},
    # 1 Red
    {"BG": "#120306", "PRI": "#EF4444", "PRI_DIM": "#B91C1C",
     "BORDER": "rgba(239,68,68,0.16)", "ACC": "#F43F5E", "CYAN": "#FCA5A5", "GREEN": "#10B981"},
    # 2 Green
    {"BG": "#020a05", "PRI": "#10B981", "PRI_DIM": "#047857",
     "BORDER": "rgba(16,185,129,0.16)", "ACC": "#34D399", "CYAN": "#A7F3D0", "GREEN": "#3B82F6"},
    # 3 Purple
    {"BG": "#080014", "PRI": "#D946EF", "PRI_DIM": "#C026D3",
     "BORDER": "rgba(217,70,239,0.16)", "ACC": "#06B6D4", "CYAN": "#F472B6", "GREEN": "#10B981"},
    # 4 Electric
    {"BG": "#02020a", "PRI": "#00f0ff", "PRI_DIM": "#008bb0",
     "BORDER": "rgba(0,240,255,0.18)", "ACC": "#bd00ff", "CYAN": "#00ffff", "GREEN": "#39ff14"},
    # 5 Orange
    {"BG": "#130900", "PRI": "#FF9933", "PRI_DIM": "#D97706",
     "BORDER": "rgba(255,153,51,0.18)", "ACC": "#F59E0B", "CYAN": "#FDE68A", "GREEN": "#10B981"},
]


def _load_theme():
    f = CONFIG_DIR / "theme.json"
    if f.exists():
        try:
            idx = json.loads(f.read_text("utf-8")).get("theme_idx", 0)
            if 0 <= idx < len(_THEMES):
                for k, v in _THEMES[idx].items():
                    setattr(C, k, v)
        except Exception:
            pass


_load_theme()


def _qc(h: str, a: int = 255) -> QColor:
    c = QColor(h)
    c.setAlpha(a)
    return c


# ═══════════════════════════════════════════════════════════════════════════════
#  Orb Widget
# ═══════════════════════════════════════════════════════════════════════════════
class PrimeOrb(QWidget):
    """Animated AI core orb — glowing circle with rotating rings and particles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(160, 160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        # State
        self.state   = "LISTENING"
        self.muted   = False
        self.speaking = False

        # Animation vars
        self._scale      = 1.0
        self._tgt_scale  = 1.0
        self._halo       = 60.0
        self._tgt_halo   = 60.0
        self._voice_lvl  = 0.0
        self._tgt_voice  = 0.0
        self._phase      = 0.0
        self._ring1      = 0.0
        self._ring2      = 0.0
        self._last_t     = time.time()
        self._tick       = 0

        # Voice bars (12 bands)
        self._bars = [random.uniform(0.08, 0.3) for _ in range(12)]

        # Flying particles
        self._parts: list[list[float]] = []

        # 25 FPS timer
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(40)

    # ── public ──────────────────────────────────────────────────────────────

    def set_voice_level(self, level: float):
        self._tgt_voice = max(0.0, min(1.0, level))

    # ── animation loop ───────────────────────────────────────────────────────

    def _step(self):
        self._tick  += 1
        self._phase  = (self._phase + 0.048) % (2 * math.pi)

        now = time.time()
        if now - self._last_t > (0.08 if self.speaking else 0.32):
            if self.speaking:
                self._tgt_scale = random.uniform(1.06, 1.20)
                self._tgt_halo  = random.uniform(110, 175)
            elif self.muted:
                self._tgt_scale = random.uniform(0.96, 1.0)
                self._tgt_halo  = random.uniform(18, 28)
            elif self.state in ("THINKING", "PROCESSING"):
                self._tgt_scale = random.uniform(1.0, 1.10)
                self._tgt_halo  = random.uniform(72, 105)
            else:
                self._tgt_scale = random.uniform(0.98, 1.04)
                self._tgt_halo  = random.uniform(50, 78)
            self._last_t = now

        sp = 0.24 if self.speaking else 0.10
        self._scale += (self._tgt_scale - self._scale) * sp
        self._halo  += (self._tgt_halo  - self._halo)  * sp

        if self.speaking:
            lv = self._tgt_voice if self._tgt_voice > 0.01 else random.uniform(0.25, 0.88)
        else:
            lv = 0.0
            self._tgt_voice = 0.0
        self._voice_lvl += (lv - self._voice_lvl) * 0.24

        rs1 = 2.2 if (self.speaking or self.state in ("THINKING", "PROCESSING")) else 0.45
        rs2 = -3.1 if (self.speaking or self.state in ("THINKING", "PROCESSING")) else -0.65
        self._ring1 = (self._ring1 + rs1) % 360
        self._ring2 = (self._ring2 + rs2) % 360

        # Voice bars
        for i in range(len(self._bars)):
            if self.speaking:
                t = random.uniform(0.15, 0.95)
            elif self.state in ("THINKING", "PROCESSING"):
                t = random.uniform(0.28, 0.72)
            else:
                t = random.uniform(0.04, 0.22)
            self._bars[i] += (t - self._bars[i]) * 0.28

        # Particles
        if self.speaking and random.random() < 0.22:
            W, H = self.width(), self.height()
            cx, cy = W / 2, H * 0.44
            ang = random.uniform(0, 2 * math.pi)
            r   = min(W, H) * 0.20
            self._parts.append([
                cx + math.cos(ang) * r, cy + math.sin(ang) * r,
                math.cos(ang) * random.uniform(1.0, 2.6),
                math.sin(ang) * random.uniform(1.0, 2.6), 1.0,
            ])
        self._parts = [
            [p[0] + p[2], p[1] + p[3], p[2] * 0.93, p[3] * 0.93, p[4] - 0.04]
            for p in self._parts if p[4] > 0
        ]

        self.update()

    # ── painting ─────────────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H  = self.width(), self.height()
        cx    = W / 2
        cy    = H * 0.43
        fw    = min(W, H) * 0.84

        # State → colours
        if self.muted:
            pri, sec, ga = C.MUTED_C, C.ACC, 62
        elif self.speaking:
            pri, sec, ga = C.ACC, C.PRI, 90 + int(52 * self._voice_lvl)
        elif self.state in ("THINKING", "PROCESSING"):
            pri, sec, ga = C.CYAN, C.ACC2, 88
        else:
            pri, sec, ga = C.PRI, C.ACC, 72

        # ── Outer soft aura ───────────────────────────────────────────────
        r_aura = fw * 0.50 * self._scale
        aura = QRadialGradient(cx, cy, r_aura)
        aura.setColorAt(0.0, _qc(pri, ga))
        aura.setColorAt(0.42, _qc(pri, int(ga * 0.22)))
        aura.setColorAt(1.0,  _qc(C.BG, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(aura))
        p.drawEllipse(QRectF(cx - r_aura, cy - r_aura, r_aura * 2, r_aura * 2))

        # ── Rotating dashed rings ─────────────────────────────────────────
        r1 = fw * 0.29 * self._scale + 16
        r2 = fw * 0.29 * self._scale + 32

        p.save()
        p.translate(cx, cy)
        p.rotate(self._ring1)
        pen1 = QPen(_qc(C.CYAN, 72), 1.4)
        pen1.setDashPattern([11.0, 7.0])
        p.setPen(pen1)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(-r1, -r1, r1 * 2, r1 * 2))
        p.restore()

        p.save()
        p.translate(cx, cy)
        p.rotate(self._ring2)
        pen2 = QPen(_qc(C.ACC, 48), 1.0)
        pen2.setDashPattern([4.0, 11.0])
        p.setPen(pen2)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(-r2, -r2, r2 * 2, r2 * 2))
        p.restore()

        # ── Core orb ──────────────────────────────────────────────────────
        r_orb = fw * 0.268 * self._scale
        og = QRadialGradient(cx - r_orb * 0.26, cy - r_orb * 0.26, r_orb * 1.25)
        og.setColorAt(0.0, _qc(pri, 225))
        og.setColorAt(0.42, _qc(pri, 145))
        og.setColorAt(0.75, _qc(sec, 105))
        og.setColorAt(1.0,  _qc(C.DARK, 230))
        p.setPen(QPen(_qc(pri, 110), 1.6))
        p.setBrush(QBrush(og))
        p.drawEllipse(QRectF(cx - r_orb, cy - r_orb, r_orb * 2, r_orb * 2))

        # ── Specular highlight ────────────────────────────────────────────
        sr  = r_orb * 0.36
        sxc = cx - r_orb * 0.29
        syc = cy - r_orb * 0.30
        sg  = QRadialGradient(sxc, syc, sr)
        sg.setColorAt(0.0, _qc(C.WHITE, 82))
        sg.setColorAt(1.0, _qc(C.WHITE, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(sg))
        p.drawEllipse(QRectF(sxc - sr, syc - sr, sr * 2, sr * 2))

        # ── Explosion particles ───────────────────────────────────────────
        for pt in self._parts:
            a = max(0, min(255, int(pt[4] * 215)))
            p.setBrush(QBrush(_qc(pri, a)))
            p.drawEllipse(QPointF(pt[0], pt[1]), 2.1, 2.1)

        # ── Voice waveform bars ───────────────────────────────────────────
        base_y  = cy + r_orb + 20
        n       = len(self._bars)
        total_w = min(W - 36, 138)
        bw      = total_w / n - 2.2
        bx0     = cx - total_w / 2

        p.setPen(Qt.PenStyle.NoPen)
        for i, bv in enumerate(self._bars):
            bx   = bx0 + i * (bw + 2.2)
            maxh = 28
            bh   = max(3.0, bv * maxh)
            by   = base_y + (maxh - bh) / 2

            bg = QLinearGradient(bx, by + bh, bx, by)
            bg.setColorAt(0.0, _qc(pri, 38))
            bg.setColorAt(1.0, _qc(pri, int(175 * bv) + 42))
            p.setBrush(QBrush(bg))
            p.drawRoundedRect(QRectF(bx, by, bw, bh), bw / 2, bw / 2)


# ═══════════════════════════════════════════════════════════════════════════════
#  Chat bubble
# ═══════════════════════════════════════════════════════════════════════════════
class _Bubble(QFrame):
    def __init__(self, role: str, text: str, parent=None):
        super().__init__(parent)
        is_user = role.lower() in ("user", "you")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(8)

        ava = QLabel("👤" if is_user else "🤖")
        ava.setFont(QFont("Segoe UI Emoji", 13))
        ava.setFixedWidth(30)
        ava.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)
        ava.setStyleSheet("background: transparent;")

        msg = QLabel(text)
        msg.setWordWrap(True)
        msg.setFont(QFont("Segoe UI", 9))
        msg.setMinimumWidth(60)
        msg.setMaximumWidth(390)
        msg.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        if is_user:
            msg.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 rgba(59,130,246,0.52), stop:1 rgba(139,92,246,0.44));
                    color: #ffffff;
                    border-radius: 14px; border-top-right-radius: 4px;
                    padding: 9px 13px; font-size: 9pt;
                }
            """)
            lay.addStretch()
            lay.addWidget(msg)
            lay.addWidget(ava)
        else:
            msg.setStyleSheet(f"""
                QLabel {{
                    background: rgba(39,200,245,0.07);
                    color: #dde4ec;
                    border: 1px solid rgba(39,200,245,0.13);
                    border-radius: 14px; border-top-left-radius: 4px;
                    padding: 9px 13px; font-size: 9pt;
                }}
            """)
            lay.addWidget(ava)
            lay.addWidget(msg)
            lay.addStretch()


# ═══════════════════════════════════════════════════════════════════════════════
#  Chat / log scroll area
# ═══════════════════════════════════════════════════════════════════════════════
class _ChatArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: rgba(12,18,34,0.5); width: 5px; border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(39,200,245,0.38); border-radius: 3px; min-height: 18px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        self._inner = QWidget()
        self._inner.setStyleSheet("background: transparent;")
        self._lay   = QVBoxLayout(self._inner)
        self._lay.setContentsMargins(10, 14, 10, 14)
        self._lay.setSpacing(9)
        self._lay.addStretch()
        self.setWidget(self._inner)

    def add_bubble(self, role: str, text: str):
        b = _Bubble(role, text)
        self._lay.insertWidget(self._lay.count() - 1, b)
        QTimer.singleShot(60, self._bottom)

    def add_log(self, text: str):
        lbl = QLabel(text)
        lbl.setFont(QFont("Consolas", 8))
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"color: {C.TEXT_DIM}; background: transparent; padding: 1px 12px;"
        )
        self._lay.insertWidget(self._lay.count() - 1, lbl)
        QTimer.singleShot(60, self._bottom)

    def clear_all(self):
        while self._lay.count() > 1:
            item = self._lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _bottom(self):
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())


# ═══════════════════════════════════════════════════════════════════════════════
#  Main window
# ═══════════════════════════════════════════════════════════════════════════════
class SimpleMainWindow(QMainWindow):
    # ── thread-safe signals ──────────────────────────────────────────────────
    _state_sig        = pyqtSignal(str)
    _thought_sig      = pyqtSignal(str)
    _log_sig          = pyqtSignal(str)
    _chat_sig         = pyqtSignal(str, str)
    _router_badge_sig = pyqtSignal(str)
    _fullscreen_sig   = pyqtSignal(bool)
    _pulse_highlight_sig = pyqtSignal(int, int, float, str)
    _ocr_translate_sig   = pyqtSignal(list)

    def __init__(self, face_path: str):
        super().__init__()
        self._muted    = False
        self._ready    = True
        self._drag_pos = None
        self.on_text_command = None

        # Wire signals → slots
        self._state_sig.connect(self._on_state)
        self._thought_sig.connect(self._on_thought)
        self._log_sig.connect(lambda t: self._chat.add_log(t))
        self._chat_sig.connect(lambda r, t: self._chat.add_bubble(r, t))
        self._router_badge_sig.connect(self._on_router_badge)

        self._setup_window()
        self._build_ui()
        self._build_tray(face_path)

        # Greeting
        self._chat.add_bubble("assistant", "Hello! I'm IP Prime — ready to help. 🚀")

    # ── window setup ────────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowTitle("IP Prime")
        self.setMinimumSize(800, 560)
        self.resize(960, 680)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        icon = BASE_DIR / "assets" / "ip_prime_logo.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("IPRoot")
        root.setStyleSheet(f"""
            #IPRoot {{
                background: {C.BG};
                border-radius: 18px;
                border: 1px solid {C.BORDER};
            }}
        """)
        self.setCentralWidget(root)

        vlay = QVBoxLayout(root)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        # Header
        vlay.addWidget(self._mk_header())
        vlay.addWidget(self._mk_hline())

        # Body  (left orb | divider | right chat)
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        hlay = QHBoxLayout(body)
        hlay.setContentsMargins(0, 0, 0, 0)
        hlay.setSpacing(0)

        hlay.addWidget(self._mk_left())
        hlay.addWidget(self._mk_vline())
        hlay.addWidget(self._mk_right(), 1)

        vlay.addWidget(body, 1)
        vlay.addWidget(self._mk_hline())
        vlay.addWidget(self._mk_footer())

    # ── header ──────────────────────────────────────────────────────────────

    def _mk_header(self) -> QWidget:
        hdr = QWidget()
        hdr.setFixedHeight(54)
        hdr.setStyleSheet("background: transparent;")
        # Make header draggable
        hdr.mousePressEvent = lambda e: self._hdr_press(e)
        hdr.mouseMoveEvent  = lambda e: self._hdr_move(e)

        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(20, 0, 14, 0)
        lay.setSpacing(10)

        # Brand
        brand = QLabel()
        brand.setStyleSheet("background: transparent; border: none;")
        brand.setText(
            f"<span style='color:{C.PRI};font-size:15px;"
            f"font-weight:800;letter-spacing:3px;'>IP</span>"
            f"<span style='color:{C.WHITE};font-size:12px;"
            f"font-weight:300;letter-spacing:2px;'> · PRIME</span>"
        )
        lay.addWidget(brand)

        # Build tag
        tag = QLabel("v7")
        tag.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        tag.setStyleSheet(f"""
            color:{C.TEXT_DIM};
            background:rgba(39,200,245,0.07);
            border:1px solid rgba(39,200,245,0.14);
            border-radius:8px; padding:2px 8px;
        """)
        lay.addWidget(tag)
        lay.addStretch()

        # Router badge
        self._rbadge = QLabel("🟢 Gemini")
        self._rbadge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self._rbadge.setStyleSheet(f"""
            color:{C.GREEN}; background:rgba(16,185,129,0.10);
            border:1px solid rgba(16,185,129,0.25);
            border-radius:10px; padding:3px 11px;
        """)
        lay.addWidget(self._rbadge)
        lay.addSpacing(8)

        # Control buttons
        self._mute_btn = self._mk_ctrl_btn("🔇", "Mute / Unmute", self._toggle_mute)
        lay.addWidget(self._mk_ctrl_btn("—", "Minimise", self.showMinimized))
        lay.addWidget(self._mute_btn)
        lay.addWidget(self._mk_ctrl_btn("✕", "Close", self._quit, danger=True))

        return hdr

    def _mk_ctrl_btn(self, icon: str, tip: str, slot, danger=False) -> QPushButton:
        btn = QPushButton(icon)
        btn.setFixedSize(34, 34)
        btn.setFont(QFont("Segoe UI", 10))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tip)
        if danger:
            btn.setStyleSheet("""
                QPushButton{background:rgba(239,68,68,0.11);color:#ef4444;
                    border:1px solid rgba(239,68,68,0.28);border-radius:17px;}
                QPushButton:hover{background:rgba(239,68,68,0.32);}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton{{background:transparent;color:{C.TEXT_MED};
                    border:1px solid {C.BORDER};border-radius:17px;}}
                QPushButton:hover{{background:rgba(39,200,245,0.11);color:{C.PRI};}}
            """)
        btn.clicked.connect(slot)
        return btn

    # ── left panel (orb) ────────────────────────────────────────────────────

    def _mk_left(self) -> QWidget:
        pnl = QWidget()
        pnl.setFixedWidth(252)
        pnl.setStyleSheet("background: transparent;")

        lay = QVBoxLayout(pnl)
        lay.setContentsMargins(14, 18, 14, 14)
        lay.setSpacing(10)

        # Orb
        self.hud = PrimeOrb()
        self.hud.setMinimumHeight(200)
        lay.addWidget(self.hud, 2)

        # State badge
        self._sbadge = QLabel("● LISTENING")
        self._sbadge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self._sbadge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sbadge.setStyleSheet(f"""
            color:{C.GREEN}; background:rgba(16,185,129,0.10);
            border:1px solid rgba(16,185,129,0.24);
            border-radius:12px; padding:5px 14px; letter-spacing:2px;
        """)
        lay.addWidget(self._sbadge)

        # Thought card
        tc = QWidget()
        tc.setStyleSheet(f"""
            background:rgba(39,200,245,0.04);
            border:1px solid rgba(39,200,245,0.09);
            border-radius:10px;
        """)
        tl = QVBoxLayout(tc)
        tl.setContentsMargins(10, 8, 10, 8)
        tl.setSpacing(4)

        lhdr = QLabel("💭  ACTION")
        lhdr.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lhdr.setStyleSheet(f"color:{C.TEXT_DIM}; background:transparent; letter-spacing:1px;")
        tl.addWidget(lhdr)

        self._thought_lbl = QLabel("Idle · Waiting...")
        self._thought_lbl.setFont(QFont("Segoe UI", 8))
        self._thought_lbl.setWordWrap(True)
        self._thought_lbl.setStyleSheet(f"color:{C.TEXT_MED}; background:transparent;")
        tl.addWidget(self._thought_lbl)

        lay.addWidget(tc, 1)

        # Stats card
        lay.addWidget(self._mk_stats_card())

        return pnl

    def _mk_stats_card(self) -> QWidget:
        card = QWidget()
        card.setStyleSheet(f"""
            background:rgba(6,10,22,0.7);
            border:1px solid {C.BORDER};
            border-radius:10px;
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(11, 8, 11, 8)
        cl.setSpacing(4)

        hl = QLabel("⚡  SYSTEM")
        hl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        hl.setStyleSheet(f"color:{C.TEXT_DIM}; background:transparent; letter-spacing:1px;")
        cl.addWidget(hl)

        self._cpu_lbl = QLabel("CPU  —")
        self._mem_lbl = QLabel("MEM  —")
        for lb in (self._cpu_lbl, self._mem_lbl):
            lb.setFont(QFont("Consolas", 8))
            lb.setStyleSheet(f"color:{C.TEXT_MED}; background:transparent;")
            cl.addWidget(lb)

        self._stats_tmr = QTimer(self)
        self._stats_tmr.timeout.connect(self._upd_stats)
        self._stats_tmr.start(5000)
        self._upd_stats()
        return card

    def _upd_stats(self):
        try:
            self._cpu_lbl.setText(f"CPU  {psutil.cpu_percent(interval=None):.0f}%")
            self._mem_lbl.setText(f"MEM  {psutil.virtual_memory().percent:.0f}%")
        except Exception:
            pass

    # ── right panel (chat) ──────────────────────────────────────────────────

    def _mk_right(self) -> QWidget:
        pnl = QWidget()
        pnl.setStyleSheet("background: transparent;")

        lay = QVBoxLayout(pnl)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Sub-header
        shdr = QWidget()
        shdr.setFixedHeight(36)
        shdr.setStyleSheet(f"background:transparent; border-bottom:1px solid {C.BORDER};")
        shl = QHBoxLayout(shdr)
        shl.setContentsMargins(16, 0, 14, 0)

        stitle = QLabel("💬  CONVERSATION")
        stitle.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        stitle.setStyleSheet(f"color:{C.TEXT_DIM}; background:transparent; letter-spacing:1px;")
        shl.addWidget(stitle)
        shl.addStretch()

        clr = QPushButton("🗑 Clear")
        clr.setFont(QFont("Segoe UI", 7))
        clr.setCursor(Qt.CursorShape.PointingHandCursor)
        clr.setStyleSheet(f"""
            QPushButton{{background:transparent;color:{C.TEXT_DIM};border:none;padding:2px 8px;}}
            QPushButton:hover{{color:{C.RED};}}
        """)
        clr.clicked.connect(lambda: self._chat.clear_all())
        shl.addWidget(clr)

        lay.addWidget(shdr)

        # Chat area
        self._chat = _ChatArea()
        lay.addWidget(self._chat, 1)

        return pnl

    # ── footer (input bar) ──────────────────────────────────────────────────

    def _mk_footer(self) -> QWidget:
        ft = QWidget()
        ft.setFixedHeight(62)
        ft.setStyleSheet("background: transparent;")

        lay = QHBoxLayout(ft)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a command or message…")
        self._input.setFont(QFont("Segoe UI", 9))
        self._input.setStyleSheet(f"""
            QLineEdit{{
                background:rgba(12,18,34,0.82);
                border:1px solid {C.BORDER};
                border-radius:20px;
                color:{C.TEXT};
                padding:8px 18px;
                font-size:9pt;
            }}
            QLineEdit:focus{{
                border:1px solid rgba(39,200,245,0.44);
                background:rgba(18,26,48,0.92);
            }}
        """)
        self._input.returnPressed.connect(self._on_send)
        lay.addWidget(self._input, 1)

        send = QPushButton("➤")
        send.setFixedSize(40, 40)
        send.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.setToolTip("Send")
        send.setStyleSheet(f"""
            QPushButton{{
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {C.PRI},stop:1 {C.ACC});
                color:white; border:none; border-radius:20px;
            }}
            QPushButton:hover{{padding:0 1px 1px 0;}}
            QPushButton:pressed{{padding:1px 0 0 1px;}}
        """)
        send.clicked.connect(self._on_send)
        lay.addWidget(send)

        return ft

    # ── helpers ─────────────────────────────────────────────────────────────

    def _mk_hline(self) -> QFrame:
        f = QFrame()
        f.setFixedHeight(1)
        f.setStyleSheet(f"background:{C.BORDER};")
        return f

    def _mk_vline(self) -> QFrame:
        f = QFrame()
        f.setFixedWidth(1)
        f.setStyleSheet(f"background:{C.BORDER};")
        return f

    # ── system tray ─────────────────────────────────────────────────────────

    def _build_tray(self, face_path: str):
        icon_p = BASE_DIR / "assets" / "ip_prime_logo.png"
        icon   = QIcon(str(icon_p)) if icon_p.exists() else QIcon()
        self._tray = QSystemTrayIcon(icon, self)
        menu = QMenu()
        menu.addAction("Show / Hide", self._toggle_vis)
        menu.addSeparator()
        menu.addAction("Quit", self._quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(
            lambda r: self._toggle_vis()
            if r == QSystemTrayIcon.ActivationReason.Trigger else None
        )
        self._tray.show()

    def _toggle_vis(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()
            self.raise_()

    def _quit(self):
        QApplication.instance().quit()

    # ── slot handlers ────────────────────────────────────────────────────────

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        if self._muted:
            self._mute_btn.setText("🔊")
            self._on_state("MUTED")
        else:
            self._mute_btn.setText("🔇")
            self._on_state("LISTENING")

    def _on_state(self, state: str):
        self.hud.state   = state
        self.hud.speaking = (state == "SPEAKING")
        cfg = {
            "LISTENING":  (C.GREEN,   "rgba(16,185,129,0.10)", "rgba(16,185,129,0.26)", "●  LISTENING"),
            "SPEAKING":   (C.ACC2,    "rgba(139,92,246,0.10)", "rgba(139,92,246,0.30)", "▶  SPEAKING"),
            "THINKING":   (C.CYAN,    "rgba(39,200,245,0.10)", "rgba(39,200,245,0.26)", "◎  THINKING"),
            "PROCESSING": (C.PRI,     "rgba(39,200,245,0.10)", "rgba(39,200,245,0.26)", "⟳  PROCESSING"),
            "MUTED":      (C.MUTED_C, "rgba(244,63,94,0.10)",  "rgba(244,63,94,0.26)",  "✖  MUTED"),
        }
        col, bg, bdr, txt = cfg.get(
            state, (C.TEXT_MED, "rgba(14,20,36,0.5)", C.BORDER, state)
        )
        self._sbadge.setStyleSheet(f"""
            color:{col}; background:{bg}; border:1px solid {bdr};
            border-radius:12px; padding:5px 14px; letter-spacing:2px;
        """)
        self._sbadge.setText(txt)

    def _on_thought(self, text: str):
        self._thought_lbl.setText(text)

    def _on_router_badge(self, model: str):
        ml = model.lower()
        if "nvidia" in ml or "nim" in ml:
            self._rbadge.setText("🟩 NVIDIA")
            self._rbadge.setStyleSheet("""
                color:#22c55e;background:rgba(34,197,94,0.10);
                border:1px solid rgba(34,197,94,0.26);
                border-radius:10px;padding:3px 11px;
            """)
        elif "hacker" in ml:
            self._rbadge.setText("💀 HACKER")
            self._rbadge.setStyleSheet(f"""
                color:{C.RED};background:rgba(239,68,68,0.10);
                border:1px solid rgba(239,68,68,0.26);
                border-radius:10px;padding:3px 11px;
            """)
        else:
            self._rbadge.setText("🟢 Gemini")
            self._rbadge.setStyleSheet(f"""
                color:{C.GREEN};background:rgba(16,185,129,0.10);
                border:1px solid rgba(16,185,129,0.26);
                border-radius:10px;padding:3px 11px;
            """)

    def _on_send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._chat.add_bubble("user", text)
        if callable(self.on_text_command):
            threading.Thread(
                target=self.on_text_command, args=(text,), daemon=True
            ).start()

    # ── drag (header) ────────────────────────────────────────────────────────

    def _hdr_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def _hdr_move(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    # ── compatibility stubs ──────────────────────────────────────────────────

    def append_log(self, text: str):
        self._chat.add_log(text)

    def nativeEvent(self, eventType, message):
        return False, 0

    def closeEvent(self, event):
        event.ignore()
        self.hide()


# ═══════════════════════════════════════════════════════════════════════════════
#  Welcome splash (minimal)
# ═══════════════════════════════════════════════════════════════════════════════
class WelcomeSplash(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(380, 190)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() // 2 - 190, screen.height() // 2 - 95)

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel(
            f"<div style='text-align:center;'>"
            f"<span style='color:{C.PRI};font-size:26px;"
            f"font-weight:800;letter-spacing:6px;'>IP PRIME</span><br><br>"
            f"<span style='color:#3D4E66;font-size:10px;"
            f"letter-spacing:2px;'>INITIALIZING CORE INTELLIGENCE…</span>"
            f"</div>"
        )
        lbl.setStyleSheet("background:transparent;border:none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)

        QTimer.singleShot(2000, self.close)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(_qc("#040810", 242)))
        p.setPen(QPen(_qc(C.PRI, 80), 1))
        p.drawRoundedRect(self.rect(), 18, 18)


# ═══════════════════════════════════════════════════════════════════════════════
#  _RootShim  (main.py compatibility)
# ═══════════════════════════════════════════════════════════════════════════════
class _RootShim:
    def __init__(self, app):
        self._app = app

    def mainloop(self):
        self._app.exec()

    def after(self, ms, fn):
        QTimer.singleShot(ms, fn)

    def quit(self):
        self._app.quit()


# ═══════════════════════════════════════════════════════════════════════════════
#  Public IPRayUI — same API as ui_core.IPRayUI
# ═══════════════════════════════════════════════════════════════════════════════
class IPRayUI:
    def __init__(self, face_path: str, size=None):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._app.setQuitOnLastWindowClosed(False)

        self._splash = WelcomeSplash()
        self._splash.show()
        self._app.processEvents()

        self._win = SimpleMainWindow(face_path)
        self._win.show()
        self.root = _RootShim(self._app)

    # ── muted ────────────────────────────────────────────────────────────────

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            self._win._toggle_mute()

    # ── file drop zone (stub — no drop zone in simple UI) ───────────────────

    @property
    def current_file(self) -> str | None:
        return None

    # ── text command callback ────────────────────────────────────────────────

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    # ── state ────────────────────────────────────────────────────────────────

    def set_state(self, state: str):
        self._win._state_sig.emit(state)

    # ── thought / log / chat ─────────────────────────────────────────────────

    def write_thought(self, text: str):
        try:
            self._win._thought_sig.emit(str(text))
        except Exception:
            pass

    def write_log(self, text: str):
        self._win._log_sig.emit(str(text))

    def write_chat(self, role: str, text: str):
        self._win._chat_sig.emit(role, str(text))

    # ── misc ─────────────────────────────────────────────────────────────────

    def set_fullscreen(self, full: bool):
        pass  # no-op in simple UI

    def wait_for_api_key(self):
        while not self._win._ready:
            time.sleep(0.1)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")

    def pulse_highlight(self, x: int, y: int, duration: float = 3.0, color: str = "cyan"):
        pass  # no-op

    def show_ocr_translation(self, items: list):
        pass  # no-op

    def set_router_badge(self, model: str):
        self._win._router_badge_sig.emit(model)

    def set_speaking_volume(self, vol: float) -> None:
        try:
            self._win.hud.set_voice_level(vol)
        except Exception:
            pass


__all__ = ["IPRayUI", "CONFIG_DIR", "_load_theme"]

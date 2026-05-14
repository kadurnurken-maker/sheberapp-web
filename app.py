import streamlit as st
import mediapipe as mp
import cv2
import numpy as np
import av
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration, WebRtcMode
import threading
import os
import urllib.request
import json

# ─────────────────────────────────────────────
# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SHEBER AI",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# 2. ИНИЦИАЛИЗАЦИЯ MEDIAPIPE
# ─────────────────────────────────────────────
@st.cache_resource
def get_mp_pose():
    return mp.solutions.pose.Pose(
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        smooth_landmarks=True
    )

pose_model = get_mp_pose()
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# ─────────────────────────────────────────────
# 3. RTC КОНФИГУРАЦИЯ — STUN + TURN
# ─────────────────────────────────────────────
# Используем несколько STUN серверов + бесплатный TURN от Open Relay
# Для продакшена рекомендуется зарегистрироваться на metered.ca
def get_rtc_config():
    """
    Строим RTC конфиг с STUN и TURN серверами.
    TURN нужен когда STUN не работает (корпоративные сети, мобильные операторы).
    
    Бесплатные TURN серверы от openrelay.metered.ca (лимит: 500MB/мес)
    Для своего проекта зарегистрируйся: https://www.metered.ca/tools/openrelay/
    """
    return RTCConfiguration({
        "iceServers": [
            # ── STUN серверы (помогают при обычном NAT) ──
            {"urls": ["stun:stun.l.google.com:19302"]},
            {"urls": ["stun:stun1.l.google.com:19302"]},
            {"urls": ["stun:stun.relay.metered.ca:80"]},

            # ── TURN серверы (работают даже за строгим файрволом) ──
            # Протокол UDP порт 80 — часто открыт
            {
                "urls": "turn:openrelay.metered.ca:80",
                "username": "openrelayproject",
                "credential": "openrelayproject"
            },
            # Протокол TCP порт 80 — обходит большинство файрволов
            {
                "urls": "turn:openrelay.metered.ca:80?transport=tcp",
                "username": "openrelayproject",
                "credential": "openrelayproject"
            },
            # Порт 443 — HTTPS порт, открыт везде
            {
                "urls": "turn:openrelay.metered.ca:443",
                "username": "openrelayproject",
                "credential": "openrelayproject"
            },
            # TURNS (TURN over TLS) — максимальная совместимость
            {
                "urls": "turns:openrelay.metered.ca:443?transport=tcp",
                "username": "openrelayproject",
                "credential": "openrelayproject"
            },
        ],
        # Принудительно используем TURN если STUN не работает
        "iceTransportPolicy": "all"  # можно поменять на "relay" если вообще ничего не работает
    })

RTC_CONFIG = get_rtc_config()

# ─────────────────────────────────────────────
# 4. CSS + JS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Bebas+Neue&family=Noto+Sans:wght@300;400;600&display=swap');

.stApp {
    background: #080b10;
    color: #e8dcc8;
    font-family: 'Noto Sans', sans-serif;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; max-width: 1400px; }

button[kind="header"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarNavCollapseIcon"],
section[data-testid="stSidebar"] > div > div > div > button,
.st-emotion-cache-1cypcdb,
.st-emotion-cache-wc0xt,
.eczjsme0,
.eczjsme4 {
    display: none !important;
    visibility: hidden !important;
    pointer-events: none !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
}

[data-testid="stSidebar"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    transform: none !important;
    min-width: 320px !important;
    max-width: 320px !important;
    width: 320px !important;
    background: #060911 !important;
    border-right: 1px solid rgba(240,192,64,0.1) !important;
    position: relative !important;
    left: 0 !important;
    transition: none !important;
}

@media (max-width: 992px) {
    [data-testid="stSidebar"] {
        display: flex !important;
        min-width: 280px !important;
        max-width: 280px !important;
        width: 280px !important;
        position: relative !important;
        z-index: 999 !important;
    }
    .main .block-container { padding-left: 1rem !important; }
}

[data-testid="stSidebar"] .stMarkdown h3 {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.4rem;
    letter-spacing: 3px;
    color: #f0c040;
    border-bottom: 1px solid rgba(240,192,64,0.2);
    padding-bottom: 8px;
    margin-bottom: 16px;
}
[data-testid="stSidebar"] label {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 0.75rem !important;
    letter-spacing: 2px !important;
    color: #7a6a4a !important;
    text-transform: uppercase !important;
}
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] select,
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(240,192,64,0.05) !important;
    border: 1px solid rgba(240,192,64,0.2) !important;
    border-radius: 6px !important;
    color: #e8dcc8 !important;
    font-family: 'Rajdhani', sans-serif !important;
}

.hero-wrap { text-align: center; padding: 10px 0 5px; position: relative; }
.hero-eyebrow {
    font-family: 'Rajdhani', sans-serif; font-size: 0.85rem; font-weight: 600;
    letter-spacing: 6px; color: #b8860b; text-transform: uppercase; margin-bottom: 4px;
}
.hero-title {
    font-family: 'Bebas Neue', sans-serif; font-size: 4.5rem; line-height: 1;
    color: #f0c040; letter-spacing: 4px;
    text-shadow: 0 0 40px rgba(240, 192, 64, 0.25), 0 2px 0 #7a5500;
}
.hero-subtitle {
    font-family: 'Rajdhani', sans-serif; font-size: 1rem; font-weight: 400;
    letter-spacing: 3px; color: #8a7a60; margin-top: 2px;
}
.hero-line {
    width: 120px; height: 2px;
    background: linear-gradient(90deg, transparent, #f0c040, transparent);
    margin: 12px auto;
}

.metrics-row { display: flex; gap: 16px; margin: 16px 0; }
.metric-card {
    flex: 1;
    background: linear-gradient(135deg, rgba(240,192,64,0.05) 0%, rgba(8,11,16,0) 100%);
    border: 1px solid rgba(240,192,64,0.15);
    border-top: 2px solid #f0c040;
    border-radius: 4px 4px 12px 12px;
    padding: 18px 20px 14px;
    position: relative; overflow: hidden;
}
.metric-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(240,192,64,0.6), transparent);
}
.metric-label {
    font-family: 'Rajdhani', sans-serif; font-size: 0.72rem; font-weight: 600;
    letter-spacing: 3px; color: #7a6a4a; text-transform: uppercase; margin-bottom: 6px;
}
.metric-value { font-family: 'Bebas Neue', sans-serif; font-size: 2.2rem; line-height: 1; color: #f0c040; letter-spacing: 2px; }
.metric-value.blue { color: #4dc8ff; }
.metric-value.green { color: #4dff8a; }
.metric-value.red { color: #ff6b4d; }

.xp-track { background: rgba(255,255,255,0.07); border-radius: 3px; height: 5px; margin-top: 10px; overflow: hidden; }
.xp-fill {
    background: linear-gradient(90deg, #b8860b, #f0c040, #ffd700);
    height: 100%; border-radius: 3px; transition: width 0.5s ease;
    box-shadow: 0 0 8px rgba(240,192,64,0.5);
}
.xp-caption { font-size: 0.65rem; color: #5a4a2a; margin-top: 4px; font-family: 'Rajdhani', sans-serif; letter-spacing: 2px; }

.video-container { border: 1px solid rgba(240,192,64,0.25); border-radius: 12px; overflow: hidden; background: #040608; }
.video-header { background: rgba(240,192,64,0.07); border-bottom: 1px solid rgba(240,192,64,0.15); padding: 10px 16px; display: flex; align-items: center; gap: 10px; }
.live-dot { width: 8px; height: 8px; background: #ff3333; border-radius: 50%; box-shadow: 0 0 6px #ff3333; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
.video-title-text { font-family: 'Rajdhani', sans-serif; font-size: 0.8rem; font-weight: 600; letter-spacing: 3px; color: #8a7a60; text-transform: uppercase; }

.stButton > button {
    width: 100%;
    background: linear-gradient(135deg, #8a6500, #c8960a) !important;
    color: #080b10 !important;
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1.1rem !important;
    letter-spacing: 3px !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 10px !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #c8960a, #f0c040) !important;
    box-shadow: 0 4px 20px rgba(240,192,64,0.3) !important;
    transform: translateY(-1px) !important;
}

.guide-card {
    background: rgba(240,192,64,0.04);
    border: 1px solid rgba(240,192,64,0.12);
    border-left: 3px solid #f0c040;
    border-radius: 0 8px 8px 0;
    padding: 14px 16px; margin-top: 12px;
}
.guide-move-title { font-family: 'Bebas Neue', sans-serif; font-size: 1.3rem; letter-spacing: 2px; color: #f0c040; margin-bottom: 4px; }
.guide-tip { font-size: 0.85rem; color: #8a7a60; line-height: 1.6; }

.sidebar-rank { text-align: center; padding: 16px; background: rgba(240,192,64,0.05); border: 1px solid rgba(240,192,64,0.15); border-radius: 10px; margin-bottom: 16px; }
.sidebar-rank-icon { font-size: 2.5rem; }
.sidebar-rank-name { font-family: 'Bebas Neue', sans-serif; font-size: 1.6rem; letter-spacing: 4px; color: #f0c040; }
.sidebar-rank-desc { font-size: 0.72rem; color: #5a4a2a; font-family: 'Rajdhani', sans-serif; letter-spacing: 2px; }

.divider { border: none; border-top: 1px solid rgba(240,192,64,0.1); margin: 20px 0; }

.status-box {
    padding: 10px 16px; border-radius: 8px; margin: 8px 0;
    font-family: 'Rajdhani', sans-serif; font-size: 1rem;
    font-weight: 600; letter-spacing: 2px; text-align: center;
}
.status-good { background: rgba(77,255,138,0.1); border: 1px solid rgba(77,255,138,0.3); color: #4dff8a; }
.status-warn { background: rgba(255,107,77,0.1); border: 1px solid rgba(255,107,77,0.4); color: #ff6b4d; }

/* Блок предупреждения о соединении */
.conn-warn {
    background: rgba(255,160,0,0.08);
    border: 1px solid rgba(255,160,0,0.3);
    border-left: 3px solid #ffa000;
    border-radius: 6px;
    padding: 12px 16px;
    margin: 12px 0;
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.85rem;
    color: #c8a040;
    line-height: 1.6;
}
.conn-ok {
    background: rgba(77,255,138,0.06);
    border: 1px solid rgba(77,255,138,0.2);
    border-left: 3px solid #4dff8a;
    border-radius: 6px;
    padding: 10px 16px;
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.8rem;
    color: #4a8a60;
    letter-spacing: 1px;
}
</style>

<script>
(function keepSidebarOpen() {
    function forceOpen() {
        document.body.classList.remove('sidebar-collapsed');
        const selectors = [
            '[data-testid="collapsedControl"]',
            '[data-testid="stSidebarCollapseButton"]',
            'button[aria-label="Close sidebar"]',
            'button[aria-label="Collapse sidebar"]',
        ];
        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(btn => {
                btn.style.display = 'none';
                btn.style.visibility = 'hidden';
                btn.style.pointerEvents = 'none';
                btn.addEventListener('click', e => { e.stopImmediatePropagation(); e.preventDefault(); }, true);
            });
        });
        const sidebar = document.querySelector('[data-testid="stSidebar"]');
        if (sidebar) {
            sidebar.style.display = 'flex';
            sidebar.style.visibility = 'visible';
            sidebar.style.opacity = '1';
            sidebar.style.transform = 'none';
            sidebar.style.minWidth = '320px';
            sidebar.style.width = '320px';
        }
    }
    forceOpen();
    setInterval(forceOpen, 500);
    const observer = new MutationObserver(forceOpen);
    observer.observe(document.body, { childList: true, subtree: true, attributes: true });
})();
</script>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 5. СИСТЕМА РЕЙТИНГА
# ─────────────────────────────────────────────
RANKS = [
    {"name": "BALA",         "icon": "🥋", "min": 0,    "max": 150,  "desc": "Жас жауынгер"},
    {"name": "ZHASOSPIRIM",  "icon": "⚔️", "min": 150,  "max": 500,  "desc": "Үміткер батыр"},
    {"name": "BATYR",        "icon": "🦅", "min": 500,  "max": 1200, "desc": "Дала батыры"},
    {"name": "ҰЛТТЫҚ БАТЫР", "icon": "👑", "min": 1200, "max": 9999, "desc": "Мәңгілік даңқ"},
]

def get_rank(xp):
    for r in reversed(RANKS):
        if xp >= r["min"]:
            return r
    return RANKS[0]

def get_rank_progress(xp):
    rank = get_rank(xp)
    span = rank["max"] - rank["min"]
    earned = xp - rank["min"]
    return min(int((earned / span) * 100), 100), rank["max"]

# ─────────────────────────────────────────────
# 6. ДАННЫЕ СЕССИИ
# ─────────────────────────────────────────────
defaults = {"xp": 0, "reps": 0, "name": "Batyr", "move": "Zhambas"}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# 7. ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ (thread-safe)
# ─────────────────────────────────────────────
_global_reps   = 0
_global_xp     = 0
_global_hint   = "READY"
_global_status = "OK"
_lock = threading.Lock()

def increment_rep():
    global _global_reps, _global_xp
    with _lock:
        _global_reps += 1
        _global_xp   += 10

def reset_global():
    global _global_reps, _global_xp, _global_hint, _global_status
    with _lock:
        _global_reps   = 0
        _global_xp     = 0
        _global_hint   = "READY"
        _global_status = "OK"

def get_global_stats():
    with _lock:
        return _global_reps, _global_xp, _global_hint, _global_status

def set_global_hint(hint, status="OK"):
    global _global_hint, _global_status
    with _lock:
        _global_hint   = hint
        _global_status = status


# ─────────────────────────────────────────────
# 8. AI ENGINE
# ─────────────────────────────────────────────
class SheberAI(VideoProcessorBase):
    def __init__(self):
        self.pose  = pose_model
        self.stage = None
        self.current_name = "Batyr"
        self.current_move = "Zhambas"
        self._local_reps = 0
        self._local_xp   = 0

    def calculate_angle(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = (np.arctan2(c[1]-b[1], c[0]-b[0])
                   - np.arctan2(a[1]-b[1], a[0]-b[0]))
        angle = np.abs(radians * 180.0 / np.pi)
        return 360 - angle if angle > 180 else angle

    def get_lm(self, lms, idx):
        lm = lms[idx.value]
        return [lm.x, lm.y]

    def check_posture(self, lms):
        l_shoulder = self.get_lm(lms, mp_pose.PoseLandmark.LEFT_SHOULDER)
        r_shoulder = self.get_lm(lms, mp_pose.PoseLandmark.RIGHT_SHOULDER)
        l_hip      = self.get_lm(lms, mp_pose.PoseLandmark.LEFT_HIP)
        r_hip      = self.get_lm(lms, mp_pose.PoseLandmark.RIGHT_HIP)
        shoulder_tilt = abs(l_shoulder[1] - r_shoulder[1])
        mid_shoulder  = [(l_shoulder[0]+r_shoulder[0])/2, (l_shoulder[1]+r_shoulder[1])/2]
        mid_hip       = [(l_hip[0]+r_hip[0])/2,           (l_hip[1]+r_hip[1])/2]
        spine_lean    = abs(mid_shoulder[0] - mid_hip[0])
        straight      = shoulder_tilt < 0.07 and spine_lean < 0.10
        return straight, shoulder_tilt

    # ── ЖАМБАС ──────────────────────────────────
    def analyze_zhambas(self, lms):
        l_hip   = self.get_lm(lms, mp_pose.PoseLandmark.LEFT_HIP)
        l_knee  = self.get_lm(lms, mp_pose.PoseLandmark.LEFT_KNEE)
        l_ankle = self.get_lm(lms, mp_pose.PoseLandmark.LEFT_ANKLE)
        r_hip   = self.get_lm(lms, mp_pose.PoseLandmark.RIGHT_HIP)
        r_knee  = self.get_lm(lms, mp_pose.PoseLandmark.RIGHT_KNEE)
        r_ankle = self.get_lm(lms, mp_pose.PoseLandmark.RIGHT_ANKLE)
        knee_angle = min(
            self.calculate_angle(l_hip, l_knee, l_ankle),
            self.calculate_angle(r_hip, r_knee, r_ankle)
        )
        posture_ok, _ = self.check_posture(lms)
        if not posture_ok:
            set_global_hint("⚠️ BACK STRAIGHT!", "WARN_POSTURE")
            return knee_angle, "KEEP BACK STRAIGHT!", (0, 50, 220)
        if knee_angle < 120:
            self.stage = "down"
            set_global_hint("GOOD SQUAT!", "OK")
            return knee_angle, "GOOD SQUAT - DRIVE!", (64, 180, 255)
        if knee_angle > 160 and self.stage == "down":
            self.stage = "up"
            increment_rep()
            self._local_reps, self._local_xp, _, _ = get_global_stats()
            set_global_hint("✅ PERFECT!", "OK")
            return knee_angle, "PERFECT THROW!", (64, 255, 100)
        return knee_angle, f"ANGLE: {int(knee_angle)}", (180, 180, 100)

    # ── ШАЛУ ────────────────────────────────────
    def analyze_shalu(self, lms):
        l_hip   = self.get_lm(lms, mp_pose.PoseLandmark.LEFT_HIP)
        l_knee  = self.get_lm(lms, mp_pose.PoseLandmark.LEFT_KNEE)
        l_ankle = self.get_lm(lms, mp_pose.PoseLandmark.LEFT_ANKLE)
        r_hip   = self.get_lm(lms, mp_pose.PoseLandmark.RIGHT_HIP)
        r_knee  = self.get_lm(lms, mp_pose.PoseLandmark.RIGHT_KNEE)
        r_ankle = self.get_lm(lms, mp_pose.PoseLandmark.RIGHT_ANKLE)
        l_angle    = self.calculate_angle(l_hip, l_knee, l_ankle)
        r_angle    = self.calculate_angle(r_hip, r_knee, r_ankle)
        angle_diff = abs(l_angle - r_angle)
        posture_ok, _ = self.check_posture(lms)
        if not posture_ok:
            set_global_hint("⚠️ LEAN FORWARD!", "WARN_POSTURE")
            return min(l_angle, r_angle), "LEAN INTO SWEEP!", (0, 50, 220)
        if angle_diff > 40 and self.stage != "sweep":
            self.stage = "sweep"
            set_global_hint("SWEEP!", "OK")
            return min(l_angle, r_angle), "SWEEP NOW!", (64, 180, 255)
        if angle_diff < 15 and self.stage == "sweep":
            self.stage = None
            increment_rep()
            self._local_reps, self._local_xp, _, _ = get_global_stats()
            set_global_hint("✅ NICE SWEEP!", "OK")
            return min(l_angle, r_angle), "NICE SWEEP!", (64, 255, 100)
        return min(l_angle, r_angle), f"DIFF: {int(angle_diff)}", (180, 180, 100)

    # ── КӨТЕРМЕ ─────────────────────────────────
    def analyze_koterme(self, lms):
        l_hip   = self.get_lm(lms, mp_pose.PoseLandmark.LEFT_HIP)
        l_knee  = self.get_lm(lms, mp_pose.PoseLandmark.LEFT_KNEE)
        l_ankle = self.get_lm(lms, mp_pose.PoseLandmark.LEFT_ANKLE)
        r_hip   = self.get_lm(lms, mp_pose.PoseLandmark.RIGHT_HIP)
        r_knee  = self.get_lm(lms, mp_pose.PoseLandmark.RIGHT_KNEE)
        r_ankle = self.get_lm(lms, mp_pose.PoseLandmark.RIGHT_ANKLE)
        knee_angle = min(
            self.calculate_angle(l_hip, l_knee, l_ankle),
            self.calculate_angle(r_hip, r_knee, r_ankle)
        )
        posture_ok, _ = self.check_posture(lms)
        # Фаза 1: глубокий присед < 100° (глубже чем Жамбас!)
        if knee_angle < 100:
            self.stage = "squat"
            set_global_hint("DEEP SQUAT!", "OK")
            return knee_angle, "DEEP SQUAT - GOOD!", (64, 180, 255)
        # Фаза 2: начало подъёма
        if knee_angle > 130 and knee_angle < 160 and self.stage == "squat":
            self.stage = "lifting"
            set_global_hint("LIFT!", "OK")
            return knee_angle, "LIFT & THROW!", (255, 180, 0)
        # Фаза 3: полное выпрямление — бросок
        if knee_angle > 165 and self.stage == "lifting":
            self.stage = None
            increment_rep()
            self._local_reps, self._local_xp, _, _ = get_global_stats()
            set_global_hint("✅ POWERFUL LIFT!", "OK")
            return knee_angle, "POWERFUL LIFT!", (64, 255, 100)
        # Предупреждение если пытается схитрить без глубокого приседа
        if not posture_ok:
            set_global_hint("⚠️ BEND DEEPER!", "WARN_POSTURE")
            return knee_angle, "GRIP & BEND DEEP!", (0, 50, 220)
        return knee_angle, f"KNEE: {int(knee_angle)}", (180, 180, 100)

    # ── ГЛАВНЫЙ ОБРАБОТЧИК ──────────────────────
    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        h, w = img.shape[:2]
        rgb     = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        angle_val  = None
        hint_text  = "STAND IN FRAME"
        hint_color = (100, 100, 100)
        posture_ok = True

        if results.pose_landmarks:
            lms = results.pose_landmarks.landmark
            posture_ok, _ = self.check_posture(lms)
            skeleton_color = (64, 255, 100) if posture_ok else (0, 50, 220)

            mp_drawing.draw_landmarks(
                img, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=skeleton_color, thickness=2, circle_radius=3),
                mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=1, circle_radius=1)
            )

            try:
                move = self.current_move
                if move == "Zhambas":
                    angle_val, hint_text, hint_color = self.analyze_zhambas(lms)
                elif move == "Shalu":
                    angle_val, hint_text, hint_color = self.analyze_shalu(lms)
                elif move == "Koterme":
                    angle_val, hint_text, hint_color = self.analyze_koterme(lms)
            except Exception:
                hint_text  = "POSITIONING..."
                hint_color = (100, 100, 100)

        # Красный оверлей при ошибке осанки
        if not posture_ok and results.pose_landmarks:
            red_overlay = img.copy()
            cv2.rectangle(red_overlay, (0, 0), (w, h), (0, 0, 180), -1)
            img = cv2.addWeighted(red_overlay, 0.08, img, 0.92, 0)
            cv2.rectangle(img, (0, 0), (w-1, h-1), (0, 0, 255), 3)

        # HUD
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0),      (w, 64),    (5, 8, 14), -1)
        cv2.line(overlay,      (0, 64),     (w, 64),    (80, 60, 20), 1)
        cv2.rectangle(overlay, (0, h - 60), (w, h),     (5, 8, 14), -1)
        cv2.line(overlay,      (0, h - 60), (w, h - 60),(80, 60, 20), 1)
        img = cv2.addWeighted(overlay, 0.85, img, 0.15, 0)

        cv2.putText(img, self.current_name,
                    (16, 40), cv2.FONT_HERSHEY_DUPLEX, 0.7, (230, 220, 200), 1, cv2.LINE_AA)
        cv2.putText(img, self.current_move.upper(),
                    (w // 2 - 60, 40), cv2.FONT_HERSHEY_DUPLEX, 0.7, (240, 192, 64), 1, cv2.LINE_AA)
        cv2.putText(img, f"XP: {self._local_xp}",
                    (w - 170, 25), cv2.FONT_HERSHEY_DUPLEX, 0.55, (180, 140, 40), 1, cv2.LINE_AA)
        cv2.putText(img, f"REPS: {self._local_reps}",
                    (w - 170, 48), cv2.FONT_HERSHEY_DUPLEX, 0.55, (77, 200, 255), 1, cv2.LINE_AA)

        if angle_val is not None:
            cv2.putText(img, f"{int(angle_val)}°",
                        (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (150, 130, 80), 2, cv2.LINE_AA)

        hint_x = max(10, w // 2 - len(hint_text) * 8)
        cv2.putText(img, hint_text,
                    (hint_x, h - 18), cv2.FONT_HERSHEY_DUPLEX, 0.85, hint_color, 2, cv2.LINE_AA)

        cv2.putText(img, (self.stage or "READY").upper(),
                    (w - 130, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 90, 50), 1, cv2.LINE_AA)

        if not posture_ok and results.pose_landmarks:
            cv2.putText(img, "! BAD POSTURE",
                        (16, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 60, 255), 1, cv2.LINE_AA)

        return av.VideoFrame.from_ndarray(img, format="bgr24")


# ─────────────────────────────────────────────
# 9. ГЛАВНЫЙ ИНТЕРФЕЙС
# ─────────────────────────────────────────────
def main():

    with st.sidebar:
        st.markdown("### 🦅 WARRIOR PROFILE")

        name = st.text_input("Warrior Name", value=st.session_state["name"], key="name_input")
        st.session_state["name"] = name

        move = st.selectbox(
            "Select Drill",
            ["Zhambas", "Shalu", "Koterme"],
            index=["Zhambas", "Shalu", "Koterme"].index(st.session_state["move"])
        )
        st.session_state["move"] = move

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        g_reps, g_xp, g_hint, g_status = get_global_stats()
        st.session_state["reps"] = g_reps
        st.session_state["xp"]   = g_xp

        xp   = st.session_state["xp"]
        rank = get_rank(xp)
        st.markdown(f"""
        <div class="sidebar-rank">
            <div class="sidebar-rank-icon">{rank['icon']}</div>
            <div class="sidebar-rank-name">{rank['name']}</div>
            <div class="sidebar-rank-desc">{rank['desc']}</div>
        </div>
        """, unsafe_allow_html=True)

        prog, next_xp = get_rank_progress(xp)
        st.markdown(f"""
        <div style="margin-bottom:4px;">
            <span style="font-family:'Rajdhani',sans-serif;font-size:0.7rem;color:#5a4a2a;letter-spacing:2px;">{xp} / {next_xp} XP</span>
        </div>
        <div class="xp-track"><div class="xp-fill" style="width:{prog}%"></div></div>
        """, unsafe_allow_html=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        status_class = "status-warn" if "WARN" in g_status else "status-good"
        st.markdown(f'<div class="status-box {status_class}">{g_hint}</div>', unsafe_allow_html=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        if st.button("⟳  RESET SESSION"):
            reset_global()
            st.session_state["reps"] = 0
            st.session_state["xp"]   = 0
            st.rerun()

    # ── HEADER ───────────────────────────────────
    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-eyebrow">Қазақ Күресі · AI Coach</div>
        <div class="hero-title">🦅 SHEBER</div>
        <div class="hero-subtitle">THE INTELLIGENT THROW TRAINER</div>
        <div class="hero-line"></div>
    </div>
    """, unsafe_allow_html=True)

    # ── МЕТРИКИ ──────────────────────────────────
    xp    = st.session_state["xp"]
    reps  = st.session_state["reps"]
    rank  = get_rank(xp)
    prog, next_xp = get_rank_progress(xp)

    st.markdown(f"""
    <div class="metrics-row">
        <div class="metric-card">
            <div class="metric-label">Rank</div>
            <div class="metric-value">{rank['icon']} {rank['name']}</div>
            <div class="xp-caption">{rank['desc']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Experience</div>
            <div class="metric-value">{xp}</div>
            <div class="xp-track"><div class="xp-fill" style="width:{prog}%"></div></div>
            <div class="xp-caption">{xp} / {next_xp} XP TO NEXT RANK</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Reps Completed</div>
            <div class="metric-value blue">{reps}</div>
            <div class="xp-caption">+10 XP PER REP</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Current Drill</div>
            <div class="metric-value" style="font-size:1.5rem;">{st.session_state['move'].upper()}</div>
            <div class="xp-caption">КАЗАҚ КҮРЕСІ</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── ПРЕДУПРЕЖДЕНИЕ О СОЕДИНЕНИИ ──────────────
    with st.expander("⚠️ Проблемы с подключением камеры? Читай здесь", expanded=False):
        st.markdown("""
        <div class="conn-warn">
        <b>Почему появляется ошибка соединения?</b><br>
        WebRTC (технология видео) требует прямого соединения между твоим браузером и сервером.
        Файрволы, VPN, корпоративные сети и мобильные операторы часто это блокируют.<br><br>
        <b>Решения (по порядку):</b><br>
        1. Отключи VPN если включён<br>
        2. Попробуй другую сеть (мобильный хотспот вместо WiFi)<br>
        3. Используй Chrome или Edge (Firefox иногда глючит с WebRTC)<br>
        4. Разреши доступ к камере в браузере (иконка замка в адресной строке)<br>
        5. Если на Streamlit Cloud — лучше запустить локально: <code>streamlit run app.py</code><br>
        </div>
        <div class="conn-ok">
        ✅ В коде уже добавлены TURN серверы (openrelay.metered.ca) — они работают даже за строгими файрволами через порт 443 (HTTPS).
        </div>
        """, unsafe_allow_html=True)

    # ── ВИДЕО + ГАЙД ─────────────────────────────
    col_vid, col_guide = st.columns([2, 1])

    with col_vid:
        st.markdown("""
        <div class="video-container">
            <div class="video-header">
                <div class="live-dot"></div>
                <span class="video-title-text">LIVE · POSE TRACKING · AI ANALYSIS</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        ctx = webrtc_streamer(
            key="sheber-v4",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIG,
            video_processor_factory=SheberAI,
            media_stream_constraints={
                "video": {"width": 640, "height": 480, "frameRate": 25},
                "audio": False
            },
            async_processing=True,
        )

        if ctx.video_processor:
            ctx.video_processor.current_name = st.session_state["name"]
            ctx.video_processor.current_move = st.session_state["move"]

    with col_guide:
        move    = st.session_state["move"]
        img_map = {
            "Zhambas": "jambass.jpg",
            "Shalu":   "shalu.jpg",
            "Koterme": "koterme.webp"
        }
        img_path = img_map.get(move, "hero.jpg")
        if os.path.exists(img_path):
            st.image(img_path, use_container_width=True)
        elif os.path.exists("hero.jpg"):
            st.image("hero.jpg", use_container_width=True)

        guides = {
            "Zhambas": {
                "title": "ЖАМБАС", "desc": "Бедренный бросок",
                "tip": "Держи спину ровно. AI считает: угол колена < 120° (подсед) → выпрямление > 160° (бросок).",
                "steps": ["Захват пояса", "Подсед 90–120°", "Подъём через бедро", "Бросок вперёд"],
                "detect": "📐 Угол колена + осанка"
            },
            "Shalu": {
                "title": "ШАЛУ", "desc": "Подсечка",
                "tip": "Перенеси вес на одну ногу. AI считает разницу углов ног: > 40° (перенос) → возврат в стойку.",
                "steps": ["Тяни противника", "Зайди сбоку", "Перенос веса", "Подсечка — возврат"],
                "detect": "⚖️ Разница углов ног (баланс)"
            },
            "Koterme": {
                "title": "КӨТЕРМЕ", "desc": "Подъёмный бросок",
                "tip": "Глубже чем Жамбас! AI считает 3 фазы: присед < 100° → подъём → полное выпрямление > 165°.",
                "steps": ["Глубокий захват пояса", "Присед ниже 100°", "Взрывной подъём", "Полное выпрямление"],
                "detect": "🏋️ 3 фазы: < 100° → подъём → 165°+"
            }
        }

        g = guides.get(move, guides["Zhambas"])
        st.markdown(f"""
        <div class="guide-card">
            <div class="guide-move-title">{g['title']} · {g['desc']}</div>
            <div class="guide-tip">💡 {g['tip']}</div>
            <div style="margin-top:8px;font-family:'Rajdhani',sans-serif;font-size:0.75rem;
                        color:#5a4a2a;letter-spacing:2px;">{g['detect']}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**📋 Шаги техники:**")
        for i, step in enumerate(g["steps"], 1):
            st.markdown(f"`{i}.` {step}")

        st.markdown("""
        <div style="margin-top:16px;padding:12px;background:rgba(0,0,0,0.3);
                    border-radius:8px;font-family:'Rajdhani',sans-serif;font-size:0.8rem;letter-spacing:1px;">
            <div style="color:#7a6a4a;font-size:0.7rem;letter-spacing:3px;margin-bottom:8px;">AI FEEDBACK</div>
            <div>🟢 <span style="color:#4dff8a">Зелёный</span> — повтор засчитан</div>
            <div>🔵 <span style="color:#4dc8ff">Синий</span> — фаза выполнения</div>
            <div>🔴 <span style="color:#ff4040">Красный</span> — ошибка / плохая осанка</div>
            <div>🟡 <span style="color:#f0c040">Жёлтый</span> — промежуточная фаза</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    if os.path.exists("hero.jpg"):
        st.image("hero.jpg", use_container_width=True)
    st.markdown("""
    <div style="text-align:center;padding:16px 0 8px;font-family:'Rajdhani',sans-serif;
                font-size:0.75rem;letter-spacing:3px;color:#3a2a10;">
        SHEBER AI · КАЗАҚ КҮРЕСІ · 2025
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

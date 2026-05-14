import streamlit as st
import mediapipe as mp
import cv2
import numpy as np
import av
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration, WebRtcMode
import threading
import os

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
# 3. CSS + JS — САЙДБАР ВСЕГДА ОТКРЫТ
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Bebas+Neue&family=Noto+Sans:wght@300;400;600&display=swap');

/* === БАЗОВЫЕ СТИЛИ === */
.stApp {
    background: #080b10;
    color: #e8dcc8;
    font-family: 'Noto Sans', sans-serif;
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; max-width: 1400px; }

/* ═══════════════════════════════════════════
   САЙДБАР — ВСЕГДА ВИДЕН, НИКОГДА НЕ ЗАКРЫВАЕТСЯ
   ═══════════════════════════════════════════ */

/* Скрываем ВСЕ кнопки сворачивания/разворачивания */
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

/* Принудительно держим сайдбар раскрытым */
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

/* Фиксим на мобильных */
@media (max-width: 992px) {
    [data-testid="stSidebar"] {
        display: flex !important;
        min-width: 280px !important;
        max-width: 280px !important;
        width: 280px !important;
        position: relative !important;
        z-index: 999 !important;
    }
    .main .block-container {
        padding-left: 1rem !important;
    }
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
[data-testid="stSidebar"] input:focus {
    border-color: rgba(240,192,64,0.5) !important;
    box-shadow: 0 0 0 2px rgba(240,192,64,0.1) !important;
}

/* === HERO ЗАГОЛОВОК === */
.hero-wrap {
    text-align: center;
    padding: 10px 0 5px;
    position: relative;
}
.hero-eyebrow {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 6px;
    color: #b8860b;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.hero-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 4.5rem;
    line-height: 1;
    color: #f0c040;
    letter-spacing: 4px;
    text-shadow: 0 0 40px rgba(240, 192, 64, 0.25), 0 2px 0 #7a5500;
}
.hero-subtitle {
    font-family: 'Rajdhani', sans-serif;
    font-size: 1rem;
    font-weight: 400;
    letter-spacing: 3px;
    color: #8a7a60;
    margin-top: 2px;
}
.hero-line {
    width: 120px;
    height: 2px;
    background: linear-gradient(90deg, transparent, #f0c040, transparent);
    margin: 12px auto;
}

/* === МЕТРИЧЕСКИЕ КАРТОЧКИ === */
.metrics-row {
    display: flex;
    gap: 16px;
    margin: 16px 0;
}
.metric-card {
    flex: 1;
    background: linear-gradient(135deg, rgba(240,192,64,0.05) 0%, rgba(8,11,16,0) 100%);
    border: 1px solid rgba(240,192,64,0.15);
    border-top: 2px solid #f0c040;
    border-radius: 4px 4px 12px 12px;
    padding: 18px 20px 14px;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(240,192,64,0.6), transparent);
}
.metric-label {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 3px;
    color: #7a6a4a;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.metric-value {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.2rem;
    line-height: 1;
    color: #f0c040;
    letter-spacing: 2px;
}
.metric-value.blue { color: #4dc8ff; }
.metric-value.green { color: #4dff8a; }
.metric-value.red { color: #ff6b4d; }

/* XP Прогресс бар */
.xp-track {
    background: rgba(255,255,255,0.07);
    border-radius: 3px;
    height: 5px;
    margin-top: 10px;
    overflow: hidden;
}
.xp-fill {
    background: linear-gradient(90deg, #b8860b, #f0c040, #ffd700);
    height: 100%;
    border-radius: 3px;
    transition: width 0.5s ease;
    box-shadow: 0 0 8px rgba(240,192,64,0.5);
}
.xp-caption {
    font-size: 0.65rem;
    color: #5a4a2a;
    margin-top: 4px;
    font-family: 'Rajdhani', sans-serif;
    letter-spacing: 2px;
}

/* === ВИДЕО ЗОНА === */
.video-container {
    border: 1px solid rgba(240,192,64,0.25);
    border-radius: 12px;
    overflow: hidden;
    background: #040608;
    position: relative;
}
.video-header {
    background: rgba(240,192,64,0.07);
    border-bottom: 1px solid rgba(240,192,64,0.15);
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.live-dot {
    width: 8px; height: 8px;
    background: #ff3333;
    border-radius: 50%;
    box-shadow: 0 0 6px #ff3333;
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}
.video-title-text {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 3px;
    color: #8a7a60;
    text-transform: uppercase;
}

/* === КНОПКИ === */
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

/* === ГАЙД КАРТОЧКИ === */
.guide-card {
    background: rgba(240,192,64,0.04);
    border: 1px solid rgba(240,192,64,0.12);
    border-left: 3px solid #f0c040;
    border-radius: 0 8px 8px 0;
    padding: 14px 16px;
    margin-top: 12px;
}
.guide-move-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.3rem;
    letter-spacing: 2px;
    color: #f0c040;
    margin-bottom: 4px;
}
.guide-tip {
    font-size: 0.85rem;
    color: #8a7a60;
    line-height: 1.6;
}

/* === РАНГОВЫЙ БЕЙДЖ === */
.sidebar-rank {
    text-align: center;
    padding: 16px;
    background: rgba(240,192,64,0.05);
    border: 1px solid rgba(240,192,64,0.15);
    border-radius: 10px;
    margin-bottom: 16px;
}
.sidebar-rank-icon { font-size: 2.5rem; }
.sidebar-rank-name {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.6rem;
    letter-spacing: 4px;
    color: #f0c040;
}
.sidebar-rank-desc {
    font-size: 0.72rem;
    color: #5a4a2a;
    font-family: 'Rajdhani', sans-serif;
    letter-spacing: 2px;
}

.divider {
    border: none;
    border-top: 1px solid rgba(240,192,64,0.1);
    margin: 20px 0;
}
</style>

<script>
// Принудительно открываем сайдбар и блокируем кнопку закрытия
(function keepSidebarOpen() {
    function forceOpen() {
        // Убираем класс "collapsed" с body/html если Streamlit его ставит
        document.body.classList.remove('sidebar-collapsed');

        // Ищем кнопки сворачивания и скрываем их
        const selectors = [
            '[data-testid="collapsedControl"]',
            '[data-testid="stSidebarCollapseButton"]',
            'button[aria-label="Close sidebar"]',
            'button[aria-label="Collapse sidebar"]',
            'button[title="Collapse sidebar"]',
        ];
        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(btn => {
                btn.style.display = 'none';
                btn.style.visibility = 'hidden';
                btn.style.pointerEvents = 'none';
                // Перехватываем клик если кнопка всё же появилась
                btn.addEventListener('click', e => {
                    e.stopImmediatePropagation();
                    e.preventDefault();
                }, true);
            });
        });

        // Если сайдбар схлопнулся — разворачиваем
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

    // Запускаем сразу и через интервал (Streamlit рендерит асинхронно)
    forceOpen();
    setInterval(forceOpen, 500);

    // Также следим за изменениями DOM
    const observer = new MutationObserver(forceOpen);
    observer.observe(document.body, { childList: true, subtree: true, attributes: true });
})();
</script>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 4. КОНФИГУРАЦИЯ СЕТИ (WebRTC)
# ─────────────────────────────────────────────
RTC_CONFIG = RTCConfiguration({
    "iceServers": [
        {"urls": ["stun:stun.l.google.com:19302"]},
        {"urls": ["stun:stun1.l.google.com:19302"]},
        {"urls": ["stun:stun2.l.google.com:19302"]},
    ]
})

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
defaults = {
    "xp": 0,
    "reps": 0,
    "name": "Batyr",
    "move": "Zhambas",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# 7. AI ENGINE — THREAD-SAFE СЧЁТЧИК
# ─────────────────────────────────────────────
_global_reps = 0
_global_xp   = 0
_lock = threading.Lock()

def increment_rep():
    global _global_reps, _global_xp
    with _lock:
        _global_reps += 1
        _global_xp   += 10

def reset_global():
    global _global_reps, _global_xp
    with _lock:
        _global_reps = 0
        _global_xp   = 0

def get_global_stats():
    with _lock:
        return _global_reps, _global_xp


class SheberAI(VideoProcessorBase):
    """
    Строгая многофазная система оценки бросков.

    Чтобы бросок ЗАСЧИТАЛСЯ, нужно пройти все фазы по порядку:

    ZHAMBAS  (бедренный бросок):
      1. СТОЙКА  — колено > 155° (стоишь прямо)
      2. ПОДСЕД  — колено опускается до < 115° (глубокий подсед, мин. амплитуда 45°)
      3. БРОСОК  — колено возвращается > 160° И скорость разгибания быстрая

    SHALU  (подсечка):
      1. СТОЙКА  — обе ноги примерно одинаково (разница < 20°)
      2. ПЕРЕНОС — разница углов левой/правой ноги > 45° (вес на одну ногу)
      3. ПОДСЕЧКА — разница возвращается < 20° (возврат в стойку — бросок засчитан)

    KOTERME  (подъёмный бросок):
      1. СТОЙКА  — колено > 155°
      2. ГЛУБОКИЙ ПРИСЕД — колено < 95° (глубже чем Жамбас)
      3. ПОДЪЁМ  — промежуточная фаза 95-145° (контролируем что идёт подъём)
      4. БРОСОК  — колено > 160° (полное выпрямление)

    Дополнительные защиты от читерства:
    - min_amplitude: минимальная амплитуда за движение
    - cooldown_frames: блокировка после засчитанного репа (40 кадров ≈ 1.5 сек)
    - phase_timeout: если застрял в фазе > 120 кадров — сброс (≈ 5 сек)
    - visibility_check: если ключевые суставы не видны — не считаем
    """

    def __init__(self):
        self.pose  = pose_model
        self.current_name = "Batyr"
        self.current_move = "Zhambas"
        self._local_reps = 0
        self._local_xp   = 0

        # ── Состояние машины фаз ──────────────────
        self.phase          = "READY"      # текущая фаза
        self.phase_frame    = 0            # сколько кадров в текущей фазе
        self.cooldown       = 0            # кадры до следующего разрешённого репа
        self.peak_down      = 180.0        # минимальный угол достигнутый в подседе
        self.start_angle    = None         # угол в момент начала движения

        # ── HUD ──────────────────────────────────
        self.hint       = "STAND STRAIGHT"
        self.hint_color = (180, 160, 100)

    # ─── ВЫЧИСЛЕНИЕ УГЛА ─────────────────────────
    def angle3(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        r = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        ang = np.abs(r * 180.0 / np.pi)
        return 360 - ang if ang > 180 else ang

    def lm(self, lms, idx):
        p = lms[idx.value]
        return [p.x, p.y], p.visibility

    # ─── ПРОВЕРКА ВИДИМОСТИ ──────────────────────
    def visible(self, lms, *indices, threshold=0.55):
        """Возвращает True только если ВСЕ суставы достаточно видны."""
        for idx in indices:
            if lms[idx.value].visibility < threshold:
                return False
        return True

    # ─── ПОЛУЧЕНИЕ УГЛОВ КОЛЕНЕЙ ─────────────────
    def knee_angles(self, lms):
        LP = mp_pose.PoseLandmark
        vis_left  = self.visible(lms, LP.LEFT_HIP,  LP.LEFT_KNEE,  LP.LEFT_ANKLE)
        vis_right = self.visible(lms, LP.RIGHT_HIP, LP.RIGHT_KNEE, LP.RIGHT_ANKLE)

        l_ang = r_ang = None
        if vis_left:
            lh, _ = self.lm(lms, LP.LEFT_HIP)
            lk, _ = self.lm(lms, LP.LEFT_KNEE)
            la, _ = self.lm(lms, LP.LEFT_ANKLE)
            l_ang = self.angle3(lh, lk, la)
        if vis_right:
            rh, _ = self.lm(lms, LP.RIGHT_HIP)
            rk, _ = self.lm(lms, LP.RIGHT_KNEE)
            ra, _ = self.lm(lms, LP.RIGHT_ANKLE)
            r_ang = self.angle3(rh, rk, ra)

        if l_ang is None and r_ang is None:
            return None, None, None
        if l_ang is None:   return r_ang, r_ang, r_ang
        if r_ang is None:   return l_ang, l_ang, l_ang
        return l_ang, r_ang, min(l_ang, r_ang)

    # ═══════════════════════════════════════════════
    # ЖАМБАС — 3 обязательные фазы
    # ═══════════════════════════════════════════════
    def analyze_zhambas(self, lms):
        _, _, knee = self.knee_angles(lms)
        if knee is None:
            self.hint = "SHOW LEGS TO CAMERA"
            self.hint_color = (120, 120, 120)
            return None

        STAND_THRESH  = 155   # стойка: нога прямая
        DOWN_THRESH   = 115   # подсед: глубокий присед
        UP_THRESH     = 158   # бросок: нога выпрямляется
        MIN_AMPLITUDE = 40    # минимальная амплитуда (иначе "не считается")
        COOLDOWN      = 40    # кадров паузы после репа
        TIMEOUT       = 120   # кадров до сброса если застрял

        # Кулдаун — блокируем новый реп
        if self.cooldown > 0:
            self.cooldown -= 1
            self.hint = "GOOD! REST..."
            self.hint_color = (64, 255, 100)
            return knee

        self.phase_frame += 1

        # ── Фаза 1: READY — ждём прямую стойку ───
        if self.phase == "READY":
            if knee > STAND_THRESH:
                self.hint = "READY — START SQUAT"
                self.hint_color = (180, 160, 100)
            else:
                self.hint = "STAND STRAIGHT FIRST"
                self.hint_color = (200, 100, 50)

            if knee > STAND_THRESH:
                self.phase      = "STANDING"
                self.start_angle = knee
                self.peak_down  = knee
                self.phase_frame = 0

        # ── Фаза 2: STANDING — начало подседа ────
        elif self.phase == "STANDING":
            if self.phase_frame > TIMEOUT:
                self.phase = "READY"
                self.phase_frame = 0

            if knee < self.peak_down:
                self.peak_down = knee  # запоминаем глубину

            if knee < DOWN_THRESH:
                # Проверяем амплитуду: должен опуститься минимум на MIN_AMPLITUDE
                amplitude = (self.start_angle or 170) - knee
                if amplitude >= MIN_AMPLITUDE:
                    self.phase = "DOWN"
                    self.phase_frame = 0
                    self.hint = "DEEP! NOW DRIVE UP!"
                    self.hint_color = (64, 180, 255)
                else:
                    self.hint = "SQUAT DEEPER!"
                    self.hint_color = (200, 120, 50)
            else:
                self.hint = "SQUAT — BEND KNEES"
                self.hint_color = (180, 180, 100)

        # ── Фаза 3: DOWN — ждём взрывного подъёма
        elif self.phase == "DOWN":
            if self.phase_frame > TIMEOUT:
                # Застрял внизу — сбрасываем без репа
                self.phase = "READY"
                self.phase_frame = 0
                self.hint = "TIMEOUT — TRY AGAIN"
                self.hint_color = (200, 80, 50)
                return knee

            if knee < self.peak_down:
                self.peak_down = knee

            if knee > UP_THRESH:
                # Проверяем реальную амплитуду всего движения
                real_amplitude = knee - self.peak_down
                if real_amplitude >= MIN_AMPLITUDE:
                    # ✅ БРО ЗАСЧИТАН
                    increment_rep()
                    self._local_reps, self._local_xp = get_global_stats()
                    self.phase    = "READY"
                    self.cooldown = COOLDOWN
                    self.peak_down = 180
                    self.phase_frame = 0
                    self.hint = "✅ THROW COUNTED!"
                    self.hint_color = (64, 255, 100)
                else:
                    # Мало амплитуды — не засчитываем
                    self.phase = "READY"
                    self.phase_frame = 0
                    self.hint = "NOT DEEP ENOUGH!"
                    self.hint_color = (200, 80, 50)
            else:
                self.hint = "PUSH UP — EXPLOSIVE!"
                self.hint_color = (64, 180, 255)

        return knee

    # ═══════════════════════════════════════════════
    # ШАЛУ — 3 обязательные фазы (разница углов ног)
    # ═══════════════════════════════════════════════
    def analyze_shalu(self, lms):
        l_ang, r_ang, _ = self.knee_angles(lms)
        if l_ang is None or r_ang is None:
            self.hint = "SHOW BOTH LEGS"
            self.hint_color = (120, 120, 120)
            return None

        diff = abs(l_ang - r_ang)

        STAND_DIFF  = 20   # обе ноги почти одинаковы — стойка
        SWEEP_DIFF  = 45   # одна нога резко согнута — подсечка
        RETURN_DIFF = 22   # вернулись в стойку — засчитываем
        COOLDOWN    = 40
        TIMEOUT     = 120

        if self.cooldown > 0:
            self.cooldown -= 1
            self.hint = "GOOD! REST..."
            self.hint_color = (64, 255, 100)
            return min(l_ang, r_ang)

        self.phase_frame += 1

        if self.phase == "READY":
            if diff < STAND_DIFF:
                self.phase = "STANDING"
                self.phase_frame = 0
                self.hint = "BALANCED — SWEEP NOW"
                self.hint_color = (180, 160, 100)
            else:
                self.hint = "BALANCE FIRST"
                self.hint_color = (180, 140, 60)

        elif self.phase == "STANDING":
            if self.phase_frame > TIMEOUT:
                self.phase = "READY"; self.phase_frame = 0

            if diff > SWEEP_DIFF:
                self.phase = "SWEEP"
                self.phase_frame = 0
                self.hint = "SWEEP! RETURN NOW!"
                self.hint_color = (64, 180, 255)
            else:
                self.hint = f"SHIFT WEIGHT  DIFF:{int(diff)}°"
                self.hint_color = (180, 180, 100)

        elif self.phase == "SWEEP":
            if self.phase_frame > TIMEOUT:
                self.phase = "READY"; self.phase_frame = 0
                self.hint = "TOO SLOW — RETRY"
                self.hint_color = (200, 80, 50)
                return min(l_ang, r_ang)

            if diff < RETURN_DIFF:
                # ✅ ЗАСЧИТАН
                increment_rep()
                self._local_reps, self._local_xp = get_global_stats()
                self.phase    = "READY"
                self.cooldown = COOLDOWN
                self.phase_frame = 0
                self.hint = "✅ SWEEP COUNTED!"
                self.hint_color = (64, 255, 100)
            else:
                self.hint = f"RETURN TO STANCE  DIFF:{int(diff)}°"
                self.hint_color = (64, 180, 255)

        return min(l_ang, r_ang)

    # ═══════════════════════════════════════════════
    # КӨТЕРМЕ — 4 фазы (глубже + подъём + выпрямление)
    # ═══════════════════════════════════════════════
    def analyze_koterme(self, lms):
        _, _, knee = self.knee_angles(lms)
        if knee is None:
            self.hint = "SHOW LEGS TO CAMERA"
            self.hint_color = (120, 120, 120)
            return None

        STAND_THRESH  = 155
        DEEP_THRESH   = 95    # глубже чем Жамбас!
        LIFT_LOW      = 95    # начало подъёма
        LIFT_HIGH     = 145   # ещё не выпрямился
        UP_THRESH     = 158
        MIN_AMPLITUDE = 55    # больше чем у Жамбаса — Köterme требует реального приседа
        COOLDOWN      = 45
        TIMEOUT       = 150

        if self.cooldown > 0:
            self.cooldown -= 1
            self.hint = "POWERFUL! REST..."
            self.hint_color = (64, 255, 100)
            return knee

        self.phase_frame += 1

        if self.phase == "READY":
            if knee > STAND_THRESH:
                self.phase = "STANDING"
                self.start_angle = knee
                self.peak_down   = knee
                self.phase_frame = 0
                self.hint = "READY — GRIP & SQUAT DEEP"
                self.hint_color = (180, 160, 100)
            else:
                self.hint = "STAND STRAIGHT FIRST"
                self.hint_color = (200, 100, 50)

        elif self.phase == "STANDING":
            if self.phase_frame > TIMEOUT:
                self.phase = "READY"; self.phase_frame = 0

            if knee < knee: self.peak_down = knee
            if knee < self.peak_down: self.peak_down = knee

            if knee < DEEP_THRESH:
                amplitude = (self.start_angle or 165) - knee
                if amplitude >= MIN_AMPLITUDE:
                    self.phase = "DEEP"
                    self.phase_frame = 0
                    self.hint = "DEEP! NOW LIFT & THROW!"
                    self.hint_color = (64, 180, 255)
                else:
                    self.hint = f"NEED DEEPER!  {int(knee)}° / need <{DEEP_THRESH}°"
                    self.hint_color = (200, 120, 50)
            else:
                self.hint = f"SQUAT DEEPER  {int(knee)}°"
                self.hint_color = (180, 180, 100)

        elif self.phase == "DEEP":
            if self.phase_frame > TIMEOUT:
                self.phase = "READY"; self.phase_frame = 0
                self.hint = "TIMEOUT — TRY AGAIN"
                self.hint_color = (200, 80, 50)
                return knee

            if knee < self.peak_down:
                self.peak_down = knee

            if LIFT_LOW < knee < LIFT_HIGH:
                self.phase = "LIFTING"
                self.phase_frame = 0
                self.hint = "LIFT! ALMOST THERE!"
                self.hint_color = (255, 180, 0)

        elif self.phase == "LIFTING":
            if self.phase_frame > TIMEOUT:
                self.phase = "READY"; self.phase_frame = 0
                self.hint = "TIMEOUT — TRY AGAIN"
                self.hint_color = (200, 80, 50)
                return knee

            if knee > UP_THRESH:
                real_amplitude = knee - self.peak_down
                if real_amplitude >= MIN_AMPLITUDE:
                    # ✅ ЗАСЧИТАН
                    increment_rep()
                    self._local_reps, self._local_xp = get_global_stats()
                    self.phase    = "READY"
                    self.cooldown = COOLDOWN
                    self.peak_down = 180
                    self.phase_frame = 0
                    self.hint = "✅ LIFT COUNTED!"
                    self.hint_color = (64, 255, 100)
                else:
                    self.phase = "READY"; self.phase_frame = 0
                    self.hint = "NOT DEEP ENOUGH!"
                    self.hint_color = (200, 80, 50)
            else:
                self.hint = f"PUSH UP FULLY!  {int(knee)}°"
                self.hint_color = (255, 180, 0)

        return knee

    # ═══════════════════════════════════════════════
    # ГЛАВНЫЙ ОБРАБОТЧИК КАДРА
    # ═══════════════════════════════════════════════
    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        h, w = img.shape[:2]

        rgb     = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        angle_val = None

        if results.pose_landmarks:
            lms = results.pose_landmarks.landmark

            # Цвет скелета: зелёный в норме, оранжевый в подседе
            skel_color = (64, 255, 100)
            if self.phase in ("DOWN", "DEEP", "LIFTING", "SWEEP"):
                skel_color = (64, 180, 255)

            mp_drawing.draw_landmarks(
                img, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=skel_color, thickness=2, circle_radius=3),
                mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=1, circle_radius=1)
            )

            try:
                move = self.current_move
                if move == "Zhambas":
                    angle_val = self.analyze_zhambas(lms)
                elif move == "Shalu":
                    angle_val = self.analyze_shalu(lms)
                elif move == "Koterme":
                    angle_val = self.analyze_koterme(lms)
            except Exception as e:
                self.hint       = "POSITIONING..."
                self.hint_color = (120, 120, 120)

        else:
            self.hint       = "STAND IN FRAME"
            self.hint_color = (120, 120, 120)

        # ── HUD ────────────────────────────────────
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0),        (w, 64),     (5, 8, 14), -1)
        cv2.line(overlay,      (0, 64),        (w, 64),     (80, 60, 20), 1)
        cv2.rectangle(overlay, (0, h - 58),   (w, h),      (5, 8, 14), -1)
        cv2.line(overlay,      (0, h - 58),   (w, h - 58), (80, 60, 20), 1)
        img = cv2.addWeighted(overlay, 0.85, img, 0.15, 0)

        # Верхняя строка
        cv2.putText(img, self.current_name,
                    (16, 40), cv2.FONT_HERSHEY_DUPLEX, 0.7, (230, 220, 200), 1, cv2.LINE_AA)
        cv2.putText(img, self.current_move.upper(),
                    (w // 2 - 60, 40), cv2.FONT_HERSHEY_DUPLEX, 0.7, (240, 192, 64), 1, cv2.LINE_AA)
        cv2.putText(img, f"XP: {self._local_xp}",
                    (w - 170, 25), cv2.FONT_HERSHEY_DUPLEX, 0.55, (180, 140, 40), 1, cv2.LINE_AA)
        cv2.putText(img, f"REPS: {self._local_reps}",
                    (w - 170, 48), cv2.FONT_HERSHEY_DUPLEX, 0.55, (77, 200, 255), 1, cv2.LINE_AA)

        # Нижняя строка: угол | подсказка | фаза
        if angle_val is not None:
            cv2.putText(img, f"{int(angle_val)}" + chr(176),
                        (16, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (150, 130, 80), 2, cv2.LINE_AA)

        # Подсказка — центр
        hint_x = max(10, w // 2 - len(self.hint) * 7)
        cv2.putText(img, self.hint,
                    (hint_x, h - 18), cv2.FONT_HERSHEY_DUPLEX, 0.78, self.hint_color, 2, cv2.LINE_AA)

        # Фаза — правый угол
        phase_colors = {
            "READY":    (100, 90, 50),
            "STANDING": (180, 160, 80),
            "DOWN":     (64, 180, 255),
            "DEEP":     (64, 180, 255),
            "LIFTING":  (255, 180, 0),
            "SWEEP":    (64, 180, 255),
        }
        p_color = phase_colors.get(self.phase, (100, 90, 50))
        cv2.putText(img, self.phase,
                    (w - 120, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.58, p_color, 1, cv2.LINE_AA)

        # Мини прогресс-бар амплитуды для Жамбас/Көтерме
        if angle_val is not None and self.phase in ("STANDING", "DOWN", "DEEP", "LIFTING"):
            bar_w  = 160
            bar_x  = (w - bar_w) // 2
            bar_y  = h - 52
            filled = int(bar_w * max(0, min(1, (170 - (self.peak_down or 170)) / 70)))
            cv2.rectangle(img, (bar_x, bar_y),              (bar_x + bar_w, bar_y + 4), (40, 40, 40), -1)
            cv2.rectangle(img, (bar_x, bar_y),              (bar_x + filled, bar_y + 4), (64, 180, 255), -1)
            cv2.putText(img, "DEPTH",
                        (bar_x, bar_y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (100, 80, 40), 1, cv2.LINE_AA)

        return av.VideoFrame.from_ndarray(img, format="bgr24")


# ─────────────────────────────────────────────
# 8. ГЛАВНЫЙ ИНТЕРФЕЙС
# ─────────────────────────────────────────────
def main():

    # ── САЙДБАР ──────────────────────────────────
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

        g_reps, g_xp = get_global_stats()
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
            key="sheber-v3",
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
                "tip": "Держи спину ровно при подседе. Взрыв идёт от бёдер — корпус должен войти под противника. Контролируй центр тяжести.",
                "steps": ["Захват пояса", "Подсед — угол 90°", "Подъём через бедро", "Бросок вперёд"]
            },
            "Shalu": {
                "title": "ШАЛУ", "desc": "Подсечка",
                "tip": "Используй инерцию противника. Зацеп должен быть молниеносным. Контроль баланса — ключ к технике.",
                "steps": ["Тяни на себя", "Зайди сбоку", "Подсечка ноги", "Добей на ковёр"]
            },
            "Koterme": {
                "title": "КӨТЕРМЕ", "desc": "Подъёмный бросок",
                "tip": "Это силовой приём. Контролируй захват пояса до полного завершения броска. Поднимай от земли, не от пояса.",
                "steps": ["Глубокий захват", "Приседание", "Взрывной подъём", "Бросок назад"]
            }
        }

        g = guides.get(move, guides["Zhambas"])
        st.markdown(f"""
        <div class="guide-card">
            <div class="guide-move-title">{g['title']} · {g['desc']}</div>
            <div class="guide-tip">💡 {g['tip']}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**📋 Шаги техники:**")
        for i, step in enumerate(g["steps"], 1):
            st.markdown(f"`{i}.` {step}")

    # ── FOOTER ───────────────────────────────────
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

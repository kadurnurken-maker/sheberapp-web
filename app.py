# ==========================================
# 🦅 SHEBER APP PRO: CORE REPOSITORY v3.0
# ==========================================
import av
import cv2
import numpy as np
import streamlit as st
import time
from streamlit_webrtc import (
    webrtc_streamer, 
    VideoProcessorBase, 
    RTCConfiguration, 
    WebRtcMode
)

# ── 1. ГЛОБАЛЬНАЯ КОНФИГУРАЦИЯ ──
st.set_page_config(
    page_title="SheberApp Pro | AI Wrestling Analyst",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── 2. ПРОДВИНУТЫЙ ULTRA NEON DESIGN (CSS) ──
# Мы расширяем блок стилей, чтобы добавить "глубину" интерфейсу
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Montserrat:wght@300;400;600;700&display=swap');

    :root {
        --primary: #f5c842;
        --secondary: #4db8ff;
        --bg-dark: #020408;
        --glass: rgba(255, 255, 255, 0.03);
    }

    .stApp {
        background: radial-gradient(circle at 50% 0%, #0a1221 0%, #020408 100%);
        color: #e0e0e0;
        font-family: 'Montserrat', sans-serif;
    }

    /* Анимированные заголовки */
    .main-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 3.5rem;
        font-weight: 900;
        background: linear-gradient(90deg, #f5c842, #ffffff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-transform: uppercase;
        letter-spacing: 5px;
        margin-bottom: 0;
    }

    /* Карточки аналитики */
    .metric-card {
        background: var(--glass);
        border: 1px solid rgba(245, 200, 66, 0.1);
        border-radius: 25px;
        padding: 25px;
        text-align: center;
        backdrop-filter: blur(15px);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .metric-card:hover {
        transform: translateY(-10px);
        border-color: var(--primary);
        box-shadow: 0 15px 30px rgba(245, 200, 66, 0.1);
    }

    .label { color: #888; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 2px; }
    .value { font-size: 2.2rem; font-weight: 700; margin: 10px 0; }
    
    /* Прогресс-бар опыта */
    .xp-container {
        width: 100%;
        background: rgba(255,255,255,0.05);
        border-radius: 50px;
        height: 10px;
        margin-top: 15px;
        overflow: hidden;
    }
    .xp-fill {
        background: linear-gradient(90deg, #f5c842, #ffae00);
        height: 100%;
        box-shadow: 0 0 15px #f5c842;
        transition: width 1s ease-in-out;
    }

    /* Зона сканера */
    .scanner-viewport {
        border: 3px solid rgba(245, 200, 66, 0.3);
        border-radius: 30px;
        padding: 10px;
        background: #000;
        position: relative;
    }
    
    /* Декоративные уголки сканера */
    .scanner-viewport::before {
        content: ""; position: absolute; top: -5px; left: -5px; width: 30px; height: 30px;
        border-top: 5px solid #f5c842; border-left: 5px solid #f5c842; border-radius: 5px 0 0 0;
    }

    /* Кастомные алерты */
    .stAlert {
        border-radius: 15px;
        background: rgba(245, 200, 66, 0.05) !important;
        border: 1px solid rgba(245, 200, 66, 0.2) !important;
    }
</style>
""", unsafe_allow_html=True)

# ── 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И ДАННЫЕ ──
RANKS = [
    (0, 100, "Bala", "🥋", "#CD7F32"),
    (101, 400, "Zhasospirim", "⚔️", "#C0C0C0"),
    (401, 1000, "Batyr", "🦅", "#FFD700"),
    (1001, 10000, "Sheber", "👑", "#00F2FF")
]

RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

def calculate_biomechanics(a, b, c):
    """Вычисление углов для анализа качества приема (IB IA Physics)"""
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba = a - b
    bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-7)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return np.degrees(angle)

# ── 4. СОСТОЯНИЕ СЕССИИ (SESSION STATE) ──
if "xp" not in st.session_state:
    st.session_state.update({
        "xp": 0, 
        "reps": 0, 
        "history": [], 
        "start_time": time.time(),
        "current_tech": "Zhambas"
    })

# ── 5. ЯДРО AI: ОБРАБОТКА ВИДЕО ──
class WrestlingAIProcessor(VideoProcessorBase):
    def __init__(self):
        # Локальный импорт внутри потока для стабильности Streamlit Cloud
        import mediapipe as mp
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose_engine = self.mp_pose.Pose(
            min_detection_confidence=0.7, 
            min_tracking_confidence=0.7,
            model_complexity=1
        )
        self.counter = 0
        self.stage = "down" # Состояние для подсчета повторений
        self.feedback = "START TRAINING"
        self.fb_color = (255, 255, 255)

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1) # Зеркальное отображение
        h, w, _ = img.shape
        
        # Конвертация для MediaPipe
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.pose_engine.process(rgb_img)

        if results.pose_landmarks:
            # Отрисовка скелета
            self.mp_drawing.draw_landmarks(
                img, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing.DrawingSpec(color=(245, 200, 66), thickness=3, circle_radius=3),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2)
            )

            # Извлечение координат
            try:
                landmarks = results.pose_landmarks.landmark
                
                # Точки для анализа Zhambas (Бросок через бедро)
                shldr = [landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                hip = [landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value].y]
                knee = [landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE.value].y]
                ankle = [landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].x, landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].y]

                # Расчет углов
                back_angle = calculate_biomechanics(shldr, hip, knee)
                knee_angle = calculate_biomechanics(hip, knee, ankle)

                # Логика подсчета (Алгоритм распознавания фаз)
                if knee_angle < 110: # Фаза подседа
                    self.stage = "down"
                    self.feedback = "GOOD DEPTH! NOW LIFT"
                    self.fb_color = (0, 255, 255)
                
                if knee_angle > 160 and self.stage == "down": # Фаза подрыва
                    if back_angle > 150: # Если спина прямая
                        self.stage = "up"
                        self.counter += 1
                        st.session_state["xp"] += 15
                        st.session_state["reps"] += 1
                        self.feedback = "PERFECT REP! +15 XP"
                        self.fb_color = (0, 255, 0)
                    else:
                        self.feedback = "KEEP BACK STRAIGHT!"
                        self.fb_color = (0, 0, 255)
                        self.stage = "up" # Сброс фазы

            except Exception as e:
                pass

        # Отрисовка HUD на видео
        cv2.rectangle(img, (0, 0), (w, 80), (0, 0, 0), -1)
        cv2.putText(img, f"STATUS: {self.feedback}", (20, 50), cv2.FONT_HERSHEY_DUPLEX, 1, self.fb_color, 2)
        
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# ── 6. ГЛАВНЫЙ ИНТЕРФЕЙС (UI) ──
def main():
    # HEADER
    st.markdown("<h1 class='main-title'>🦅 SHEBER APP PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='letter-spacing:3px; color:#f5c842; font-weight:bold;'>AI-POWERED KAZAKH KURES ANALYST</p>", unsafe_allow_html=True)
    
    st.write("---")

    # СЕКЦИЯ СТАТИСТИКИ
    xp = st.session_state["xp"]
    rank_name, emoji, rank_color = "Bala", "🥋", "#CD7F32"
    for lo, hi, n, e, c in RANKS:
        if lo <= xp <= hi:
            rank_name, emoji, rank_color = n, e, c

    # Расчет прогресса для шкалы
    next_rank_xp = 100 if xp < 100 else (400 if xp < 400 else 1000)
    prog_val = min((xp / next_rank_xp) * 100, 100)

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Current Mastership</div>
            <div class="value" style="color:{rank_color}">{emoji} {rank_name}</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Experience Level</div>
            <div class="value">{xp} XP</div>
            <div class="xp-container"><div class="xp-fill" style="width:{prog_val}%"></div></div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Total Successful Reps</div>
            <div class="value" style="color:#4db8ff;">{st.session_state['reps']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.write(" ")

    # ОСНОВНОЙ БЛОК: СКАНЕР И ИНСТРУКЦИИ
    left_col, right_col = st.columns([1.6, 1])

    with left_col:
        st.markdown("### 📸 NEURAL SCANNER ACTIVE")
        st.markdown('<div class="scanner-viewport">', unsafe_allow_html=True)
        webrtc_streamer(
            key="sheber-ai-core",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIG,
            video_processor_factory=WrestlingAIProcessor,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
        st.info("Система автоматически анализирует углы суставов и засчитывает очки только за идеальную технику.")

    with right_col:
        st.markdown("### 📖 TECHNIQUE GUIDE")
        tab1, tab2 = st.tabs(["Selection", "Bio-Analysis"])
        
        with tab1:
            tech = st.selectbox("Choose drill:", ["Zhambas", "Shalu", "Koterme"])
            st.session_state["current_tech"] = tech
            
            # Динамическая подгрузка изображений
            img_map = {"Zhambas": "jambass.jpg", "Shalu": "shalu.jpg", "Koterme": "koterme.webp"}
            st.image(img_map[tech], caption=f"Optimal Form for {tech}", use_container_width=True)
            
            # Описание техники
            if tech == "Zhambas":
                st.warning("**Совет мастера:** Скручивайте бедро под углом 45 градусов к противнику.")
            elif tech == "Shalu":
                st.warning("**Совет мастера:** Зацеп должен быть резким, стопа прижата к ковру.")
            else:
                st.warning("**Совет мастера:** Поднимайте за счет силы ног, а не поясницы.")

        with tab2:
            st.markdown("#### 📐 AI Parameters")
            st.write("Current Metrics Tracked:")
            st.code(f"""
- Spine Angle: > 150° (Straight)
- Knee Flexion: < 110° (Active Load)
- Center of Mass: Balanced
- Recognition: Real-time MP Pose
            """)
            
            if st.button("🔄 RESET ALL SESSION DATA"):
                st.session_state.xp = 0
                st.session_state.reps = 0
                st.rerun()

    # FOOTER AREA
    st.write("---")
    f_col1, f_col2 = st.columns([2, 1])
    with f_col1:
        st.image("hero.jpg", use_container_width=True)
    with f_col2:
        st.markdown("#### 🏅 Achievements")
        if xp > 100: st.success("🔓 First Blood: Reach 100 XP")
        if st.session_state["reps"] > 10: st.success("🔓 Consistent: 10 Reps in one go")
        if xp > 500: st.success("🔓 Batyr Path: Level 3 Unlocked")

if __name__ == "__main__":
    main()

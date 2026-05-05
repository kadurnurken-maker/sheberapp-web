import av
import cv2
import numpy as np
import streamlit as st
import time
import logging
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration, WebRtcMode

# Настройка логирования для чистоты консоли
logging.basicConfig(level=logging.WARNING)

# 1. СТРОГАЯ КОНФИГУРАЦИЯ
st.set_page_config(
    page_title="SHEBER AI PRO | Digital Coach",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. ULTRA NEON DESIGN (CSS)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600&display=swap');

    .stApp {
        background: #05070a;
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }

    /* Заголовок */
    .hero-title {
        font-family: 'Orbitron', sans-serif;
        background: linear-gradient(90deg, #f5c842, #ffae00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 900;
        text-align: center;
        letter-spacing: 3px;
        margin-top: -50px;
    }

    /* Карточки статистики */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(245, 200, 66, 0.2);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
    }
    
    .metric-label { color: #888; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-family: 'Orbitron', sans-serif; font-size: 1.6rem; color: #f5c842; margin-top: 5px; }

    /* Прогресс-бар */
    .xp-bar-outer {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 50px;
        height: 8px;
        width: 100%;
        margin-top: 10px;
    }
    .xp-bar-inner {
        background: linear-gradient(90deg, #f5c842, #ffae00);
        height: 100%;
        border-radius: 50px;
        box-shadow: 0 0 15px rgba(245, 200, 66, 0.4);
    }

    /* Видео-контейнер */
    .video-container {
        border: 2px solid #f5c842;
        border-radius: 25px;
        overflow: hidden;
        background: #000;
        box-shadow: 0 0 30px rgba(245, 200, 66, 0.1);
    }

    /* Сайдбар */
    [data-testid="stSidebar"] {
        background-color: #0a0f18;
        border-right: 1px solid rgba(245, 200, 66, 0.2);
    }

    /* Кнопки */
    .stButton>button {
        border-radius: 10px !important;
        background: linear-gradient(90deg, #f5c842, #ffae00) !important;
        color: #000 !important;
        font-weight: 700 !important;
        border: none !important;
        font-family: 'Orbitron', sans-serif;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 3. ИНИЦИАЛИЗАЦИЯ ДАННЫХ
if "xp" not in st.session_state:
    st.session_state.update({
        "xp": 0, 
        "reps": 0, 
        "user_name": "Batyr",
        "selected_move": "Zhambas"
    })

RANKS = [
    (0, 100, "BALA", "🥋"),
    (101, 500, "ZHASOSPIRIM", "⚔️"),
    (501, 1500, "BATYR", "🦅"),
    (1501, 10000, "SHEBER", "👑")
]

RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

# 4. AI ENGINE (ОПТИМИЗИРОВАННЫЙ)
class SheberAI(VideoProcessorBase):
    def __init__(self):
        import mediapipe as mp
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(
            model_complexity=0, # Для скорости
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.stage = None
        self.hint = "WAITING..."

    def find_angle(self, a, b, c):
        a = np.array(a); b = np.array(b); c = np.array(c)
        rad = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        deg = np.abs(rad*180.0/np.pi)
        return deg if deg <= 180 else 360-deg

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        h, w, _ = img.shape
        
        results = self.pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                img, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=(245, 200, 66), thickness=2, circle_radius=2),
                self.mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=1)
            )
            
            try:
                lms = results.pose_landmarks.landmark
                # Логика анализа подседов
                hip = [lms[self.mp_pose.PoseLandmark.LEFT_HIP.value].x, lms[self.mp_pose.PoseLandmark.LEFT_HIP.value].y]
                knee = [lms[self.mp_pose.PoseLandmark.LEFT_KNEE.value].x, lms[self.mp_pose.PoseLandmark.LEFT_KNEE.value].y]
                ankle = [lms[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].x, lms[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
                
                angle = self.find_angle(hip, knee, ankle)

                if angle < 110: 
                    self.stage = "down"
                    self.hint = "PUSH UP!"
                if angle > 160 and self.stage == "down":
                    self.stage = "up"
                    st.session_state["xp"] += 15
                    st.session_state["reps"] += 1
                    self.hint = "EXCELLENT!"
            except: pass

        # Отрисовка HUD (Интерфейс внутри видео)
        cv2.rectangle(img, (0,0), (w, 60), (0,0,0), -1)
        cv2.putText(img, f"PLAYER: {st.session_state['user_name']}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
        cv2.putText(img, f"MOVE: {st.session_state['selected_move']}", (w//2, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (245, 200, 66), 2)
        cv2.putText(img, self.hint, (w-180, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# 5. ГЛАВНЫЙ ИНТЕРФЕЙС
def main():
    # САЙДБАР: ВВОД ДАННЫХ
    with st.sidebar:
        st.markdown("### 👤 PROFILE SETUP")
        st.session_state["user_name"] = st.text_input("Enter Warrior Name:", value="Batyr")
        st.session_state["selected_move"] = st.selectbox(
            "Select Your Throw:", 
            ["Zhambas", "Shalu", "Koterme", "Belbeu"]
        )
        st.write("---")
        st.markdown("#### ⚙️ Settings")
        st.checkbox("Show Skeleton", value=True)
        if st.button("RESET SESSION"):
            st.session_state.xp = 0
            st.session_state.reps = 0
            st.rerun()

    # HEADER
    st.markdown("<h1 class='hero-title'>🦅 SHEBER AI PRO</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:#888;'>Welcome, <b>{st.session_state['user_name']}</b>! Prepare for {st.session_state['selected_move']}.</p>", unsafe_allow_html=True)

    # STATISTICS
    xp = st.session_state["xp"]
    rank_name, emoji = "BALA", "🥋"
    for lo, hi, n, e in RANKS:
        if lo <= xp <= hi: rank_name, emoji = n, e
    
    next_goal = 100 if xp < 100 else (500 if xp < 500 else 1500)
    prog = min((xp / next_goal) * 100, 100)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='glass-card'><div class='metric-label'>Rank</div><div class='metric-value'>{emoji} {rank_name}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>Total Experience</div>
            <div class='metric-value'>{xp} XP</div>
            <div class='xp-bar-outer'><div class='xp-bar-inner' style='width:{prog}%'></div></div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='glass-card'><div class='metric-label'>Reps Count</div><div class='metric-value' style='color:#4db8ff;'>{st.session_state['reps']}</div></div>", unsafe_allow_html=True)

    st.write(" ")

    # MAIN WORKSPACE
    col_vid, col_info = st.columns([1.7, 1])

    with col_vid:
        st.markdown(f"### 🛰️ LIVE ANALYZING: {st.session_state['selected_move']}")
        st.markdown('<div class="video-container">', unsafe_allow_html=True)
        webrtc_streamer(
            key="sheber-main",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIG,
            video_processor_factory=SheberAI,
            media_stream_constraints={"video": {"width": 1280, "height": 720}, "audio": False},
            async_processing=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_info:
        st.markdown("### 📖 MASTER GUIDE")
        
        # Динамическая инструкция
        move = st.session_state["selected_move"]
        img_map = {"Zhambas": "jambass.jpg", "Shalu": "shalu.jpg", "Koterme": "koterme.webp", "Belbeu": "hero.jpg"}
        
        st.image(img_map.get(move, "hero.jpg"), use_container_width=True)
        
        tips = {
            "Zhambas": "Сфокусируйтесь на плотном захвате пояса. Подсед должен быть глубоким.",
            "Shalu": "Используйте инерцию противника. Зацеп делайте резким движением стопы.",
            "Koterme": "Спина должна оставаться ровной. Основная нагрузка на ноги.",
            "Belbeu": "Контролируйте центр тяжести противника через плотный обхват."
        }
        
        st.success(f"**Coach Tip:** {tips.get(move)}")
        
        st.markdown("#### 🎯 Session Goals")
        st.write(f"- Complete 10 {move} throws")
        st.write("- Keep spine angle > 160°")
        st.write("- Reach next rank level")

    st.write("---")
    st.image("hero.jpg", use_container_width=True)

if __name__ == "__main__":
    main()

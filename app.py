import streamlit as st
import mediapipe as mp
import cv2
import numpy as np
import av
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration, WebRtcMode
import threading

# 1. ОСНОВНЫЕ НАСТРОЙКИ
st.set_page_config(page_title="SHEBER", page_icon="🦅", layout="wide")

# Инициализация данных
if "xp" not in st.session_state: st.session_state.xp = 0
if "reps" not in st.session_state: st.session_state.reps = 0

# Мост для передачи данных между видео и интерфейсом
lock = threading.Lock()
class SharedData:
    new_reps = 0
    new_xp = 0
shared = SharedData()

# 2. ЧИСТЫЙ ДИЗАЙН (CSS)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700&display=swap');
    
    .stApp { background-color: #0e1117; color: #e0e0e0; font-family: 'Inter', sans-serif; }
    
    /* Заголовок */
    .main-title {
        font-weight: 700; font-size: 3rem; color: #D4AF37;
        text-align: center; margin-bottom: 2rem; letter-spacing: 2px;
    }
    
    /* Карточки статистики */
    .stat-card {
        background: #1c1f26; border-radius: 15px; padding: 1.5rem;
        border-top: 3px solid #D4AF37; text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .stat-label { font-size: 0.8rem; color: #888; text-transform: uppercase; margin-bottom: 5px; }
    .stat-value { font-size: 1.8rem; font-weight: 700; color: #ffffff; }

    /* Видео-контейнер */
    .video-container { border: 1px solid #30363d; border-radius: 20px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# 3. ЛОГИКА ТРЕНИРОВКИ (AI)
class SheberEngine(VideoProcessorBase):
    def __init__(self):
        self.pose = mp.solutions.pose.Pose(model_complexity=0, min_detection_confidence=0.5)
        self.stage = "up"
        self.current_move = "Zhambas"

    def calculate_angle(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = np.abs(radians*180.0/np.pi)
        return angle if angle <= 180.0 else 360-angle

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        results = self.pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        if results.pose_landmarks:
            lms = results.pose_landmarks.landmark
            try:
                # Колено, бедро, лодыжка (для Жамбас)
                hip = [lms[23].x, lms[23].y]
                knee = [lms[25].x, lms[25].y]
                ankle = [lms[27].x, lms[27].y]
                
                angle = self.calculate_angle(hip, knee, ankle)

                # Логика Жамбас (присед)
                if self.current_move == "Zhambas":
                    if angle < 110: self.stage = "down"
                    if angle > 160 and self.stage == "down":
                        self.stage = "up"
                        with lock:
                            shared.new_reps += 1
                            shared.new_xp += 15
                
                # Рисуем скелет
                mp.solutions.drawing_utils.draw_landmarks(img, results.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
            except: pass

        return av.VideoFrame.from_ndarray(img, format="bgr24")

# 4. ИНТЕРФЕЙС
def main():
    st.markdown("<h1 class='main-title'>SHEBER</h1>", unsafe_allow_html=True)

    # Обновляем статистику из буфера
    with lock:
        st.session_state.reps += shared.new_reps
        st.session_state.xp += shared.new_xp
        shared.new_reps = 0
        shared.new_xp = 0

    # Рейтинг
    xp = st.session_state.xp
    rank = "BALA" if xp < 100 else ("ZHASOSPIRIM" if xp < 500 else "BATYR")

    # Верхняя панель статистики
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Rank</div><div class='stat-value'>{rank}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Total XP</div><div class='stat-value'>{xp}</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Reps Done</div><div class='stat-value'>{st.session_state.reps}</div></div>", unsafe_allow_html=True)

    st.write("---")

    # Рабочая зона
    v_col, g_col = st.columns([2, 1])

    with v_col:
        st.subheader("Live Training")
        ctx = webrtc_streamer(
            key="sheber-main",
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=SheberEngine,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": {"width": 640, "height": 480}, "audio": False},
            async_processing=True
        )

    with g_col:
        st.subheader("Settings")
        move = st.selectbox("Current Drill", ["Zhambas", "Shalu", "Koterme"])
        if ctx.video_processor:
            ctx.video_processor.current_move = move
        
        st.info(f"Выполняй {move}, следи за осанкой. Система зачислит +15 XP за каждый четкий повтор.")
        
        if st.button("Reset Session"):
            st.session_state.xp = 0
            st.session_state.reps = 0
            st.rerun()

if __name__ == "__main__":
    main()

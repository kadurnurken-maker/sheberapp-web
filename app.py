import os

# КРИТИЧЕСКИЙ ФИКС: Указываем MediaPipe использовать /tmp ДО импорта библиотек
os.environ['MEDIAPIPE_MODEL_PATH'] = '/tmp/'

import urllib.request
import streamlit as st
import mediapipe as mp
import cv2
import numpy as np
import av
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration, WebRtcMode

# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ
st.set_page_config(
    page_title="SHEBER AI PRO",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. ИСПРАВЛЕНИЕ PERMISSION ERROR
@st.cache_resource
def get_mp_pose():
    model_dir = "/tmp/mediapipe_models"
    model_path = os.path.join(model_dir, "pose_landmark_lite.tflite")
    
    if not os.path.exists(model_dir):
        os.makedirs(model_dir, exist_ok=True)
        
    model_url = "https://storage.googleapis.com/mediapipe-assets/pose_landmark_lite.tflite"
    
    if not os.path.exists(model_path):
        try:
            urllib.request.urlretrieve(model_url, model_path)
        except Exception as e:
            st.error(f"Error downloading model: {e}")

    # Инициализация Pose
    return mp.solutions.pose.Pose(
        model_complexity=0, 
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

# Инициализация модели и инструментов рисования
pose_model = get_mp_pose()
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# 3. PREMIUM DARK DESIGN (CSS) - Без изменений
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600&display=swap');
    .stApp { background: #05070a; color: #ffffff; font-family: 'Inter', sans-serif; }
    .hero-title {
        font-family: 'Orbitron', sans-serif;
        background: linear-gradient(90deg, #f5c842, #ffae00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.2rem;
        font-weight: 900;
        text-align: center;
        filter: drop-shadow(0 0 10px rgba(245, 200, 66, 0.3));
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(245, 200, 66, 0.2);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        backdrop-filter: blur(15px);
    }
    .metric-val {
        font-family: 'Orbitron', sans-serif;
        font-size: 1.8rem;
        color: #f5c842;
        text-shadow: 0 0 10px rgba(245, 200, 66, 0.5);
    }
    .xp-outer { background: rgba(255,255,255,0.1); border-radius: 10px; height: 10px; margin-top: 10px; overflow: hidden; }
    .xp-inner { background: linear-gradient(90deg, #f5c842, #ffae00); height: 100%; }
    .video-box { border: 2px solid #f5c842; border-radius: 25px; overflow: hidden; }
    [data-testid="stSidebar"] { background-color: #0a0f18; border-right: 1px solid rgba(245, 200, 66, 0.2); }
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #f5c842, #ffae00) !important;
        color: black !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        font-family: 'Orbitron', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# 4. СЕТЬ
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

# 5. ДАННЫЕ СЕССИИ
if "xp" not in st.session_state:
    st.session_state.update({"xp": 0, "reps": 0, "name": "Batyr", "move": "Zhambas"})

# 6. AI ENGINE
class SheberAI(VideoProcessorBase):
    def __init__(self):
        self.pose = pose_model
        self.stage = None
        self.hint = "READY"

    def calculate_angle(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = np.abs(radians*180.0/np.pi)
        return angle if angle <= 180.0 else 360-angle

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        h, w, _ = img.shape
        
        results = self.pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                img, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(245, 200, 66), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=1)
            )
            
            try:
                lms = results.pose_landmarks.landmark
                hip = [lms[mp_pose.PoseLandmark.LEFT_HIP.value].x, lms[mp_pose.PoseLandmark.LEFT_HIP.value].y]
                knee = [lms[mp_pose.PoseLandmark.LEFT_KNEE.value].x, lms[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
                ankle = [lms[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, lms[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
                
                angle = self.calculate_angle(hip, knee, ankle)

                if angle < 110: 
                    self.stage = "down"
                    self.hint = "PUSH UP!"
                if angle > 160 and self.stage == "down":
                    self.stage = "up"
                    st.session_state["xp"] += 10
                    st.session_state["reps"] += 1
                    self.hint = "PERFECT!"
            except: pass

        # HUD
        cv2.rectangle(img, (0, 0), (w, 60), (0, 0, 0), -1)
        cv2.putText(img, f"WARRIOR: {st.session_state['name']}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(img, f"TASK: {st.session_state['move']}", (w//2 - 60, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (245, 200, 66), 2)
        cv2.putText(img, self.hint, (w-150, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# 7. ГЛАВНЫЙ ИНТЕРФЕЙС
def main():
    with st.sidebar:
        st.markdown("### 🛠️ PROFILE")
        st.session_state["name"] = st.text_input("Warrior Name", value=st.session_state["name"])
        # ТВОИ 3 БРОСКА
        st.session_state["move"] = st.selectbox("Select Drill", ["Zhambas", "Shalu", "Koterme"])
        st.write("---")
        if st.button("RESET SESSION"):
            st.session_state.xp = 0
            st.session_state.reps = 0
            st.rerun()

    st.markdown("<h1 class='hero-title'>🦅 SHEBER AI PRO</h1>", unsafe_allow_html=True)
    
    # Статистика
    xp = st.session_state["xp"]
    rank = "BALA" if xp < 100 else ("ZHASOSPIRIM" if xp < 500 else "BATYR")
    goal = 100 if xp < 100 else (500 if xp < 500 else 1500)
    prog = min((xp / goal) * 100, 100)

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='metric-card'><small>RANK</small><div class='metric-val'>🥋 {rank}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"""<div class='metric-card'><small>EXPERIENCE</small><div class='metric-val'>{xp} XP</div>
                <div class='xp-outer'><div class='xp-inner' style='width:{prog}%'></div></div></div>""", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><small>REPS</small><div class='metric-val' style='color:#4db8ff;'>{st.session_state['reps']}</div></div>", unsafe_allow_html=True)

    st.write(" ")
    col_vid, col_guide = st.columns([1.8, 1])

    with col_vid:
        st.markdown(f"### 🛰️ LIVE: {st.session_state['move']}")
        st.markdown('<div class="video-box">', unsafe_allow_html=True)
        webrtc_streamer(
            key="sheber-final-v2", # Изменил ключ, чтобы избежать конфликтов в кэше
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIG,
            video_processor_factory=SheberAI,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_guide:
        st.markdown("### 📘 GUIDE")
        move = st.session_state["move"]
        img_map = {"Zhambas": "jambass.jpg", "Shalu": "shalu.jpg", "Koterme": "koterme.webp"}
        st.image(img_map.get(move, "hero.jpg"), use_container_width=True)
        
        tips = {
            "Zhambas": "Держи спину ровно при подседе. Взрыв должен идти от бедер.",
            "Shalu": "Используй инерцию противника. Зацеп должен быть молниеносным.",
            "Koterme": "Это силовой прием. Контролируй захват пояса до конца."
        }
        st.success(f"**Совет:** {tips.get(move)}")

    st.write("---")
    st.image("hero.jpg", use_container_width=True)

if __name__ == "__main__":
    main()

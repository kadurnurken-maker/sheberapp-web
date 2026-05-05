import av
import cv2
import numpy as np
import streamlit as st
import mediapipe as mp
import urllib.request
import os
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration, WebRtcMode

# 1. КОНФИГУРАЦИЯ
st.set_page_config(
    page_title="SHEBER AI PRO",
    page_icon="🦅",
    layout="wide"
)

# 2. FIX FOR PERMISSION ERROR (DOWNLOAD TO TMP)
@st.cache_resource
def get_mp_pose():
    # На Streamlit Cloud запись разрешена только в /tmp
    model_path = "/tmp/pose_landmark_lite.tflite"
    model_url = "https://storage.googleapis.com/mediapipe-assets/pose_landmark_lite.tflite"
    
    if not os.path.exists(model_path):
        with st.spinner("Initializing AI Engine... (Downloading model)"):
            urllib.request.urlretrieve(model_url, model_path)
    
    return mp.solutions.pose.Pose(
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

pose_model = get_mp_pose()
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# 3. PREMIUM DARK DESIGN (CSS)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Inter:wght@400;600&display=swap');
    .stApp { background: #05070a; color: white; font-family: 'Inter', sans-serif; }
    .hero-title {
        font-family: 'Orbitron', sans-serif;
        background: linear-gradient(90deg, #f5c842, #ffae00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 900;
        text-align: center;
        filter: drop-shadow(0 0 10px rgba(245, 200, 66, 0.4));
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(245, 200, 66, 0.3);
        border-radius: 15px;
        padding: 15px;
        text-align: center;
        backdrop-filter: blur(10px);
    }
    .metric-val { font-family: 'Orbitron', sans-serif; font-size: 1.5rem; color: #f5c842; }
    .video-box { border: 2px solid #f5c842; border-radius: 20px; overflow: hidden; }
    [data-testid="stSidebar"] { background-color: #0a0f18; }
</style>
""", unsafe_allow_html=True)

# 4. ИНИЦИАЛИЗАЦИЯ
if "xp" not in st.session_state:
    st.session_state.update({"xp": 0, "reps": 0, "name": "Batyr", "move": "Zhambas"})

RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

# 5. AI ENGINE
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
            mp_drawing.draw_landmarks(img, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
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
                    self.hint = "NICE!"
            except: pass

        # HUD
        cv2.putText(img, f"LVL: {st.session_state['reps']//10} | {self.hint}", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (245, 200, 66), 2)
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# 6. UI
def main():
    with st.sidebar:
        st.markdown("### 🛠️ SETTINGS")
        st.session_state["name"] = st.text_input("Warrior Name", value=st.session_state["name"])
        st.session_state["move"] = st.selectbox("Select Drill", ["Zhambas", "Shalu", "Koterme", "Belbeu"])
        if st.button("RESET"):
            st.session_state.xp = 0
            st.session_state.reps = 0
            st.rerun()

    st.markdown("<h1 class='hero-title'>🦅 SHEBER AI PRO</h1>", unsafe_allow_html=True)
    
    # Stats
    xp = st.session_state["xp"]
    rank = "BALA" if xp < 100 else ("BATYR" if xp < 500 else "SHEBER")
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='metric-card'><small>RANK</small><div class='metric-val'>🥋 {rank}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><small>XP</small><div class='metric-val'>{xp}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><small>REPS</small><div class='metric-val'>{st.session_state['reps']}</div></div>", unsafe_allow_html=True)

    st.write("---")
    
    col_v, col_g = st.columns([2, 1])
    with col_v:
        st.markdown('<div class="video-box">', unsafe_allow_html=True)
        webrtc_streamer(
            key="sheber-stream",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIG,
            video_processor_factory=SheberAI,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_g:
        st.markdown("### 📘 GUIDE")
        # Тут используем твои картинки (убедись, что они в репозитории)
        img_map = {"Zhambas": "jambass.jpg", "Shalu": "shalu.jpg", "Koterme": "koterme.webp", "Belbeu": "hero.jpg"}
        st.image(img_map.get(st.session_state["move"], "hero.jpg"), use_container_width=True)
        st.info(f"Тренировка: {st.session_state['move']}. Следите за углом в коленях!")

if __name__ == "__main__":
    main()

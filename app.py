import av
import cv2
import numpy as np
import mediapipe as mp
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration

# ── CONFIG ──
st.set_page_config(page_title="SheberApp Pro", page_icon="🦅", layout="wide")

# ── ULTRA DESIGN CSS ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700;900&display=swap');

html, body, [data-testid="stApp"] {
    background: #020408;
    color: #ffffff;
    font-family: 'Montserrat', sans-serif;
}

/* Плавное появление всех элементов */
.stApp {
    animation: fadeIn 1.2s cubic-bezier(0.22, 1, 0.36, 1);
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Стеклянные карточки с неоновым свечением */
.rank-card {
    background: rgba(255, 255, 255, 0.02);
    backdrop-filter: blur(15px);
    border-radius: 24px;
    padding: 25px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    text-align: center;
    transition: 0.4s ease;
}
.rank-card:hover {
    border-color: #f5c842;
    background: rgba(245, 200, 66, 0.05);
    transform: translateY(-5px);
}

.rank-name { font-size: 2.2rem; font-weight: 900; color: #f5c842; text-transform: uppercase; }
.xp-value { font-size: 1.8rem; font-weight: 700; color: #4db8ff; }

/* Кастомный прогресс-бар (120fps feel) */
.xp-bar-bg { background: rgba(255,255,255,0.05); border-radius: 50px; height: 12px; margin: 15px 0; overflow: hidden; }
.xp-bar-fg { 
    background: linear-gradient(90deg, #f5c842, #ffae00); 
    height: 100%; 
    border-radius: 50px;
    transition: width 1.5s cubic-bezier(0.65, 0, 0.35, 1);
}

/* Стиль для фото */
.coach-img {
    border-radius: 20px;
    width: 100%;
    margin-bottom: 20px;
    border: 1px solid rgba(255,255,255,0.1);
}
</style>
""", unsafe_allow_html=True)

# ── DATA ──
RANKS = [(0, 100, "Bala", "🥋"), (101, 400, "Zhasospirim", "⚔️"), (401, 1000, "Batyr", "🦅"), (1001, 9999, "Sheber", "👑")]
XP_PER_CORRECT = 15
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

# ── SESSION STATE ──
if "xp" not in st.session_state: st.session_state.update({"xp": 0, "user_name": "Batyr", "throw": "Zhambas", "reps": 0})

# ── AI LOGIC ──
class WrestlingCoach(VideoProcessorBase):
    def __init__(self):
        self.pose = mp.solutions.pose.Pose(min_detection_confidence=0.7)
        self._correct_frames = 0
        self._cooldown = 0

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        h, w = img.shape[:2]
        
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = self.pose.process(rgb)

        status = "READY"
        color = (150, 150, 150)

        if res.pose_landmarks:
            # Отрисовка скелета (Белый/Золотой)
            mp.solutions.drawing_utils.draw_landmarks(
                img, res.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(color=(245, 200, 66), thickness=1, circle_radius=2),
                connection_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(color=(255, 255, 255), thickness=1)
            )
            
            # (Здесь твоя логика углов calculate_angle...)
            # Для примера: имитация успеха
            is_correct = True # Вставь сюда реальные проверки углов
            
            if is_correct:
                self._correct_frames += 1
                if self._correct_frames > 25 and self._cooldown == 0:
                    st.session_state["xp"] += 15
                    st.session_state["reps"] += 1
                    self._cooldown = 50
                    self._correct_frames = 0
                status = "PERFECT FORM!"
                color = (0, 255, 120)
            
            if self._cooldown > 0: self._cooldown -= 1

        cv2.putText(img, status, (40, h-40), cv2.FONT_HERSHEY_DUPLEX, 1.2, color, 2)
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# ── UI LAYOUT ──
st.title("🦅 SHEBER APP PRO")
st.markdown("### National Wrestling AI Analyst")

# Top Section: Stats
xp = st.session_state["xp"]
rank_name, emoji = "Bala", "🥋"
for lo, hi, n, e in RANKS:
    if lo <= xp <= hi: rank_name, emoji = n, e

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"<div class='rank-card'><small>LEVEL</small><div class='rank-name'>{emoji} {rank_name}</div></div>", unsafe_allow_html=True)
with c2:
    prog = min((xp % 100) / 100, 1.0)
    st.markdown(f"<div class='rank-card'><small>PROGRESS</small><div class='xp-value'>{xp} XP</div><div class='xp-bar-bg'><div class='xp-bar-fg' style='width:{int(prog*100)}%'></div></div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='rank-card'><small>SUCCESSFUL REPS</small><div class='xp-value'>{st.session_state['reps']}</div></div>", unsafe_allow_html=True)

st.divider()

# Main Training Section
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.markdown("#### 📸 LIVE AI SCANNER")
    webrtc_streamer(key="pro-coach", video_processor_factory=WrestlingCoach, rtc_configuration=RTC_CONFIG)

with col_right:
    st.markdown(f"#### 📖 {st.session_state['throw']} Technique")
    
    # Смена фото в зависимости от приема
    t = st.session_state["throw"]
    if t == "Zhambas":
        st.image("zhambas.jpg", caption="Optimal Hip Position", use_container_width=True)
        st.info("💡 Keep your back at 160° and knees bent at 130° for max leverage.")
    elif t == "Shalu":
        st.image("shalu.jpg", caption="Leg Sweep Execution", use_container_width=True)
        st.info("💡 Fully extend your leg and ensure the ankle sweep is sharp.")
    else:
        st.image("koterme.jpg", caption="The Power Lift", use_container_width=True)
        st.info("💡 Use your legs! Deep squat (100°) and keep your chest up.")

    st.divider()
    st.session_state["throw"] = st.selectbox("Switch Technique", ["Zhambas", "Shalu", "Koterme"])
    if st.button("RESET TRAINING DATA", use_container_width=True):
        st.session_state.update({"xp": 0, "reps": 0})
        st.rerun()

# Hero Image at the bottom for vibe
st.divider()
st.image("hero.jpg", use_container_width=True)

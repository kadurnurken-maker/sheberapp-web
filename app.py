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

/* Стеклянные карточки */
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

/* Кастомный прогресс-бар */
.xp-bar-bg { background: rgba(255,255,255,0.05); border-radius: 50px; height: 12px; margin: 15px 0; overflow: hidden; }
.xp-bar-fg { 
    background: linear-gradient(90deg, #f5c842, #ffae00); 
    height: 100%; 
    border-radius: 50px;
    transition: width 1.5s cubic-bezier(0.65, 0, 0.35, 1);
}
</style>
""", unsafe_allow_html=True)

# ── DATA & CONSTANTS ──
RANKS = [(0, 100, "Bala", "🥋"), (101, 400, "Zhasospirim", "⚔️"), (401, 1000, "Batyr", "🦅"), (1001, 9999, "Sheber", "👑")]
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

# ── SESSION STATE ──
if "xp" not in st.session_state: 
    st.session_state.update({"xp": 0, "user_name": "Batyr", "throw": "Zhambas", "reps": 0})

# ── HELPER FUNCTION (MATH) ──
def calculate_angle(a, b, c):
    """Calculates the angle between three points (for IB IA complexity points)"""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    ba = a - b
    bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return np.degrees(angle)

# ── AI LOGIC ──
class WrestlingCoach(VideoProcessorBase):
    def __init__(self):
        self.pose = mp.solutions.pose.Pose(min_detection_confidence=0.6, min_tracking_confidence=0.6)
        self._correct_frames = 0
        self._cooldown = 0

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        h, w = img.shape[:2]
        
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = self.pose.process(rgb)

        status = "STAND BACK (NO POSE DETECTED)"
        color = (0, 0, 255) # Red

        if res.pose_landmarks:
            # Draw Skeleton
            mp.solutions.drawing_utils.draw_landmarks(
                img, res.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(color=(245, 200, 66), thickness=2, circle_radius=3),
                connection_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(color=(255, 255, 255), thickness=2)
            )
            
            # Extract landmarks for math
            lms = res.pose_landmarks.landmark
            shoulder = [lms[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value].x, lms[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value].y]
            hip = [lms[mp.solutions.pose.PoseLandmark.LEFT_HIP.value].x, lms[mp.solutions.pose.PoseLandmark.LEFT_HIP.value].y]
            knee = [lms[mp.solutions.pose.PoseLandmark.LEFT_KNEE.value].x, lms[mp.solutions.pose.PoseLandmark.LEFT_KNEE.value].y]
            ankle = [lms[mp.solutions.pose.PoseLandmark.LEFT_ANKLE.value].x, lms[mp.solutions.pose.PoseLandmark.LEFT_ANKLE.value].y]

            # Biomechanics Check (Zhambas Example: back straight > 160, knees bent < 130)
            back_angle = calculate_angle(shoulder, hip, knee)
            knee_angle = calculate_angle(hip, knee, ankle)
            
            is_correct = (back_angle > 150) and (knee_angle < 140)
            
            if is_correct:
                self._correct_frames += 1
                status = "HOLD..."
                color = (0, 200, 255) # Yellow
                
                if self._correct_frames > 20 and self._cooldown == 0:
                    # IA specific: Add to global state
                    st.session_state["xp"] += 15
                    st.session_state["reps"] += 1
                    self._cooldown = 40
                    self._correct_frames = 0
            else:
                self._correct_frames = 0
                status = "CORRECT YOUR POSTURE"
                color = (0, 100, 255) # Orange
                
            if self._cooldown > 0:
                self._cooldown -= 1
                status = "PERFECT FORM! +15 XP"
                color = (0, 255, 100) # Green

        # Add text background for readability
        cv2.rectangle(img, (10, h - 60), (600, h - 10), (0,0,0), -1)
        cv2.putText(img, status, (20, h-25), cv2.FONT_HERSHEY_DUPLEX, 1.0, color, 2)
        
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
    prog = min((xp % 400) / 400, 1.0) # Scaled for visual progress
    st.markdown(f"<div class='rank-card'><small>PROGRESS</small><div class='xp-value'>{xp} XP</div><div class='xp-bar-bg'><div class='xp-bar-fg' style='width:{int(prog*100)}%'></div></div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='rank-card'><small>SUCCESSFUL REPS</small><div class='xp-value'>{st.session_state['reps']}</div></div>", unsafe_allow_html=True)

st.divider()

# Main Training Section
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.markdown("#### 📸 LIVE AI SCANNER")
    webrtc_streamer(
        key="pro-coach", 
        video_processor_factory=WrestlingCoach, 
        rtc_configuration=RTC_CONFIG,
        media_stream_constraints={"video": True, "audio": False}
    )

with col_right:
    st.markdown("#### 📖 Select Technique")
    st.session_state["throw"] = st.selectbox("", ["Zhambas", "Shalu", "Koterme"], label_visibility="collapsed")
    
    # ИСПРАВЛЕННЫЕ ИМЕНА ФАЙЛОВ ИЗ ТВОЕГО GITHUB:
    t = st.session_state["throw"]
    if t == "Zhambas":
        st.image("jambass.jpg", caption="Zhambas - Optimal Hip Position", use_container_width=True)
        st.info("💡 Keep your back at >150° and knees bent at <140° for max leverage.")
    elif t == "Shalu":
        st.image("shalu.jpg", caption="Shalu - Leg Sweep Execution", use_container_width=True)
        st.info("💡 Fully extend your leg and ensure the ankle sweep is sharp.")
    else:
        st.image("koterme.webp", caption="Koterme - The Power Lift", use_container_width=True)
        st.info("💡 Use your legs! Deep squat and keep your chest up.")

    st.divider()
    if st.button("RESET TRAINING DATA", use_container_width=True):
        st.session_state.update({"xp": 0, "reps": 0})
        st.rerun()

st.divider()
st.image("hero.jpg", use_container_width=True)

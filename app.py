import av
import cv2
import numpy as np
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

.stApp {
    animation: fadeIn 1.2s cubic-bezier(0.22, 1, 0.36, 1);
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

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
        # FIX: Local import to prevent AttributeError in Streamlit Cloud
        import mediapipe as mp
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5, 
            min_tracking_confidence=0.5,
            model_complexity=1
        )
        self._correct_frames = 0
        self._cooldown = 0

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        h, w = img.shape[:2]
        
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = self.pose.process(rgb)

        status = "POSITIONING..."
        color = (150, 150, 150) 

        if res.pose_landmarks:
            # Draw Skeleton
            self.mp_drawing.draw_landmarks(
                img, res.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing.DrawingSpec(color=(245, 200, 66), thickness=2, circle_radius=3),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2)
            )
            
            lms = res.pose_landmarks.landmark
            # Get key points
            try:
                shoulder = [lms[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, lms[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                hip = [lms[self.mp_pose.PoseLandmark.LEFT_HIP.value].x, lms[self.mp_pose.PoseLandmark.LEFT_HIP.value].y]
                knee = [lms[self.mp_pose.PoseLandmark.LEFT_KNEE.value].x, lms[self.mp_pose.PoseLandmark.LEFT_KNEE.value].y]
                ankle = [lms[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].x, lms[self.mp_pose.PoseLandmark.LEFT_ANKLE.value].y]

                back_angle = calculate_angle(shoulder, hip, knee)
                knee_angle = calculate_angle(hip, knee, ankle)
                
                # Check posture
                if back_angle > 150 and knee_angle < 145:
                    self._correct_frames += 1
                    status = "GOOD! HOLD..."
                    color = (0, 200, 255)
                    
                    if self._correct_frames > 25 and self._cooldown == 0:
                        st.session_state["xp"] += 15
                        st.session_state["reps"] += 1
                        self._cooldown = 30
                        self._correct_frames = 0
                else:
                    self._correct_frames = 0
                    status = "FIX FORM"
                    color = (0, 100, 255)
            except:
                pass
                
            if self._cooldown > 0:
                self._cooldown -= 1
                status = "POINT EARNED!"
                color = (0, 255, 100)

        cv2.rectangle(img, (0, h - 80), (450, h), (0,0,0), -1)
        cv2.putText(img, status, (20, h-30), cv2.FONT_HERSHEY_DUPLEX, 1.2, color, 2)
        
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# ── UI LAYOUT ──
st.title("🦅 SHEBER APP PRO")
st.markdown("### National Wrestling AI Analyst")

xp = st.session_state["xp"]
rank_name, emoji = "Bala", "🥋"
for lo, hi, n, e in RANKS:
    if lo <= xp <= hi: rank_name, emoji = n, e

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"<div class='rank-card'><small>RANK</small><div class='rank-name'>{emoji} {rank_name}</div></div>", unsafe_allow_html=True)
with c2:
    prog = min((xp % 400) / 400, 1.0)
    st.markdown(f"<div class='rank-card'><small>TOTAL XP</small><div class='xp-value'>{xp}</div><div class='xp-bar-bg'><div class='xp-bar-fg' style='width:{int(prog*100)}%'></div></div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='rank-card'><small>REPS</small><div class='xp-value'>{st.session_state['reps']}</div></div>", unsafe_allow_html=True)

st.divider()

col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.markdown("#### 📸 LIVE AI SCANNER")
    webrtc_streamer(
        key="wrestling-scanner", 
        video_processor_factory=WrestlingCoach, 
        rtc_configuration=RTC_CONFIG,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True
    )

with col_right:
    st.markdown("#### 📖 Technique Guide")
    tech = st.selectbox("Choose Technique", ["Zhambas", "Shalu", "Koterme"])
    st.session_state["throw"] = tech
    
    if tech == "Zhambas":
        st.image("jambass.jpg", caption="Zhambas Guide", use_container_width=True)
        st.warning("Keep hips low and back straight.")
    elif tech == "Shalu":
        st.image("shalu.jpg", caption="Shalu Guide", use_container_width=True)
        st.warning("Focus on the ankle sweep timing.")
    else:
        st.image("koterme.webp", caption="Koterme Guide", use_container_width=True)
        st.warning("Use explosive leg power to lift.")

    if st.button("RESET SESSION"):
        st.session_state.update({"xp": 0, "reps": 0})
        st.rerun()

st.divider()
st.image("hero.jpg", use_container_width=True)

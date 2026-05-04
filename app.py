import av
import cv2
import numpy as np
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration

# 1. СТРОГАЯ КОНФИГУРАЦИЯ
st.set_page_config(page_title="SheberApp Pro", page_icon="🦅", layout="wide")

# 2. УЛУЧШЕННЫЙ ULTRA DESIGN (CSS)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Montserrat:wght@300;700&display=swap');

    /* Основной фон */
    .stApp {
        background: radial-gradient(circle at top right, #0a0f1a, #020408);
        color: #e0e0e0;
        font-family: 'Montserrat', sans-serif;
    }

    /* Заголовки в стиле Киберпанк */
    h1, h2, h3 {
        font-family: 'Orbitron', sans-serif;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #f5c842 !important;
        text-shadow: 0 0 15px rgba(245, 200, 66, 0.3);
    }

    /* Контейнеры статистики */
    .metric-container {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(245, 200, 66, 0.2);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        backdrop-filter: blur(10px);
        transition: 0.3s;
    }
    .metric-container:hover {
        border-color: #f5c842;
        box-shadow: 0 0 20px rgba(245, 200, 66, 0.1);
    }

    .metric-label { font-size: 0.8rem; color: #888; text-transform: uppercase; }
    .metric-value { font-size: 2rem; font-weight: 700; color: #ffffff; }

    /* Видео и Картинки */
    .stImage, .element-container iframe {
        border-radius: 15px;
        border: 2px solid rgba(255,255,255,0.1);
    }

    /* Кнопки */
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #f5c842, #ffae00);
        color: black !important;
        font-weight: 700;
        border: none;
        border-radius: 10px;
        padding: 10px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 15px #f5c842;
    }
</style>
""", unsafe_allow_html=True)

# ── DATA ──
RANKS = [(0, 100, "Bala", "🥋"), (101, 400, "Zhasospirim", "⚔️"), (401, 1000, "Batyr", "🦅"), (1001, 9999, "Sheber", "👑")]
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

# ── STATE ──
if "xp" not in st.session_state:
    st.session_state.update({"xp": 0, "reps": 0, "throw": "Zhambas"})

# ── MATH ──
def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return np.degrees(np.arccos(np.clip(cosine_angle, -1.0, 1.0)))

# ── AI ENGINE ──
class WrestlingCoach(VideoProcessorBase):
    def __init__(self):
        # Импорт ВНУТРИ класса решает проблему AttributeError на сервере
        import mediapipe as mp
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self._correct_frames = 0
        self._cooldown = 0

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        h, w = img.shape[:2]
        
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = self.pose.process(rgb)

        status = "WAINTING FOR SKELETON..."
        color = (100, 100, 100)

        if res.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                img, res.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing.DrawingSpec(color=(245, 200, 66), thickness=2, circle_radius=2)
            )
            
            try:
                lms = res.pose_landmarks.landmark
                # Точки для анализа (Биомеханика)
                shoulder = [lms[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, lms[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                hip = [lms[self.mp_pose.PoseLandmark.LEFT_HIP.value].x, lms[self.mp_pose.PoseLandmark.LEFT_HIP.value].y]
                knee = [lms[self.mp_pose.PoseLandmark.LEFT_KNEE.value].x, lms[self.mp_pose.PoseLandmark.LEFT_KNEE.value].y]
                
                angle = calculate_angle(shoulder, hip, knee)

                if angle > 150: # Пример логики для броска
                    self._correct_frames += 1
                    status = "READY TO THROW!"
                    color = (0, 255, 255)
                    if self._correct_frames > 20 and self._cooldown == 0:
                        st.session_state["xp"] += 10
                        st.session_state["reps"] += 1
                        self._cooldown = 30
                else:
                    status = "FIX YOUR BACK"
                    color = (0, 0, 255)
            except: pass

        if self._cooldown > 0:
            self._cooldown -= 1
            status = "NICE! +10 XP"
            color = (0, 255, 0)

        cv2.putText(img, status, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# ── ВЕРСТКА ИНТЕРФЕЙСА ──
st.title("🦅 SHEBER APP PRO")
st.write("---")

# Секция статистики
xp = st.session_state["xp"]
rank_name = "Bala"
for lo, hi, n, e in RANKS:
    if lo <= xp <= hi: rank_name = f"{e} {n}"

col_rank, col_xp, col_reps = st.columns(3)
with col_rank:
    st.markdown(f"<div class='metric-container'><div class='metric-label'>Rank</div><div class='metric-value'>{rank_name}</div></div>", unsafe_allow_html=True)
with col_xp:
    st.markdown(f"<div class='metric-container'><div class='metric-label'>Total XP</div><div class='metric-value'>{xp}</div></div>", unsafe_allow_html=True)
with col_reps:
    st.markdown(f"<div class='metric-container'><div class='metric-label'>Reps</div><div class='metric-value'>{st.session_state['reps']}</div></div>", unsafe_allow_html=True)

st.write("")

# Основной блок (Камера + Инструкция)
main_left, main_right = st.columns([1.5, 1])

with main_left:
    st.subheader("📸 AI Scanner")
    webrtc_streamer(
        key="wrestling-coach",
        video_processor_factory=WrestlingCoach,
        rtc_configuration=RTC_CONFIG,
        media_stream_constraints={"video": True, "audio": False}
    )

with main_right:
    st.subheader("📖 Technique")
    tech = st.selectbox("Select Drill", ["Zhambas", "Shalu", "Koterme"])
    
    # Имена файлов должны совпадать с GitHub
    images = {"Zhambas": "jambass.jpg", "Shalu": "shalu.jpg", "Koterme": "koterme.webp"}
    st.image(images[tech], use_container_width=True)
    
    st.info(f"Focus on your center of gravity while performing {tech}.")
    
    if st.button("RESET SESSION"):
        st.session_state.xp = 0
        st.session_state.reps = 0
        st.rerun()

st.write("---")
st.image("hero.jpg", use_container_width=True)

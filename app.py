"""
SheberApp — Qazaq Kuresi AI Wrestling Coach
IB Computer Science IA Project
Author: [Your Name]
Description: Real-time biomechanics coaching for Qazaq Kuresi throws
             using MediaPipe Pose, OpenCV, and Streamlit-WebRTC.
"""

import av
import cv2
import numpy as np
import mediapipe as mp
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration

# ──────────────────────────────────────────────
#  PAGE CONFIG — must be FIRST Streamlit call
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="SheberApp | Qazaq Kuresi AI Coach",
    page_icon="🤼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
#  GLOBAL STYLES  (dark-mode, Kazakh palette)
# ──────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base dark theme ── */
html, body, [data-testid="stApp"] {
    background-color: #0d0f14;
    color: #e8e8e8;
    font-family: 'Trebuchet MS', sans-serif;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111827 0%, #1a2236 100%);
    border-right: 1px solid #2a3550;
}
[data-testid="stSidebar"] * { color: #c8d6f0 !important; }

/* ── Section headers ── */
h1 { color: #f5c842 !important; letter-spacing: 2px; }
h2 { color: #4db8ff !important; }
h3 { color: #aad4ff !important; }

/* ── XP / Rank cards ── */
.rank-card {
    background: linear-gradient(135deg, #1a2236, #0d1622);
    border: 1px solid #2a3550;
    border-radius: 12px;
    padding: 18px 24px;
    text-align: center;
    margin-bottom: 8px;
}
.rank-name  { font-size: 2rem; font-weight: 700; color: #f5c842; }
.rank-label { font-size: 0.85rem; color: #6b8cba; letter-spacing: 1px; }
.xp-value   { font-size: 1.6rem; font-weight: 600; color: #4db8ff; }

/* ── XP progress bar ── */
.xp-bar-bg  { background:#1e2a40; border-radius:999px; height:12px; }
.xp-bar-fg  {
    background: linear-gradient(90deg, #f5c842, #f09030);
    height: 12px; border-radius: 999px;
    transition: width 0.4s ease;
}

/* ── Instruction box ── */
.tip-box {
    background: #111c2e;
    border-left: 4px solid #f5c842;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin: 8px 0;
    font-size: 0.9rem;
    color: #b0c4de;
}

/* ── Throw selector ── */
[data-testid="stSelectbox"] select {
    background: #1a2236 !important;
    color: #e8e8e8 !important;
    border: 1px solid #2a3550 !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #f5c842, #e09020);
    color: #0d0f14;
    font-weight: 700;
    border: none;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
#  CONSTANTS
# ──────────────────────────────────────────────

# Rank thresholds
RANKS = [
    (0,   100,  "Bala",       "🥋"),
    (101, 400,  "Zhasospirim","⚔️"),
    (401, 1000, "Batyr",      "🦅"),
    (1001, 9999,"Sheber",     "👑"),
]

XP_PER_CORRECT = 15           # XP awarded for a correct rep
VISIBILITY_THRESHOLD = 0.3    # Min MediaPipe confidence to trust landmark

# WebRTC STUN servers (needed for cloud deployment)
RTC_CONFIG = RTCConfiguration({
    "iceServers": [
        {"urls": ["stun:stun.l.google.com:19302"]},
        {"urls": ["stun:stun1.l.google.com:19302"]},
    ]
})

# ──────────────────────────────────────────────
#  SESSION STATE INIT
# ──────────────────────────────────────────────
def init_state():
    defaults = {
        "xp":           0,
        "user_name":    "Batyr",
        "throw":        "Zhambas",
        "feedback":     "",
        "correct_reps": 0,
        "total_reps":   0,
        "last_correct": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ──────────────────────────────────────────────
#  HELPER FUNCTIONS
# ──────────────────────────────────────────────

def get_rank(xp: int) -> tuple:
    """Return (rank_name, emoji) based on XP."""
    for lo, hi, name, emoji in RANKS:
        if lo <= xp <= hi:
            return name, emoji
    return "Sheber", "👑"

def xp_progress(xp: int) -> tuple:
    """Return (progress 0-1, next_threshold) for current rank band."""
    for lo, hi, *_ in RANKS:
        if lo <= xp <= hi:
            band = hi - lo
            return (xp - lo) / band if band else 1.0, hi
    return 1.0, xp

def calculate_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """
    Calculate the angle at joint B formed by vectors BA and BC.
    a, b, c — each shape (2,) or (3,) arrays [x, y, (z)]
    Returns angle in degrees [0, 180].
    """
    ba = a[:2] - b[:2]
    bc = c[:2] - b[:2]
    cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))

def draw_text_with_bg(
    frame: np.ndarray,
    text: str,
    pos: tuple,
    font_scale: float = 1.0,
    color: tuple = (255, 255, 255),
    thickness: int = 2,
    bg_color: tuple = (0, 0, 0),
    alpha: float = 0.6,
) -> np.ndarray:
    """
    Draw text with a semi-transparent background rectangle.
    Much more readable on live video than plain cv2.putText.
    """
    font = cv2.FONT_HERSHEY_DUPLEX
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = pos
    pad = 8

    # Draw background overlay
    overlay = frame.copy()
    cv2.rectangle(overlay,
                  (x - pad, y - th - pad),
                  (x + tw + pad, y + baseline + pad),
                  bg_color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    # Draw text
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)
    return frame

# ──────────────────────────────────────────────
#  VIDEO PROCESSOR CLASS
# ──────────────────────────────────────────────

class WrestlingCoach(VideoProcessorBase):
    """
    Processes each video frame:
    1. Runs MediaPipe Pose detection
    2. Analyses biomechanics for selected throw
    3. Overlays coaching feedback on the frame
    4. Writes XP award signal to shared state
    """

    def __init__(self):
        # MediaPipe Pose — runs inside the WebRTC worker thread
        import mediapipe as mp                 # 🔥 ДОБАВЬ ЭТУ СТРОЧКУ СЮДА
        
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,          # 0=fast, 1=balanced, 2=accurate
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_style = mp.solutions.drawing_styles

    # ── landmark helper ──────────────────────────
    def _lm(self, landmarks, idx: int) -> tuple:
        """Return (x, y, z, visibility) for a landmark index."""
        lm = landmarks[idx]
        return lm.x, lm.y, lm.z, lm.visibility

    def _coords(self, landmarks, idx: int) -> np.ndarray:
        """Return [x, y] normalised coords as ndarray."""
        lm = landmarks[idx]
        return np.array([lm.x, lm.y])

    def _vis(self, landmarks, *indices) -> bool:
        """True if ALL given landmarks meet visibility threshold."""
        return all(landmarks[i].visibility >= VISIBILITY_THRESHOLD for i in indices)

    # ── per-throw biomechanics ───────────────────
    def _analyse_zhambas(self, lms, h: int, w: int) -> dict:
        """
        Zhambas (Hip Throw) checks:
        - Shoulder-Hip-Knee angle > 160° → straight back
        - Hip-Knee-Ankle angle  < 130° → bent knees (power position)
        Returns dict with feedback key and is_correct bool.
        """
        MP = self.mp_pose.PoseLandmark
        required = [MP.LEFT_SHOULDER, MP.LEFT_HIP, MP.LEFT_KNEE, MP.LEFT_ANKLE,
                    MP.RIGHT_SHOULDER, MP.RIGHT_HIP, MP.RIGHT_KNEE, MP.RIGHT_ANKLE]

        if not self._vis(lms, *[r.value for r in required]):
            return {"text": "STEP BACK! NEED LEGS", "color": (255, 180, 0), "correct": False, "no_legs": True}

        # Use left side (can be averaged if desired)
        shoulder = self._coords(lms, MP.LEFT_SHOULDER.value)
        hip      = self._coords(lms, MP.LEFT_HIP.value)
        knee     = self._coords(lms, MP.LEFT_KNEE.value)
        ankle    = self._coords(lms, MP.LEFT_ANKLE.value)

        back_angle  = calculate_angle(shoulder, hip, knee)    # should be > 160
        knee_angle  = calculate_angle(hip, knee, ankle)       # should be < 130

        back_ok  = back_angle  > 160
        knees_ok = knee_angle  < 130

        if back_ok and knees_ok:
            return {"text": "ZHAKSY! PERFECT ZHAMBAS!", "color": (0, 220, 80), "correct": True}
        elif not back_ok:
            return {"text": "ARQANDY TIK USTA! (BACK STRAIGHT)", "color": (0, 80, 255), "correct": False}
        else:
            return {"text": "TIZELERINDI IY! (BEND KNEES)", "color": (0, 80, 255), "correct": False}

    def _analyse_shalu(self, lms, h: int, w: int) -> dict:
        """
        Shalu (Leg Sweep) checks:
        - Sweeping leg knee > 160° → extended/straight
        - Ankles crossing on X-axis (left_ankle.x > right_ankle.x for right-leg sweep)
        """
        MP = self.mp_pose.PoseLandmark
        required = [MP.LEFT_KNEE, MP.LEFT_ANKLE, MP.RIGHT_KNEE, MP.RIGHT_ANKLE,
                    MP.LEFT_HIP, MP.RIGHT_HIP]

        if not self._vis(lms, *[r.value for r in required]):
            return {"text": "STEP BACK! NEED LEGS", "color": (255, 180, 0), "correct": False, "no_legs": True}

        l_hip   = self._coords(lms, MP.LEFT_HIP.value)
        l_knee  = self._coords(lms, MP.LEFT_KNEE.value)
        l_ankle = self._coords(lms, MP.LEFT_ANKLE.value)
        r_ankle = self._coords(lms, MP.RIGHT_ANKLE.value)

        sweep_angle  = calculate_angle(l_hip, l_knee, l_ankle)  # sweeping leg
        leg_straight = sweep_angle > 160

        # Crossing check: in normalised coords, x goes left→right
        ankles_crossing = abs(l_ankle[0] - r_ankle[0]) < 0.10

        if leg_straight and ankles_crossing:
            return {"text": "ZHAKSY! SHALU!", "color": (0, 220, 80), "correct": True}
        elif not leg_straight:
            return {"text": "AIYAQTY TIK! (STRAIGHTEN LEG)", "color": (0, 80, 255), "correct": False}
        else:
            return {"text": "AYLAQ! CROSS YOUR ANKLES", "color": (0, 80, 255), "correct": False}

    def _analyse_koterme(self, lms, h: int, w: int) -> dict:
        """
        Koterme (Pick Up / Lift) checks:
        - Both knees < 100° → deep squat position
        - Back vertical: shoulder X ≈ hip X (small horizontal offset)
        """
        MP = self.mp_pose.PoseLandmark
        required = [MP.LEFT_HIP, MP.LEFT_KNEE, MP.LEFT_ANKLE,
                    MP.RIGHT_HIP, MP.RIGHT_KNEE, MP.RIGHT_ANKLE,
                    MP.LEFT_SHOULDER, MP.RIGHT_SHOULDER]

        if not self._vis(lms, *[r.value for r in required]):
            return {"text": "STEP BACK! NEED LEGS", "color": (255, 180, 0), "correct": False, "no_legs": True}

        l_hip    = self._coords(lms, MP.LEFT_HIP.value)
        l_knee   = self._coords(lms, MP.LEFT_KNEE.value)
        l_ankle  = self._coords(lms, MP.LEFT_ANKLE.value)
        r_hip    = self._coords(lms, MP.RIGHT_HIP.value)
        r_knee   = self._coords(lms, MP.RIGHT_KNEE.value)
        r_ankle  = self._coords(lms, MP.RIGHT_ANKLE.value)
        l_sh     = self._coords(lms, MP.LEFT_SHOULDER.value)
        r_sh     = self._coords(lms, MP.RIGHT_SHOULDER.value)

        l_knee_angle = calculate_angle(l_hip, l_knee, l_ankle)
        r_knee_angle = calculate_angle(r_hip, r_knee, r_ankle)
        deep_squat   = l_knee_angle < 100 and r_knee_angle < 100

        # Back vertical: mid-shoulder x vs mid-hip x
        mid_sh  = (l_sh[0]  + r_sh[0])  / 2
        mid_hip = (l_hip[0] + r_hip[0]) / 2
        back_vertical = abs(mid_sh - mid_hip) < 0.07

        if deep_squat and back_vertical:
            return {"text": "ZHAKSY! KOTERME READY!", "color": (0, 220, 80), "correct": True}
        elif not deep_squat:
            return {"text": "TERENIREK OTY! (DEEPER SQUAT)", "color": (0, 80, 255), "correct": False}
        else:
            return {"text": "ARQANDY TIK USTA! (BACK VERTICAL)", "color": (0, 80, 255), "correct": False}

    # ── main frame callback ──────────────────────
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        """Called for every incoming video frame from the browser."""
        img = frame.to_ndarray(format="bgr24")
        h, w = img.shape[:2]

        # Mirror for natural feel
        img = cv2.flip(img, 1)

        # Convert BGR→RGB for MediaPipe
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        result = self.pose.process(rgb)

        # ── Draw skeleton ──────────────────────────
        if result.pose_landmarks:
            self.mp_draw.draw_landmarks(
                img,
                result.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_draw.DrawingSpec(
                    color=(245, 200, 66), thickness=2, circle_radius=3),
                connection_drawing_spec=self.mp_draw.DrawingSpec(
                    color=(100, 180, 255), thickness=2),
            )

            lms = result.pose_landmarks.landmark
            throw = st.session_state.get("throw", "Zhambas")

            # ── Dispatch to analyser ───────────────
            if throw == "Zhambas":
                feedback = self._analyse_zhambas(lms, h, w)
            elif throw == "Shalu":
                feedback = self._analyse_shalu(lms, h, w)
            else:  # Koterme
                feedback = self._analyse_koterme(lms, h, w)

            # ── XP cooldown logic ──────────────────
            # Award XP only after holding correct pose for ~20 frames
            # and then wait 60 frames before awarding again.
            if feedback["correct"]:
                self._correct_frames += 1
                if self._correct_frames >= 20 and self._cooldown == 0:
                    st.session_state["xp"]           += XP_PER_CORRECT
                    st.session_state["correct_reps"] += 1
                    st.session_state["last_correct"]  = True
                    self._correct_frames = 0
                    self._cooldown = 60
            else:
                self._correct_frames = 0
                st.session_state["last_correct"] = False

            if self._cooldown > 0:
                self._cooldown -= 1

            # ── Draw feedback text on frame ────────
            img = draw_text_with_bg(
                img,
                feedback["text"],
                pos=(20, h - 30),
                font_scale=0.9,
                color=feedback["color"],
                thickness=2,
                bg_color=(5, 5, 15),
                alpha=0.65,
            )

            # ── Draw throw label top-right ─────────
            img = draw_text_with_bg(
                img,
                f"Throw: {throw}",
                pos=(w - 220, 35),
                font_scale=0.7,
                color=(200, 200, 200),
                thickness=1,
                bg_color=(10, 10, 20),
                alpha=0.55,
            )

        else:
            # No pose detected
            img = draw_text_with_bg(
                img,
                "POSE NOT DETECTED — STAND BACK",
                pos=(20, h - 30),
                font_scale=0.8,
                color=(80, 80, 255),
                thickness=2,
                bg_color=(5, 5, 15),
                alpha=0.65,
            )

        return av.VideoFrame.from_ndarray(img, format="bgr24")


# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🤼 SheberApp")
    st.markdown("*Qazaq Kuresi AI Coach*")
    st.divider()

    name = st.text_input("👤 Your Name", value=st.session_state["user_name"])
    st.session_state["user_name"] = name

    throw = st.selectbox(
        "🥋 Select Throw",
        ["Zhambas", "Shalu", "Koterme"],
        index=["Zhambas", "Shalu", "Koterme"].index(st.session_state["throw"]),
    )
    st.session_state["throw"] = throw

    st.divider()

    # ── Throw tips ──
    tips = {
        "Zhambas": "Hip throw. Keep your **back straight** (>160°) and **bend knees** (<130°) to load power.",
        "Shalu":   "Leg sweep. **Extend your sweeping leg** fully (>160°) and **cross ankles** at the moment of sweep.",
        "Koterme": "Pick-up. **Deep squat** both knees (<100°) with your **back vertical** before lifting.",
    }
    st.markdown(f"""<div class='tip-box'>💡 <b>{throw}</b><br>{tips[throw]}</div>""",
                unsafe_allow_html=True)

    st.divider()
    if st.button("🔄 Reset XP"):
        st.session_state["xp"]           = 0
        st.session_state["correct_reps"] = 0
        st.session_state["total_reps"]   = 0
        st.session_state["last_correct"] = False
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("IB Computer Science IA · SheberApp v1.0")

# ══════════════════════════════════════════════
#  MAIN PAGE
# ══════════════════════════════════════════════
st.markdown(f"# 🦅 SheberApp — Qazaq Kuresi Coach")
st.markdown(f"**Salemetsizdebemi, {st.session_state['user_name']}!** Ready to train?")

# ── Stats row ──────────────────────────────────
rank_name, rank_emoji = get_rank(st.session_state["xp"])
progress, next_xp = xp_progress(st.session_state["xp"])
xp_pct = int(progress * 100)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class='rank-card'>
        <div class='rank-label'>CURRENT RANK</div>
        <div class='rank-name'>{rank_emoji} {rank_name}</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class='rank-card'>
        <div class='rank-label'>TOTAL XP</div>
        <div class='xp-value'>{st.session_state['xp']} XP</div>
        <br>
        <div class='xp-bar-bg'>
            <div class='xp-bar-fg' style='width:{xp_pct}%'></div>
        </div>
        <div style='font-size:0.75rem;color:#6b8cba;margin-top:4px'>
            {st.session_state['xp']} / {next_xp} XP to next rank
        </div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class='rank-card'>
        <div class='rank-label'>CORRECT REPS</div>
        <div class='xp-value'>{st.session_state['correct_reps']}</div>
        <div style='font-size:0.75rem;color:#6b8cba;margin-top:4px'>
            +{XP_PER_CORRECT} XP per correct hold
        </div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Rank ladder ────────────────────────────────
with st.expander("📊 Rank Ladder", expanded=False):
    for lo, hi, rname, remoji in RANKS:
        active = " ← YOU" if rname == rank_name else ""
        bar_w  = 100 if rname == rank_name else 30
        st.markdown(f"""
        <div style='display:flex;align-items:center;gap:12px;margin:6px 0'>
            <span style='width:28px'>{remoji}</span>
            <span style='width:130px;color:#c8d6f0'>{rname}{active}</span>
            <span style='color:#6b8cba;font-size:0.82rem'>{lo}–{hi} XP</span>
        </div>""", unsafe_allow_html=True)

st.divider()

# ── WebRTC Camera ──────────────────────────────
st.markdown("## 📸 Live Camera — Real-Time Analysis")
st.markdown(
    "Allow camera access when prompted. "
    "Stand **2–3 metres** from camera so your full body is visible."
)

webrtc_streamer(
    key="sheber-coach",
    video_processor_factory=WrestlingCoach,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video": True, "audio": False},
    async_processing=True,
)

# ── Colour legend ──────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
leg_col1, leg_col2, leg_col3 = st.columns(3)
with leg_col1:
    st.markdown("🟢 **Green** = ZHAKSY! (Correct form)")
with leg_col2:
    st.markdown("🔵 **Blue** = Form correction needed")
with leg_col3:
    st.markdown("🟡 **Yellow** = Move back / step away")

st.divider()
st.caption(
    "SheberApp uses MediaPipe Pose to track 33 body landmarks in real time. "
    "Biomechanical angles are computed per throw. +15 XP is awarded after "
    "holding correct form for ~20 consecutive frames. "
    "Built for IB Computer Science HL Internal Assessment."
)

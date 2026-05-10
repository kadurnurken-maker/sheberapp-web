import streamlit as st
import mediapipe as mp
import cv2
import numpy as np
import av
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration, WebRtcMode
import threading

# 1. КОНФИГУРАЦИЯ
st.set_page_config(page_title="SHEBER AI PRO", layout="wide")

# Инициализация очков в начале (чтобы не сбрасывались)
if "xp" not in st.session_state:
    st.session_state.xp = 0
if "reps" not in st.session_state:
    st.session_state.reps = 0

# Общий замок для передачи данных между ИИ и сайтом
lock = threading.Lock()
class SharedState:
    count = 0
    xp = 0

shared = SharedState()

# 2. AI ENGINE
class SheberAI(VideoProcessorBase):
    def __init__(self):
        self.pose = mp.solutions.pose.Pose(model_complexity=0) # 0 для скорости
        self.stage = None
        self.hint = "WAITING"
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
                # Точки для анализа
                hip = [lms[23].x, lms[23].y]
                knee = [lms[25].x, lms[25].y]
                ankle = [lms[27].x, lms[27].y]
                shoulder = [lms[11].x, lms[11].y]

                # 1. ЛОГИКА ДЛЯ ЖАМБАС (Глубокий подсед)
                if self.current_move == "Zhambas":
                    angle = self.calculate_angle(hip, knee, ankle)
                    if angle < 100: self.stage = "down"
                    if angle > 150 and self.stage == "down":
                        self.stage = "up"
                        with lock:
                            shared.count += 1
                            shared.xp += 15
                        self.hint = "ZHAMBAS DONE!"

                # 2. ЛОГИКА ДЛЯ SHALU (Подножка - наклон + вынос ноги)
                elif self.current_move == "Shalu":
                    # Считаем угол наклона корпуса к бедру
                    bend = self.calculate_angle(shoulder, hip, knee)
                    if bend < 120: self.stage = "down"
                    if bend > 160 and self.stage == "down":
                        self.stage = "up"
                        with lock:
                            shared.count += 1
                            shared.xp += 10
                        self.hint = "SHALU DONE!"

                # 3. ЛОГИКА ДЛЯ KOTERME (Бросок/Подъем - спина)
                elif self.current_move == "Koterme":
                    # Здесь важна высота плеч относительно бедер
                    if shoulder[1] > hip[1] - 0.1: self.stage = "down"
                    if shoulder[1] < hip[1] - 0.2 and self.stage == "down":
                        self.stage = "up"
                        with lock:
                            shared.count += 1
                            shared.xp += 20
                        self.hint = "KOTERME LIFT!"

            except: pass

        # Отрисовка текста на экране
        cv2.putText(img, f"STAGE: {self.stage}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# 3. ИНТЕРФЕЙС
def main():
    st.markdown("<h1 style='text-align: center; color: #f5c842;'>🦅 SHEBER AI PRO</h1>", unsafe_allow_html=True)

    # Сайдбар
    with st.sidebar:
        move = st.selectbox("Select Drill", ["Zhambas", "Shalu", "Koterme"])
        if st.button("Сбросить прогресс"):
            st.session_state.xp = 0
            st.session_state.reps = 0
            st.rerun()

    # Обновление очков из ИИ в Streamlit
    with lock:
        st.session_state.reps += shared.count
        st.session_state.xp += shared.xp
        shared.count = 0 # Сбрасываем временный буфер
        shared.xp = 0

    # Расчет рейтинга
    xp = st.session_state.xp
    if xp < 100: rank = "BALA (Новичок)"
    elif xp < 500: rank = "ZHASOSPIRIM (Юниор)"
    else: rank = "BATYR (Мастер)"

    # Метрики
    c1, c2, c3 = st.columns(3)
    c1.metric("RANK", rank)
    c2.metric("XP", f"{xp} pts")
    c3.metric("REPS", st.session_state.reps)

    # Запуск видео
    ctx = webrtc_streamer(
        key="sheber-v2",
        video_processor_factory=SheberAI,
        rtc_configuration=RTC_CONFIG, # используй свой старый RTC_CONFIG
        media_stream_constraints={"video": {"width": 480, "height": 360}, "audio": False},
        async_processing=True
    )

    if ctx.video_processor:
        ctx.video_processor.current_move = move

if __name__ == "__main__":
    main()

# ── НОВЫЙ PRO DESIGN (CSS) ──
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Montserrat:wght@300;500;700&display=swap');

    /* Фон и общие настройки */
    .stApp {
        background: #05070a;
        color: #e0e0e0;
        font-family: 'Montserrat', sans-serif;
    }

    /* Стеклянные карточки для статистики */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(245, 200, 66, 0.1);
        border-radius: 15px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    
    .rank-text { 
        font-family: 'Orbitron', sans-serif; 
        color: #f5c842; 
        font-size: 1.5rem; 
        font-weight: bold;
        text-shadow: 0 0 10px rgba(245, 200, 66, 0.2);
    }

    /* Кастомный прогресс-бар */
    .progress-container {
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
        height: 8px;
        margin-top: 10px;
    }
    .progress-fill {
        background: linear-gradient(90deg, #f5c842, #ffae00);
        height: 100%;
        border-radius: 10px;
        box-shadow: 0 0 10px #f5c842;
    }

    /* Рамка для сканера */
    .scanner-box {
        border: 2px solid #f5c842;
        border-radius: 20px;
        padding: 5px;
        background: #000;
    }

    /* Стиль кнопок */
    .stButton>button {
        border-radius: 8px !important;
        background: transparent !important;
        border: 1px solid #f5c842 !important;
        color: #f5c842 !important;
        transition: 0.3s !important;
    }
    .stButton>button:hover {
        background: #f5c842 !important;
        color: black !important;
    }
    
    /* Убираем лишние отступы Streamlit */
    .block-container { padding-top: 2rem !important; }
</style>
""", unsafe_allow_html=True)

# ── НОВАЯ ВЕРСТКА ИНТЕРФЕЙСА ──

# Верхняя панель: Лого и Статус
head_l, head_r = st.columns([2, 1])
with head_l:
    st.markdown(f"<h1>🦅 SHEBER APP <span style='color:white; font-size:1.2rem;'>PRO v2.0</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#888; margin-top:-15px;'>National Kazakh Kures AI Analysis System</p>", unsafe_allow_html=True)

# Панель статистики в ряд
xp = st.session_state["xp"]
rank_name = "Bala"
emoji = "🥋"
for lo, hi, n, e in RANKS:
    if lo <= xp <= hi: 
        rank_name, emoji = n, e

# Считаем прогресс до следующего уровня (для визуала)
next_goal = 100 if xp < 100 else (400 if xp < 400 else 1000)
prog_percent = min((xp / next_goal) * 100, 100)

s1, s2, s3 = st.columns(3)
with s1:
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:0.7rem; color:#888;">CURRENT RANK</div>
        <div class="rank-text">{emoji} {rank_name}</div>
    </div>
    """, unsafe_allow_html=True)
with s2:
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:0.7rem; color:#888;">EXPERIENCE POINTS</div>
        <div style="font-size:1.5rem; font-weight:bold;">{xp} XP</div>
        <div class="progress-container"><div class="progress-fill" style="width:{prog_percent}%"></div></div>
    </div>
    """, unsafe_allow_html=True)
with s3:
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:0.7rem; color:#888;">TOTAL SUCCESSFUL REPS</div>
        <div style="font-size:1.5rem; font-weight:bold; color:#4db8ff;">{st.session_state['reps']}</div>
    </div>
    """, unsafe_allow_html=True)

st.write(" ")

# Основная рабочая область
main_l, main_r = st.columns([1.6, 1])

with main_l:
    st.markdown("### 📸 AI NEURAL SCANNER")
    st.markdown('<div class="scanner-box">', unsafe_allow_html=True)
    webrtc_streamer(
        key="wrestling-coach",
        video_processor_factory=WrestlingCoach,
        rtc_configuration=RTC_CONFIG,
        media_stream_constraints={"video": True, "audio": False}
    )
    st.markdown('</div>', unsafe_allow_html=True)
    st.caption("Система автоматически фиксирует углы колен и спины в реальном времени.")

with main_r:
    st.markdown("### 📖 TRAINING GUIDE")
    tech = st.selectbox("Choose drill to analyze:", ["Zhambas", "Shalu", "Koterme"])
    
    # Контейнер для фото
    images = {"Zhambas": "jambass.jpg", "Shalu": "shalu.jpg", "Koterme": "koterme.webp"}
    st.image(images[tech], use_container_width=True)
    
    # Советы в зависимости от техники
    tips = {
        "Zhambas": "Держите спину прямой (>150°). Низкий подсед — ключ к броску.",
        "Shalu": "Скручивайте корпус одновременно с подсечкой.",
        "Koterme": "Используйте взрывную силу ног, сохраняя вертикаль корпуса."
    }
    st.warning(f"**Coach Tip:** {tips[tech]}")
    
    if st.button("🔄 RESET TRAINING DATA"):
        st.session_state.xp = 0
        st.session_state.reps = 0
        st.rerun()

st.write("---")
# Нижний баннер
st.image("hero.jpg", use_container_width=True)

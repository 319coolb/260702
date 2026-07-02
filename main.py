import streamlit as st
import random
 
# ========================================
# 기본 설정 (streamlit 기본 기능만 사용)
# ========================================
st.set_page_config(
    page_title="MBTI 포켓몬 직업 매칭 ✨",
    page_icon="🔮",
    layout="centered",
)
 
# ========================================
# 데이터: MBTI별 포켓몬 + 직업 매칭
# 포켓몬 이미지는 PokeAPI 공식 아트워크(정적 URL) 사용
# ========================================
MBTI_DATA = {
    "ISTJ": {
        "poke_id": 95, "poke_name": "롱스톤 (Onix)",
        "desc": "성실하고 단단한 원칙주의자",
        "color": "#8B7355",
        "jobs": [("📊", "회계사", "숫자와 규칙 속에서 빛나는 정확함"),
                 ("🏛️", "공무원", "체계와 신뢰를 지키는 전문가"),
                 ("🔧", "품질관리 엔지니어", "완벽을 향한 꼼꼼한 검증가")],
    },
    "ISFJ": {
        "poke_id": 113, "poke_name": "럭키 (Chansey)",
        "desc": "따뜻하고 헌신적인 수호자",
        "color": "#FFB6C1",
        "jobs": [("🩺", "간호사", "세심한 돌봄으로 사람을 살리는 손길"),
                 ("🤝", "사회복지사", "누군가의 든든한 버팀목"),
                 ("🍎", "초등교사", "아이들의 성장을 지켜보는 조력자")],
    },
    "INFJ": {
        "poke_id": 282, "poke_name": "가디안 (Gardevoir)",
        "desc": "신비롭고 통찰력 있는 이상주의자",
        "color": "#9370DB",
        "jobs": [("🧠", "상담심리사", "마음 깊은 곳을 읽어내는 통찰"),
                 ("✍️", "작가", "내면의 울림을 언어로 빚어내는 사람"),
                 ("🕊️", "인권운동가", "신념으로 세상을 바꾸는 목소리")],
    },
    "INTJ": {
        "poke_id": 65, "poke_name": "후딘 (Alakazam)",
        "desc": "치밀하고 전략적인 설계자",
        "color": "#4169E1",
        "jobs": [("📈", "데이터 과학자", "복잡한 데이터 속 패턴을 꿰뚫는 눈"),
                 ("♟️", "전략기획자", "몇 수 앞을 내다보는 마스터마인드"),
                 ("🏗️", "건축가", "머릿속 청사진을 현실로 세우는 설계자")],
    },
    "ISTP": {
        "poke_id": 123, "poke_name": "스라크 (Scyther)",
        "desc": "날렵하고 실용적인 장인",
        "color": "#3CB371",
        "jobs": [("🔩", "정비기술자", "손끝에서 문제를 해결하는 실력자"),
                 ("✈️", "파일럿", "냉철한 판단으로 하늘을 가르는 사람"),
                 ("🚑", "응급구조사", "위기의 순간 즉각 움직이는 프로")],
    },
    "ISFP": {
        "poke_id": 134, "poke_name": "샤미드 (Vaporeon)",
        "desc": "감성이 흐르는 자유로운 예술가",
        "color": "#00BFFF",
        "jobs": [("🎨", "일러스트레이터", "색채로 감정을 그려내는 손"),
                 ("🌸", "플로리스트", "자연의 아름다움을 다듬는 감각"),
                 ("📷", "사진작가", "찰나의 순간을 예술로 남기는 눈")],
    },
    "INFP": {
        "poke_id": 151, "poke_name": "뮤 (Mew)",
        "desc": "무한한 가능성을 품은 몽상가",
        "color": "#FF69B4",
        "jobs": [("📖", "소설가", "상상을 이야기로 엮어내는 창조자"),
                 ("💭", "카피라이터", "짧은 문장에 마음을 담는 재능"),
                 ("💗", "심리상담사", "깊은 공감으로 위로를 건네는 사람")],
    },
    "INTP": {
        "poke_id": 137, "poke_name": "폴리곤 (Porygon)",
        "desc": "논리로 세상을 분석하는 발명가",
        "color": "#20B2AA",
        "jobs": [("🔬", "연구원", "궁금증을 해답으로 바꾸는 탐구자"),
                 ("💻", "프로그래머", "논리 구조를 코드로 구현하는 두뇌"),
                 ("🧩", "철학자", "본질을 파고드는 깊은 사유가")],
    },
    "ESTP": {
        "poke_id": 5, "poke_name": "리자드 (Charmeleon)",
        "desc": "열정 넘치는 액션형 모험가",
        "color": "#FF4500",
        "jobs": [("💼", "세일즈매니저", "순발력으로 기회를 낚아채는 협상가"),
                 ("🏀", "스포츠에이전트", "현장에서 바로 승부를 보는 추진력"),
                 ("🚒", "소방관", "위기 앞에서 망설임 없는 행동가")],
    },
    "ESFP": {
        "poke_id": 25, "poke_name": "피카츄 (Pikachu)",
        "desc": "무대 위 타고난 인싸 엔터테이너",
        "color": "#FFD700",
        "jobs": [("🎤", "방송인", "에너지로 분위기를 사로잡는 스타"),
                 ("🎉", "이벤트플래너", "즐거움을 기획하는 무드메이커"),
                 ("🧳", "여행가이드", "설렘을 함께 나누는 동행자")],
    },
    "ENFP": {
        "poke_id": 133, "poke_name": "이브이 (Eevee)",
        "desc": "무한한 가능성을 품은 자유로운 영혼",
        "color": "#DDA0DD",
        "jobs": [("📣", "마케터", "톡톡 튀는 아이디어로 시선을 사로잡는 기획자"),
                 ("🎬", "크리에이터", "세상에 없던 콘텐츠를 만드는 상상가"),
                 ("🚀", "스타트업 창업가", "열정 하나로 새 판을 짜는 도전가")],
    },
    "ENTP": {
        "poke_id": 571, "poke_name": "조로아크 (Zoroark)",
        "desc": "재기발랄한 논쟁의 마법사",
        "color": "#8B008B",
        "jobs": [("⚖️", "변호사", "논리와 언변으로 승부하는 전략가"),
                 ("💡", "발명가", "기발한 아이디어를 현실로 만드는 사람"),
                 ("💰", "벤처투자자", "남들이 못 보는 기회를 읽는 안목")],
    },
    "ESTJ": {
        "poke_id": 68, "poke_name": "괴력몬 (Machamp)",
        "desc": "강력한 추진력의 타고난 관리자",
        "color": "#B22222",
        "jobs": [("🏢", "경영관리자", "조직을 일사불란하게 이끄는 리더"),
                 ("📋", "프로젝트매니저", "계획대로 결과를 만들어내는 실행력"),
                 ("🎖️", "장교/군인", "규율과 책임감의 표본")],
    },
    "ESFJ": {
        "poke_id": 35, "poke_name": "삐삐 (Clefairy)",
        "desc": "다정함이 넘치는 분위기 메이커",
        "color": "#FFC0CB",
        "jobs": [("🎊", "이벤트코디네이터", "모두를 챙기는 세심한 진행자"),
                 ("🧑‍🤝‍🧑", "인사담당자", "사람 사이를 잇는 따뜻한 조율자"),
                 ("💍", "웨딩플래너", "행복한 순간을 완성하는 조력자")],
    },
    "ENFJ": {
        "poke_id": 448, "poke_name": "루카리오 (Lucario)",
        "desc": "카리스마 넘치는 영감의 멘토",
        "color": "#4682B4",
        "jobs": [("🎯", "HR 코치", "사람의 잠재력을 이끌어내는 힘"),
                 ("👩‍🏫", "교사", "성장을 함께하는 든든한 안내자"),
                 ("🗳️", "정치인/리더", "비전으로 사람들을 움직이는 힘")],
    },
    "ENTJ": {
        "poke_id": 6, "poke_name": "리자몽 (Charizard)",
        "desc": "타고난 카리스마의 지휘관",
        "color": "#FF6347",
        "jobs": [("👔", "CEO", "큰 그림을 그리고 밀어붙이는 결단력"),
                 ("📊", "경영컨설턴트", "냉철한 분석으로 방향을 제시하는 사람"),
                 ("🏆", "정치 지도자", "목표를 향해 조직을 이끄는 추진력")],
    },
}
 
POKE_IMG_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{}.png"
 
# ========================================
# 커스텀 CSS (화려한 시각 효과)
# ========================================
st.markdown("""
<style>
@keyframes fadeInUp {
    0% { opacity: 0; transform: translateY(30px); }
    100% { opacity: 1; transform: translateY(0); }
}
@keyframes float {
    0% { transform: translateY(0px); }
    50% { transform: translateY(-15px); }
    100% { transform: translateY(0px); }
}
@keyframes sparkle {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
@keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
 
.main-title {
    text-align: center;
    font-size: 2.6rem;
    font-weight: 800;
    background: linear-gradient(90deg, #FF6B6B, #FFD93D, #6BCB77, #4D96FF, #FF6B6B);
    background-size: 300% 300%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: gradientShift 6s ease infinite;
    margin-bottom: 0px;
}
.sub-title {
    text-align: center;
    color: #888;
    font-size: 1.1rem;
    margin-bottom: 25px;
    animation: sparkle 2.5s ease-in-out infinite;
}
 
.poke-card {
    animation: fadeInUp 0.7s ease-out;
    background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
    border-radius: 24px;
    padding: 25px;
    text-align: center;
    border: 2px solid var(--accent, #ccc);
    box-shadow: 0 8px 32px rgba(0,0,0,0.15);
    margin-bottom: 20px;
}
.poke-img {
    animation: float 3s ease-in-out infinite;
}
.poke-name {
    font-size: 1.6rem;
    font-weight: 800;
    margin-top: 10px;
}
.poke-desc {
    font-size: 1.05rem;
    color: #aaa;
    margin-top: 4px;
}
 
.job-card {
    animation: fadeInUp 0.9s ease-out;
    background: linear-gradient(135deg, rgba(255,255,255,0.07), rgba(255,255,255,0.01));
    border-radius: 18px;
    padding: 18px 20px;
    margin-bottom: 14px;
    border-left: 6px solid var(--accent, #ccc);
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.job-card:hover {
    transform: translateX(8px) scale(1.02);
    box-shadow: 0 6px 20px rgba(0,0,0,0.25);
}
.job-emoji {
    font-size: 1.8rem;
    margin-right: 10px;
}
.job-title {
    font-size: 1.25rem;
    font-weight: 700;
}
.job-reason {
    font-size: 0.95rem;
    color: #999;
    margin-top: 3px;
}
</style>
""", unsafe_allow_html=True)
 
# ========================================
# 헤더
# ========================================
st.markdown('<div class="main-title">🔮 MBTI 포켓몬 직업 매칭 🎴</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">✨ 당신의 MBTI와 찰떡궁합인 포켓몬 & 추천 직업 3가지 ✨</div>', unsafe_allow_html=True)
 
st.write("")
 
# ========================================
# MBTI 선택
# ========================================
mbti_list = list(MBTI_DATA.keys())
selected = st.selectbox("🧬 당신의 MBTI를 선택하세요", mbti_list, index=None, placeholder="MBTI를 골라주세요 👇")
 
if selected:
    data = MBTI_DATA[selected]
    img_url = POKE_IMG_URL.format(data["poke_id"])
    color = data["color"]
 
    # 랜덤 축하 효과 🎉
    effect = random.choice(["balloons", "snow"])
    if effect == "balloons":
        st.balloons()
    else:
        st.snow()
 
    # 포켓몬 카드
    st.markdown(f"""
    <div class="poke-card" style="--accent:{color};">
        <div class="poke-img">
            <img src="{img_url}" width="220">
        </div>
        <div class="poke-name" style="color:{color};">⚡ {selected}는 <b>{data['poke_name']}</b> 타입! ⚡</div>
        <div class="poke-desc">💫 {data['desc']} 💫</div>
    </div>
    """, unsafe_allow_html=True)
 
    st.markdown("### 🎯 이런 직업이 잘 어울려요!")
 
    for emoji, job, reason in data["jobs"]:
        st.markdown(f"""
        <div class="job-card" style="--accent:{color};">
            <span class="job-emoji">{emoji}</span><span class="job-title">{job}</span>
            <div class="job-reason">👉 {reason}</div>
        </div>
        """, unsafe_allow_html=True)
 
    st.success(f"🌟 {selected} 유형이신 당신, {data['poke_name']}처럼 멋진 커리어를 만들어보세요! 🌟")
else:
    st.info("👆 위에서 MBTI를 선택하면 결과가 짠! 하고 나타나요 🎉")
  
st.markdown("---")
st.caption("🎮 Made with Streamlit · Pokémon 이미지는 PokeAPI 공식 아트워크를 사용합니다 ⚡")
st.markdown("---")
st.caption("🎮 Made with Streamlit · Pokémon 이미지는 PokeAPI 공식 아트워크를 사용합니다 ⚡")

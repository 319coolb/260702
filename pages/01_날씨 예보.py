import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# ----------------------------------------------------------------------------
# 기본 설정
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="날씨 예보",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# WMO 날씨 코드 -> (이모지, 설명) 매핑
# https://open-meteo.com/en/docs 참고
# ----------------------------------------------------------------------------
WEATHER_CODE_MAP = {
    0: ("☀️", "맑음"),
    1: ("🌤️", "대체로 맑음"),
    2: ("⛅", "구름 조금"),
    3: ("☁️", "흐림"),
    45: ("🌫️", "안개"),
    48: ("🌫️", "짙은 안개"),
    51: ("🌦️", "약한 이슬비"),
    53: ("🌦️", "이슬비"),
    55: ("🌧️", "강한 이슬비"),
    56: ("🌧️", "약한 얼음 이슬비"),
    57: ("🌧️", "강한 얼음 이슬비"),
    61: ("🌧️", "약한 비"),
    63: ("🌧️", "비"),
    65: ("🌧️", "강한 비"),
    66: ("🌧️", "약한 어는 비"),
    67: ("🌧️", "강한 어는 비"),
    71: ("🌨️", "약한 눈"),
    73: ("🌨️", "눈"),
    75: ("❄️", "강한 눈"),
    77: ("❄️", "싸락눈"),
    80: ("🌦️", "약한 소나기"),
    81: ("🌧️", "소나기"),
    82: ("⛈️", "강한 소나기"),
    85: ("🌨️", "약한 소낙눈"),
    86: ("❄️", "강한 소낙눈"),
    95: ("⛈️", "뇌우"),
    96: ("⛈️", "우박 동반 뇌우"),
    99: ("⛈️", "강한 우박 동반 뇌우"),
}


def get_weather_icon(code: int):
    return WEATHER_CODE_MAP.get(int(code), ("❓", "알 수 없음"))


# ----------------------------------------------------------------------------
# API 호출 함수 (캐싱으로 불필요한 재호출 방지)
# ----------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def geocode_city(city_name: str):
    """도시 이름으로 위도/경도를 검색합니다."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city_name, "count": 5, "language": "ko", "format": "json"}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


@st.cache_data(ttl=600, show_spinner=False)
def fetch_weather(lat: float, lon: float, timezone: str = "auto"):
    """시간별/일별 날씨 데이터를 가져옵니다."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(
            [
                "temperature_2m",
                "apparent_temperature",
                "precipitation_probability",
                "weathercode",
                "relative_humidity_2m",
                "wind_speed_10m",
            ]
        ),
        "daily": ",".join(
            [
                "weathercode",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "sunrise",
                "sunset",
            ]
        ),
        "current_weather": True,
        "timezone": timezone,
        "forecast_days": 7,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


# ----------------------------------------------------------------------------
# 스타일 (카드형 UI를 위한 커스텀 CSS)
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .big-temp {
        font-size: 4rem;
        font-weight: 700;
        line-height: 1.1;
    }
    .weather-desc {
        font-size: 1.3rem;
        color: #555;
        margin-top: -8px;
    }
    .metric-card {
        background-color: rgba(120,120,120,0.08);
        border-radius: 14px;
        padding: 14px 10px;
        text-align: center;
    }
    .hour-card {
        background-color: rgba(120,120,120,0.08);
        border-radius: 14px;
        padding: 10px 6px;
        text-align: center;
        min-width: 78px;
    }
    .day-card {
        background-color: rgba(120,120,120,0.08);
        border-radius: 14px;
        padding: 14px 8px;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# 사이드바 - 도시 검색
# ----------------------------------------------------------------------------
st.sidebar.title("🌍 지역 검색")
default_city = "Seoul"
city_input = st.sidebar.text_input("도시 이름을 입력하세요", value=default_city)

if "selected_location" not in st.session_state:
    st.session_state.selected_location = None

search_clicked = st.sidebar.button("🔍 검색", use_container_width=True)

if search_clicked or st.session_state.selected_location is None:
    if city_input.strip():
        with st.spinner("도시를 검색하는 중..."):
            results = geocode_city(city_input.strip())
        if results:
            options = {
                f"{r['name']}, {r.get('admin1', '')} {r.get('country', '')} "
                f"({r['latitude']:.2f}, {r['longitude']:.2f})": r
                for r in results
            }
            choice = st.sidebar.selectbox("검색 결과 선택", list(options.keys()))
            st.session_state.selected_location = options[choice]
        else:
            st.sidebar.error("검색 결과가 없습니다. 다른 이름으로 시도해보세요.")

location = st.session_state.selected_location

st.sidebar.markdown("---")
st.sidebar.caption("데이터 제공: Open-Meteo (API 키 불필요)")

# ----------------------------------------------------------------------------
# 메인 화면
# ----------------------------------------------------------------------------
if location is None:
    st.title("🌤️ 날씨 예보")
    st.info("왼쪽 사이드바에서 도시를 검색해주세요.")
    st.stop()

lat, lon = location["latitude"], location["longitude"]
place_name = f"{location['name']}, {location.get('admin1', '')} {location.get('country', '')}".strip()
timezone = location.get("timezone", "auto")

with st.spinner("날씨 정보를 불러오는 중..."):
    try:
        weather = fetch_weather(lat, lon, timezone)
    except Exception as e:
        st.error(f"날씨 정보를 불러오지 못했습니다: {e}")
        st.stop()

current = weather.get("current_weather", {})
hourly = weather["hourly"]
daily = weather["daily"]

hourly_df = pd.DataFrame(
    {
        "time": pd.to_datetime(hourly["time"]),
        "temp": hourly["temperature_2m"],
        "feels_like": hourly["apparent_temperature"],
        "precip_prob": hourly["precipitation_probability"],
        "code": hourly["weathercode"],
        "humidity": hourly["relative_humidity_2m"],
        "wind": hourly["wind_speed_10m"],
    }
)

daily_df = pd.DataFrame(
    {
        "date": pd.to_datetime(daily["time"]),
        "code": daily["weathercode"],
        "temp_max": daily["temperature_2m_max"],
        "temp_min": daily["temperature_2m_min"],
        "precip_prob": daily["precipitation_probability_max"],
        "sunrise": pd.to_datetime(daily["sunrise"]),
        "sunset": pd.to_datetime(daily["sunset"]),
    }
)

# ----------------------------------------------------------------------------
# 헤더 - 현재 날씨
# ----------------------------------------------------------------------------
st.title(f"🌤️ {place_name} 날씨")
st.caption(f"업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')} 기준")

icon, desc = get_weather_icon(current.get("weathercode", 0))

col_main, col_info = st.columns([1.2, 2])

with col_main:
    st.markdown(f"<div style='font-size:5rem'>{icon}</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='big-temp'>{current.get('temperature', 0):.0f}°C</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='weather-desc'>{desc}</div>", unsafe_allow_html=True)

with col_info:
    today = daily_df.iloc[0]
    now_row = hourly_df.iloc[(hourly_df["time"] - pd.Timestamp.now()).abs().argsort()[:1]]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"<div class='metric-card'>🌡️<br><b>체감</b><br>{float(now_row['feels_like'].values[0]):.0f}°C</div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div class='metric-card'>💧<br><b>습도</b><br>{float(now_row['humidity'].values[0]):.0f}%</div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"<div class='metric-card'>💨<br><b>바람</b><br>{float(now_row['wind'].values[0]):.0f}km/h</div>",
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"<div class='metric-card'>☔<br><b>강수확률</b><br>{today['precip_prob']:.0f}%</div>",
            unsafe_allow_html=True,
        )
    st.markdown("")
    st.markdown(
        f"오늘 최고 **{today['temp_max']:.0f}°C** / 최저 **{today['temp_min']:.0f}°C**　"
        f"🌅 일출 {today['sunrise'].strftime('%H:%M')}　🌇 일몰 {today['sunset'].strftime('%H:%M')}"
    )

st.markdown("---")

# ----------------------------------------------------------------------------
# 오늘의 시간별 날씨
# ----------------------------------------------------------------------------
st.subheader("⏰ 오늘의 시간별 날씨")

today_date = pd.Timestamp.now(tz=hourly_df["time"].dt.tz).date() if hourly_df["time"].dt.tz else pd.Timestamp.now().date()
today_hourly = hourly_df[hourly_df["time"].dt.date == pd.Timestamp.now().date()].reset_index(drop=True)

# 시간별 카드 (가로 스크롤 느낌으로 컬럼 배치)
hour_cols = st.columns(len(today_hourly)) if len(today_hourly) > 0 else []
for i, row in today_hourly.iterrows():
    icon_h, desc_h = get_weather_icon(row["code"])
    label_time = "지금" if row["time"].hour == pd.Timestamp.now().hour else row["time"].strftime("%H시")
    with hour_cols[i]:
        st.markdown(
            f"""<div class='hour-card'>
                <b>{label_time}</b><br>
                <span style='font-size:1.6rem'>{icon_h}</span><br>
                <b>{row['temp']:.0f}°</b><br>
                <span style='font-size:0.75rem;color:#5b9bd5'>💧{row['precip_prob']:.0f}%</span>
                </div>""",
            unsafe_allow_html=True,
        )

# 시간별 기온 그래프
st.markdown("")
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=today_hourly["time"].dt.strftime("%H시"),
        y=today_hourly["temp"],
        mode="lines+markers+text",
        text=[f"{t:.0f}°" for t in today_hourly["temp"]],
        textposition="top center",
        line=dict(color="#f39c12", width=3),
        marker=dict(size=7),
        name="기온",
    )
)
fig.add_trace(
    go.Bar(
        x=today_hourly["time"].dt.strftime("%H시"),
        y=today_hourly["precip_prob"],
        name="강수확률(%)",
        yaxis="y2",
        opacity=0.25,
        marker_color="#5b9bd5",
    )
)
fig.update_layout(
    height=320,
    margin=dict(l=10, r=10, t=30, b=10),
    yaxis=dict(title="기온(°C)"),
    yaxis2=dict(title="강수확률(%)", overlaying="y", side="right", range=[0, 100]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ----------------------------------------------------------------------------
# 주간 예보 (7일)
# ----------------------------------------------------------------------------
st.subheader("📅 주간 예보 (7일)")

day_cols = st.columns(len(daily_df))
weekday_kr = ["월", "화", "수", "목", "금", "토", "일"]
for i, row in daily_df.iterrows():
    icon_d, desc_d = get_weather_icon(row["code"])
    day_label = "오늘" if i == 0 else weekday_kr[row["date"].weekday()]
    with day_cols[i]:
        st.markdown(
            f"""<div class='day-card'>
                <b>{day_label}</b><br>
                <span style='font-size:0.75rem;color:#888'>{row['date'].strftime('%m/%d')}</span><br>
                <span style='font-size:2rem'>{icon_d}</span><br>
                <span style='font-size:0.8rem'>{desc_d}</span><br>
                <b style='color:#e74c3c'>{row['temp_max']:.0f}°</b> /
                <span style='color:#3498db'>{row['temp_min']:.0f}°</span><br>
                <span style='font-size:0.75rem;color:#5b9bd5'>💧{row['precip_prob']:.0f}%</span>
                </div>""",
            unsafe_allow_html=True,
        )

st.markdown("")
st.caption("ⓘ 본 서비스는 Open-Meteo의 무료 공개 기상 데이터를 사용합니다.")

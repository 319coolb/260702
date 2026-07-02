import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# =========================================================
# 기본 설정
# =========================================================
st.set_page_config(
    page_title="글로벌·국내 주식 분석기",
    page_icon="📈",
    layout="wide",
)

st.title("📈 글로벌 · 한국 주식 데이터 분석기")
st.caption("yfinance로 데이터를 가져오고 Plotly로 인터랙티브 차트를 그려드려요. "
           "주식 용어가 헷갈리면 하단의 '주식 용어 사전'을 펼쳐보세요 🙂")

# =========================================================
# 사이드바 - 입력
# =========================================================
st.sidebar.header("🔎 조회 설정")

market = st.sidebar.radio(
    "시장 선택",
    ["🇺🇸 해외 주식", "🇰🇷 국내 주식"],
    help="국내 주식은 종목코드(6자리 숫자)를 입력하면 자동으로 코스피/코스닥을 찾아드려요.",
)

# 자주 찾는 종목 예시 (사용자가 바로 눌러볼 수 있도록)
GLOBAL_PRESETS = {
    "애플 (AAPL)": "AAPL",
    "테슬라 (TSLA)": "TSLA",
    "엔비디아 (NVDA)": "NVDA",
    "마이크로소프트 (MSFT)": "MSFT",
    "구글 (GOOGL)": "GOOGL",
    "아마존 (AMZN)": "AMZN",
}
KOREA_PRESETS = {
    "삼성전자 (005930)": "005930",
    "SK하이닉스 (000660)": "000660",
    "네이버 (035420)": "035420",
    "카카오 (035720)": "035720",
    "현대차 (005380)": "005380",
    "LG에너지솔루션 (373220)": "373220",
}

if market == "🇺🇸 해외 주식":
    preset_label = st.sidebar.selectbox("빠른 선택 (선택 안 해도 됨)", ["직접 입력"] + list(GLOBAL_PRESETS.keys()))
    default_ticker = GLOBAL_PRESETS.get(preset_label, "AAPL")
    ticker_input = st.sidebar.text_input(
        "티커(Ticker) 입력",
        value=default_ticker if preset_label != "직접 입력" else "AAPL",
        help="예: AAPL(애플), TSLA(테슬라), 005930.KS 처럼 종목의 고유 코드예요.",
    ).strip().upper()
    resolved_ticker = ticker_input
else:
    preset_label = st.sidebar.selectbox("빠른 선택 (선택 안 해도 됨)", ["직접 입력"] + list(KOREA_PRESETS.keys()))
    default_code = KOREA_PRESETS.get(preset_label, "005930")
    code_input = st.sidebar.text_input(
        "종목코드 6자리 입력",
        value=default_code if preset_label != "직접 입력" else "005930",
        help="예: 삼성전자 005930, 카카오 035720. 코스피/코스닥 자동 판별해드려요.",
    ).strip()
    resolved_ticker = code_input  # 실제 접미사(.KS/.KQ)는 아래에서 자동 판별

st.sidebar.markdown("---")

today = datetime.today()
default_start = today - timedelta(days=365)
start_date = st.sidebar.date_input("시작일", value=default_start)
end_date = st.sidebar.date_input("종료일", value=today)

interval = st.sidebar.selectbox(
    "봉 간격 (Interval)",
    ["1d", "1wk", "1mo"],
    format_func=lambda x: {"1d": "일봉(1일)", "1wk": "주봉(1주)", "1mo": "월봉(1개월)"}[x],
)

st.sidebar.markdown("---")
st.sidebar.subheader("📐 이동평균선(MA) 설정")
ma_short = st.sidebar.number_input("단기 이동평균 (일)", min_value=2, max_value=100, value=20)
ma_long = st.sidebar.number_input("장기 이동평균 (일)", min_value=5, max_value=300, value=60)

show_rsi = st.sidebar.checkbox("RSI 지표 표시", value=True)


# =========================================================
# 데이터 로딩 함수
# =========================================================
@st.cache_data(ttl=600, show_spinner=False)
def fetch_data(ticker: str, start, end, interval: str):
    df = yf.download(ticker, start=start, end=end, interval=interval, progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


@st.cache_data(ttl=600, show_spinner=False)
def fetch_info(ticker: str):
    try:
        t = yf.Ticker(ticker)
        return t.info
    except Exception:
        return {}


def resolve_korean_ticker(code: str):
    """6자리 종목코드에 .KS(코스피) 또는 .KQ(코스닥)을 자동으로 붙여 데이터가 있는 쪽을 반환"""
    for suffix in [".KS", ".KQ"]:
        candidate = f"{code}{suffix}"
        try:
            df = yf.download(candidate, period="5d", progress=False, auto_adjust=False)
            if not df.empty:
                return candidate
        except Exception:
            continue
    return None


def calc_rsi(series: pd.Series, period: int = 14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# =========================================================
# 실제 조회 및 시세 처리
# =========================================================
final_ticker = resolved_ticker
if market == "🇰🇷 국내 주식":
    if not code_input.isdigit() or len(code_input) != 6:
        st.warning("종목코드는 6자리 숫자로 입력해주세요. 예: 005930")
        st.stop()
    with st.spinner("코스피/코스닥 확인 중..."):
        final_ticker = resolve_korean_ticker(code_input)
    if final_ticker is None:
        st.error("해당 종목코드의 데이터를 찾을 수 없어요. 코드를 다시 확인해주세요.")
        st.stop()

if not final_ticker:
    st.info("왼쪽 사이드바에서 종목을 입력해주세요.")
    st.stop()

with st.spinner(f"{final_ticker} 데이터를 불러오는 중..."):
    data = fetch_data(final_ticker, start_date, end_date, interval)
    info = fetch_info(final_ticker)

if data.empty:
    st.error("데이터가 없어요. 티커/종목코드나 기간을 다시 확인해주세요.")
    st.stop()

data = data.dropna(subset=["Open", "High", "Low", "Close"])
data[f"MA{ma_short}"] = data["Close"].rolling(window=ma_short).mean()
data[f"MA{ma_long}"] = data["Close"].rolling(window=ma_long).mean()
data["RSI"] = calc_rsi(data["Close"])

company_name = info.get("longName") or info.get("shortName") or final_ticker
currency = info.get("currency", "")

# =========================================================
# 상단 요약 지표
# =========================================================
last_close = float(data["Close"].iloc[-1])
prev_close = float(data["Close"].iloc[-2]) if len(data) > 1 else last_close
change = last_close - prev_close
pct_change = (change / prev_close * 100) if prev_close else 0
period_high = float(data["High"].max())
period_low = float(data["Low"].min())
last_volume = int(data["Volume"].iloc[-1])

st.subheader(f"{company_name}  ({final_ticker})")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("현재가", f"{last_close:,.2f} {currency}", f"{change:,.2f} ({pct_change:+.2f}%)")
col2.metric("조회기간 최고가", f"{period_high:,.2f}")
col3.metric("조회기간 최저가", f"{period_low:,.2f}")
col4.metric("최근 거래량", f"{last_volume:,}")
if info.get("marketCap"):
    col5.metric("시가총액", f"{info['marketCap']:,}")
else:
    col5.metric("시가총액", "정보 없음")

st.markdown("---")

# =========================================================
# 캔들스틱 + 이동평균선 + 거래량 차트 (Plotly)
# =========================================================
fig = make_subplots(
    rows=3 if show_rsi else 2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.6, 0.2, 0.2] if show_rsi else [0.7, 0.3],
    subplot_titles=("가격 (캔들차트)", "거래량", "RSI") if show_rsi else ("가격 (캔들차트)", "거래량"),
)

fig.add_trace(
    go.Candlestick(
        x=data.index,
        open=data["Open"],
        high=data["High"],
        low=data["Low"],
        close=data["Close"],
        name="가격",
        increasing_line_color="#e74c3c",
        decreasing_line_color="#3498db",
    ),
    row=1, col=1,
)
fig.add_trace(
    go.Scatter(x=data.index, y=data[f"MA{ma_short}"], mode="lines",
               name=f"MA{ma_short}", line=dict(width=1.3, color="#f39c12")),
    row=1, col=1,
)
fig.add_trace(
    go.Scatter(x=data.index, y=data[f"MA{ma_long}"], mode="lines",
               name=f"MA{ma_long}", line=dict(width=1.3, color="#8e44ad")),
    row=1, col=1,
)

vol_colors = np.where(data["Close"] >= data["Open"], "#e74c3c", "#3498db")
fig.add_trace(
    go.Bar(x=data.index, y=data["Volume"], name="거래량", marker_color=vol_colors),
    row=2, col=1,
)

if show_rsi:
    fig.add_trace(
        go.Scatter(x=data.index, y=data["RSI"], mode="lines", name="RSI", line=dict(width=1.3, color="#16a085")),
        row=3, col=1,
    )
    fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="blue", row=3, col=1)

fig.update_layout(
    height=800,
    xaxis_rangeslider_visible=False,
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=40, b=10),
)

st.plotly_chart(fig, use_container_width=True)

# =========================================================
# 데이터 테이블 + 복붙(복사) 편의 기능
# =========================================================
st.markdown("---")
st.subheader("📋 데이터 테이블 (복사/붙여넣기 편하게)")

show_table = data[["Open", "High", "Low", "Close", "Volume", f"MA{ma_short}", f"MA{ma_long}", "RSI"]].copy()
show_table = show_table.sort_index(ascending=False).round(2)

tab1, tab2 = st.tabs(["표로 보기 (드래그로 복사 가능)", "텍스트로 복사하기 (CSV 형식)"])

with tab1:
    st.dataframe(show_table, use_container_width=True, height=350)
    csv_bytes = show_table.to_csv().encode("utf-8-sig")
    st.download_button("📥 CSV 파일로 다운로드", data=csv_bytes,
                        file_name=f"{final_ticker}_data.csv", mime="text/csv")

with tab2:
    st.caption("아래 박스를 클릭한 뒤 Ctrl+A(전체선택) → Ctrl+C(복사)로 엑셀/시트에 바로 붙여넣을 수 있어요.")
    st.text_area("CSV 텍스트", value=show_table.to_csv(), height=300)

# =========================================================
# 요약 텍스트 (복붙용)
# =========================================================
st.markdown("---")
st.subheader("📝 한눈에 보는 요약 (복붙용)")
summary_text = f"""[{company_name} ({final_ticker})] 요약
- 현재가: {last_close:,.2f} {currency}
- 전일대비: {change:,.2f} ({pct_change:+.2f}%)
- 조회기간 최고가: {period_high:,.2f}
- 조회기간 최저가: {period_low:,.2f}
- 최근 거래량: {last_volume:,}
- 시가총액: {info.get('marketCap', '정보 없음')}
- 조회기간: {start_date} ~ {end_date} ({ {"1d":"일봉","1wk":"주봉","1mo":"월봉"}[interval] })
"""
st.code(summary_text, language="text")

# =========================================================
# 주식 용어 사전 (초보자용 친절 설명)
# =========================================================
st.markdown("---")
st.header("📖 주식 용어 사전 (누구나 쉽게!)")
st.caption("차트나 지표를 보다가 헷갈리는 용어가 있으면 아래에서 찾아보세요.")

terms = {
    "캔들차트 (봉차트)": (
        "하루(혹은 일정 기간) 동안의 '시가(시작 가격)', '종가(끝 가격)', '고가(가장 높았던 가격)', "
        "'저가(가장 낮았던 가격)'를 막대(캔들) 모양으로 표현한 차트예요. "
        "빨간색(양봉)은 시작보다 가격이 올라서 끝난 것, 파란색(음봉)은 시작보다 가격이 내려서 끝난 것을 의미해요. "
        "(색상 규칙은 나라/플랫폼마다 반대일 수 있어요!)"
    ),
    "이동평균선 (MA, Moving Average)": (
        "최근 일정 기간(예: 20일)의 종가를 평균 낸 값을 선으로 이어 그린 거예요. "
        "가격의 큰 흐름(추세)을 부드럽게 보여줘서, 지금 주가가 평소보다 비싼지 싼지 가늠하는 데 도움이 돼요. "
        "단기 이동평균선이 장기 이동평균선을 위로 뚫고 올라가는 걸 '골든크로스'(상승 신호로 해석), "
        "반대를 '데드크로스'(하락 신호로 해석)라고 불러요."
    ),
    "거래량 (Volume)": (
        "특정 기간 동안 실제로 사고팔린 주식의 수량이에요. "
        "거래량이 갑자기 크게 늘어나면 그만큼 많은 투자자들이 관심을 갖고 있다는 신호로 해석되곤 해요."
    ),
    "RSI (상대강도지수, Relative Strength Index)": (
        "최근 가격이 얼마나 많이 올랐는지/내렸는지를 0~100 사이 숫자로 나타낸 지표예요. "
        "일반적으로 70 이상이면 '많이 올라서 과열된 상태(과매수)', 30 이하면 '많이 떨어져서 저평가된 상태(과매도)'로 해석해요. "
        "다만 절대적인 매매 신호는 아니고, 참고 지표로 활용하는 게 좋아요."
    ),
    "등락률": (
        "전날(혹은 이전 기준일) 가격 대비 오늘 가격이 몇 % 오르거나 내렸는지를 보여줘요. "
        "예를 들어 어제 10,000원이던 주가가 오늘 10,500원이 되면 등락률은 +5%예요."
    ),
    "시가총액 (Market Cap)": (
        "'현재 주가 × 전체 발행 주식 수'로 계산하는, 그 회사 전체의 시장 가치예요. "
        "시가총액이 클수록 흔히 '대형주'로 분류되고, 상대적으로 주가 변동이 덜 급격한 경향이 있어요."
    ),
    "티커 (Ticker)": (
        "주식 종목을 구분하기 위한 고유한 코드예요. 예를 들어 애플은 'AAPL', 테슬라는 'TSLA'예요. "
        "한국 주식은 보통 6자리 숫자 코드를 쓰고(예: 삼성전자 005930), yfinance에서는 뒤에 "
        "코스피는 '.KS', 코스닥은 '.KQ'를 붙여서 조회해요."
    ),
    "코스피 / 코스닥": (
        "코스피(KOSPI)는 한국의 대표 증권거래소 시장으로, 삼성전자 같은 대형 우량 기업들이 주로 상장돼 있어요. "
        "코스닥(KOSDAQ)은 상대적으로 중소형·기술주 중심의 시장이에요."
    ),
    "PER (주가수익비율)": (
        "주가를 그 회사의 주당순이익(EPS)으로 나눈 값이에요. "
        "'지금 주가가 그 회사가 버는 돈에 비해 비싼 편인지 싼 편인지'를 가늠하는 대표적인 지표 중 하나예요. "
        "숫자가 낮을수록 이익 대비 저평가되어 있다고 해석되는 경우가 많지만, 업종마다 적정 수준이 달라요."
    ),
    "PBR (주가순자산비율)": (
        "주가를 그 회사의 주당순자산(자산에서 부채를 뺀 값)으로 나눈 값이에요. "
        "회사가 가진 순자산 대비 주가가 어느 정도 수준인지 보여주는 지표예요."
    ),
    "52주 최고가 / 최저가": (
        "최근 52주(약 1년) 동안 그 주식이 기록한 가장 높은 가격과 가장 낮은 가격이에요. "
        "지금 가격이 그 범위 안에서 어느 위치에 있는지를 보면 상대적인 위치를 가늠할 수 있어요."
    ),
}

for term, desc in terms.items():
    with st.expander(f"❓ {term}"):
        st.write(desc)

st.markdown("---")
st.caption("⚠️ 이 앱이 제공하는 정보는 투자 참고용이며, 투자 판단과 그 결과에 대한 책임은 투자자 본인에게 있습니다.")

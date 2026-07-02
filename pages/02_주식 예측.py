import random
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ----------------------------------------------------------------------------
# 기본 설정
# ----------------------------------------------------------------------------
st.set_page_config(page_title="주식 투자 시뮬레이션 게임", page_icon="📈", layout="centered")

TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "NFLX",
    "JPM", "DIS", "KO", "MCD", "NKE", "INTC", "AMD", "BA", "V",
    "WMT", "PG", "JNJ", "SBUX", "ADBE", "CSCO", "PEP",
    "005930.KS",  # 삼성전자
    "000660.KS",  # SK하이닉스
    "035420.KS",  # 네이버
]

VISIBLE_DAYS = 60      # 게임 시작 시 보여주는 캔들 수
HIDDEN_DAYS = 20       # 투자 판단 후 공개되는 미래 캔들 수
TOTAL_ROUNDS = 5       # 총 라운드 수
START_CASH = 1_000_000  # 시작 가상 자금 (원 단위로 취급)

RANK_TABLE = [
    (20, "🏆 투자의 신"),
    (10, "🥇 고수 투자자"),
    (3, "🥈 성장하는 투자자"),
    (0, "🥉 신중한 초보"),
    (-100, "📉 다시 공부가 필요해요"),
]


def rank_label(total_return_pct: float) -> str:
    for threshold, label in RANK_TABLE:
        if total_return_pct >= threshold:
            return label
    return RANK_TABLE[-1][1]


# ----------------------------------------------------------------------------
# 데이터 로딩 (티커별 전체 히스토리를 캐싱하여 재사용)
# ----------------------------------------------------------------------------
@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def load_history(ticker: str) -> pd.DataFrame:
    df = yf.download(ticker, period="10y", interval="1d", progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    df = df.reset_index()
    return df


def pick_round_window():
    """무작위 종목 + 무작위 구간을 골라 (visible_df, hidden_df, ticker) 반환."""
    tickers = TICKERS.copy()
    random.shuffle(tickers)
    window_size = VISIBLE_DAYS + HIDDEN_DAYS

    for ticker in tickers:
        try:
            df = load_history(ticker)
        except Exception:
            continue
        if df is None or len(df) < window_size + 5:
            continue

        max_start = len(df) - window_size
        start_idx = random.randint(0, max_start - 1)
        window = df.iloc[start_idx:start_idx + window_size].reset_index(drop=True)

        visible_df = window.iloc[:VISIBLE_DAYS].copy()
        hidden_df = window.iloc[VISIBLE_DAYS:].copy()
        return visible_df, hidden_df, ticker

    return None, None, None


def normalize_ohlc(df: pd.DataFrame, base_price: float) -> pd.DataFrame:
    out = df.copy()
    for col in ["Open", "High", "Low", "Close"]:
        out[col] = out[col] / base_price * 100
    return out


def make_candlestick(visible_norm, hidden_norm=None, decision_line=True, ticker_label="종목"):
    fig = go.Figure()

    n_visible = len(visible_norm)
    x_visible = list(range(1, n_visible + 1))

    fig.add_trace(go.Candlestick(
        x=x_visible,
        open=visible_norm["Open"], high=visible_norm["High"],
        low=visible_norm["Low"], close=visible_norm["Close"],
        increasing_line_color="#e74c3c", decreasing_line_color="#3498db",
        name="공개된 구간",
    ))

    if hidden_norm is not None and len(hidden_norm) > 0:
        x_hidden = list(range(n_visible + 1, n_visible + len(hidden_norm) + 1))
        fig.add_trace(go.Candlestick(
            x=x_hidden,
            open=hidden_norm["Open"], high=hidden_norm["High"],
            low=hidden_norm["Low"], close=hidden_norm["Close"],
            increasing_line_color="#f1948a", decreasing_line_color="#85c1e9",
            name="미래 구간 (공개됨)",
        ))

    if decision_line:
        fig.add_vline(x=n_visible + 0.5, line_width=2, line_dash="dash", line_color="gray")
        fig.add_annotation(x=n_visible + 0.5, y=1.05, yref="paper", showarrow=False,
                            text="👉 투자 결정 시점", font=dict(size=12, color="gray"))

    fig.update_layout(
        title=f"{ticker_label} — 정규화된 가격 (Day1 = 100)",
        xaxis_title="거래일 (Day)",
        yaxis_title="정규화 가격",
        xaxis_rangeslider_visible=False,
        height=420,
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


# ----------------------------------------------------------------------------
# 세션 상태 초기화
# ----------------------------------------------------------------------------
def init_game():
    st.session_state.stage = "decision"
    st.session_state.round_no = 1
    st.session_state.cash = START_CASH
    st.session_state.log = []
    load_new_round()


def load_new_round():
    with st.spinner("과거 주가 데이터를 불러오는 중..."):
        visible_df, hidden_df, ticker = pick_round_window()
    if visible_df is None:
        st.error("데이터를 불러오지 못했습니다. 네트워크 상태를 확인하고 새로고침 해주세요.")
        st.stop()
    st.session_state.visible_df = visible_df
    st.session_state.hidden_df = hidden_df
    st.session_state.ticker = ticker
    st.session_state.stage = "decision"


if "stage" not in st.session_state:
    st.session_state.stage = "intro"


# ----------------------------------------------------------------------------
# 화면: 인트로
# ----------------------------------------------------------------------------
st.title("📈 주식 투자 시뮬레이션 게임")

if st.session_state.stage == "intro":
    st.markdown(f"""
과거 실제 주가 데이터의 일부(최근 {VISIBLE_DAYS}거래일)만 보고 투자 판단을 내려보세요.

- 종목명과 날짜는 **투자 결정 전까지 비공개**입니다 (선입견 방지).
- 매 라운드마다 **매수(Long) / 관망(Cash) / 매도(Short)** 중 하나를 고르고, 투자 비중을 정합니다.
- 판단 후 다음 {HIDDEN_DAYS}거래일의 실제 결과가 공개되고, 그에 따라 가상 자금이 변동합니다.
- 총 **{TOTAL_ROUNDS}라운드** 진행 후 최종 수익률로 등급이 매겨집니다.
- 시작 자금: **{START_CASH:,}원**
""")
    if st.button("🎮 게임 시작", type="primary"):
        init_game()
        st.rerun()

# ----------------------------------------------------------------------------
# 화면: 투자 결정
# ----------------------------------------------------------------------------
elif st.session_state.stage == "decision":
    r = st.session_state.round_no
    st.subheader(f"라운드 {r} / {TOTAL_ROUNDS}")
    st.caption("이 종목이 무엇인지, 시기가 언제인지는 아직 비공개입니다. 차트 흐름만 보고 판단하세요.")

    visible_df = st.session_state.visible_df
    base_price = float(visible_df["Open"].iloc[0])
    visible_norm = normalize_ohlc(visible_df, base_price)

    fig = make_candlestick(visible_norm, ticker_label="비공개 종목")
    st.plotly_chart(fig, use_container_width=True)

    st.metric("현재 보유 현금", f"{st.session_state.cash:,.0f} 원")

    st.markdown("### 💡 투자 결정")
    direction = st.radio(
        "포지션 선택",
        options=["매수 (상승에 베팅)", "관망 (현금 보유)", "매도/공매도 (하락에 베팅)"],
        horizontal=False,
        key=f"direction_{r}",
    )

    if direction != "관망 (현금 보유)":
        alloc_pct = st.slider("투자 비중 (보유 현금 대비 %)", min_value=10, max_value=100, value=50, step=10, key=f"alloc_{r}")
    else:
        alloc_pct = 0

    if st.button("✅ 결정 확정 및 결과 확인", type="primary"):
        st.session_state.decision = {
            "direction": direction,
            "alloc_pct": alloc_pct,
        }
        st.session_state.stage = "result"
        st.rerun()

# ----------------------------------------------------------------------------
# 화면: 결과 공개
# ----------------------------------------------------------------------------
elif st.session_state.stage == "result":
    r = st.session_state.round_no
    visible_df = st.session_state.visible_df
    hidden_df = st.session_state.hidden_df
    ticker = st.session_state.ticker
    decision = st.session_state.decision

    base_price = float(visible_df["Open"].iloc[0])
    visible_norm = normalize_ohlc(visible_df, base_price)
    hidden_norm = normalize_ohlc(hidden_df, base_price)

    start_date = pd.to_datetime(visible_df["Date"].iloc[0]).date()
    end_date = pd.to_datetime(hidden_df["Date"].iloc[-1]).date()

    st.subheader(f"라운드 {r} 결과 — {ticker}")
    st.caption(f"기간: {start_date} ~ {end_date}")

    fig = make_candlestick(visible_norm, hidden_norm=hidden_norm, ticker_label=ticker)
    st.plotly_chart(fig, use_container_width=True)

    price_at_decision = float(visible_df["Close"].iloc[-1])
    price_at_end = float(hidden_df["Close"].iloc[-1])
    stock_return = (price_at_end - price_at_decision) / price_at_decision

    direction = decision["direction"]
    alloc_pct = decision["alloc_pct"] / 100.0

    if direction.startswith("매수"):
        portfolio_return = alloc_pct * stock_return
    elif direction.startswith("매도"):
        raw_return = alloc_pct * (-stock_return)
        portfolio_return = max(raw_return, -alloc_pct)  # 손실은 투자 비중만큼으로 제한
    else:
        portfolio_return = 0.0

    old_cash = st.session_state.cash
    new_cash = old_cash * (1 + portfolio_return)
    st.session_state.cash = new_cash

    col1, col2, col3 = st.columns(3)
    col1.metric(f"{HIDDEN_DAYS}거래일 후 실제 주가 변동", f"{stock_return*100:+.2f}%")
    col2.metric("이번 라운드 손익률", f"{portfolio_return*100:+.2f}%")
    col3.metric("보유 현금", f"{new_cash:,.0f} 원", delta=f"{new_cash - old_cash:,.0f} 원")

    if portfolio_return > 0:
        st.success("좋은 판단이었어요! 📈")
    elif portfolio_return < 0:
        st.error("이번엔 아쉬웠네요. 📉")
    else:
        st.info("관망하며 리스크를 피했습니다.")

    st.session_state.log.append({
        "라운드": r,
        "종목": ticker,
        "기간": f"{start_date} ~ {end_date}",
        "선택": direction,
        "비중(%)": decision["alloc_pct"] if direction != "관망 (현금 보유)" else 0,
        "실제 주가 변동률(%)": round(stock_return * 100, 2),
        "라운드 손익률(%)": round(portfolio_return * 100, 2),
        "라운드 후 현금": round(new_cash),
    })

    if r < TOTAL_ROUNDS:
        if st.button("➡️ 다음 라운드", type="primary"):
            st.session_state.round_no += 1
            load_new_round()
            st.rerun()
    else:
        if st.button("🏁 최종 결과 보기", type="primary"):
            st.session_state.stage = "gameover"
            st.rerun()

# ----------------------------------------------------------------------------
# 화면: 게임 종료 / 최종 결과
# ----------------------------------------------------------------------------
elif st.session_state.stage == "gameover":
    st.subheader("🏁 최종 결과")

    final_cash = st.session_state.cash
    total_return_pct = (final_cash - START_CASH) / START_CASH * 100

    col1, col2 = st.columns(2)
    col1.metric("시작 자금", f"{START_CASH:,.0f} 원")
    col2.metric("최종 자금", f"{final_cash:,.0f} 원", delta=f"{total_return_pct:+.2f}%")

    st.markdown(f"## 등급: {rank_label(total_return_pct)}")

    st.markdown("### 라운드별 기록")
    log_df = pd.DataFrame(st.session_state.log)
    st.dataframe(log_df, use_container_width=True, hide_index=True)

    if st.button("🔄 다시 시작", type="primary"):
        init_game()
        st.rerun()

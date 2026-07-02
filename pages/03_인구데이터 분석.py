# -*- coding: utf-8 -*-
"""
📊 대한민국 인구 데이터 탐험 대시보드
행정안전부 「연령별 인구현황」 데이터를 활용한 교육용 인터랙티브 대시보드
"""

import re
import glob

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ────────────────────────────────────────────────────────────────
# 기본 설정
# ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="대한민국 인구 데이터 탐험 🇰🇷",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

AGE_COL_PATTERN = re.compile(r"^\d{4}년\d{2}월_(계|남|여)_(\d+세|100세 이상)$")


# ────────────────────────────────────────────────────────────────
# 데이터 로딩 & 전처리
# ────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="데이터를 불러오는 중이에요... 🔍")
def load_data(file) -> pd.DataFrame:
    df = pd.read_csv(file, encoding="cp949", dtype=str)

    # 지역명 / 지역코드 분리
    codes = df["행정구역"].str.extract(r"\((\d+)\)")[0]
    names = df["행정구역"].str.extract(r"^(.*?)\s*\(")[0].str.strip()

    # 숫자 컬럼 변환 (콤마 제거 후 숫자화)
    numeric_cols = [c for c in df.columns if c != "행정구역"]
    numeric_df = df[numeric_cols].apply(
        lambda s: pd.to_numeric(s.astype(str).str.replace(",", "", regex=False), errors="coerce")
    )

    df = pd.concat([df[["행정구역"]], numeric_df], axis=1)
    df.insert(1, "지역코드", codes)
    df.insert(2, "지역명", names)

    # 행정구역 단위 판별 (코드 뒤 0의 개수로 시도 / 시군구 / 읍면동 구분)
    def get_level(code):
        if pd.isna(code):
            return None
        trailing_zeros = len(code) - len(code.rstrip("0"))
        if trailing_zeros >= 8:
            return "시도"
        elif trailing_zeros >= 6:
            return "시군구"
        return "읍면동"

    df["구분"] = df["지역코드"].apply(get_level)
    df["시도코드"] = df["지역코드"].str[:2]

    sido_map = df.loc[df["구분"] == "시도"].set_index("시도코드")["지역명"].to_dict()
    df["상위시도"] = df["시도코드"].map(sido_map)

    return df


@st.cache_data(show_spinner=False)
def get_age_columns(columns: tuple) -> dict:
    """성별(계/남/여)별 {나이: 컬럼명} 딕셔너리 반환"""
    age_cols = {"계": {}, "남": {}, "여": {}}
    for c in columns:
        m = AGE_COL_PATTERN.match(c)
        if m:
            gender, age_str = m.groups()
            age = 100 if "이상" in age_str else int(age_str.replace("세", ""))
            age_cols[gender][age] = c
    return age_cols


@st.cache_data(show_spinner=False)
def get_total_col(columns: tuple) -> str:
    for c in columns:
        if "총인구수" in c:
            return c
    return None


def find_default_csv():
    candidates = glob.glob("*.csv") + glob.glob("data/*.csv")
    for c in candidates:
        if "연령별인구현황" in c or "population" in c.lower():
            return c
    return candidates[0] if candidates else None


# ────────────────────────────────────────────────────────────────
# 사이드바 — 데이터 소스 & 지역 선택
# ────────────────────────────────────────────────────────────────
st.sidebar.title("📊 인구 데이터 탐험")
st.sidebar.caption("행정안전부 연령별 인구현황 데이터 기반")

default_csv = find_default_csv()
uploaded = st.sidebar.file_uploader(
    "CSV 파일 업로드 (선택)", type=["csv"],
    help="비워두면 저장소에 포함된 기본 데이터를 사용해요."
)

data_source = uploaded if uploaded is not None else default_csv

if data_source is None:
    st.error(
        "📁 데이터 파일을 찾을 수 없어요! CSV 파일을 앱과 같은 폴더에 두거나, "
        "왼쪽 사이드바에서 직접 업로드해주세요."
    )
    st.stop()

df = load_data(data_source)
AGE_COLS = get_age_columns(tuple(df.columns))
TOTAL_COL = get_total_col(tuple(df.columns))
BASE_MONTH = re.search(r"(\d{4})년(\d{2})월", TOTAL_COL)
YEAR_LABEL = f"{BASE_MONTH.group(1)}년 {BASE_MONTH.group(2)}월" if BASE_MONTH else ""

st.sidebar.divider()
st.sidebar.subheader("🗺️ 지역 선택")

level_choice = st.sidebar.radio("분석 단위", ["시도", "시군구"], horizontal=True)

sido_list = sorted(df.loc[df["구분"] == "시도", "지역명"].unique().tolist())

if level_choice == "시도":
    region_choice = st.sidebar.selectbox("지역 선택", ["🇰🇷 전국"] + sido_list)
    if region_choice == "🇰🇷 전국":
        selected_row = None  # 전국은 시도 합계로 별도 계산
        region_label = "전국"
    else:
        selected_row = df[(df["구분"] == "시도") & (df["지역명"] == region_choice)].iloc[0]
        region_label = region_choice
else:
    parent_sido = st.sidebar.selectbox("시/도 선택", sido_list)
    sigungu_list = sorted(
        df.loc[(df["구분"] == "시군구") & (df["상위시도"] == parent_sido), "지역명"].unique().tolist()
    )
    region_choice = st.sidebar.selectbox("시/군/구 선택", sigungu_list)
    selected_row = df[(df["구분"] == "시군구") & (df["지역명"] == region_choice)].iloc[0]
    region_label = region_choice

st.sidebar.divider()
st.sidebar.info(
    "💡 **Tip**: '출생율 반등 탐정단' 탭에서 최근 태어난 아이들의 수가 "
    "정말 늘고 있는지 데이터로 직접 확인해볼 수 있어요!"
)


# ────────────────────────────────────────────────────────────────
# 헬퍼 함수
# ────────────────────────────────────────────────────────────────
def get_age_series(row_or_df, gender="계", agg=False):
    """나이별 인구 Series(index=나이 0~100) 반환. agg=True면 여러 행 합산."""
    cols = AGE_COLS[gender]
    ages = sorted(cols.keys())
    if agg:
        values = [row_or_df[cols[a]].sum() for a in ages]
    else:
        values = [row_or_df[cols[a]] for a in ages]
    return pd.Series(values, index=ages)


def get_region_total(row_or_df, agg=False):
    if agg:
        return row_or_df[TOTAL_COL].sum()
    return row_or_df[TOTAL_COL]


def age_group_sum(series, lo, hi):
    return series[(series.index >= lo) & (series.index <= hi)].sum()


def format_num(n):
    return f"{int(n):,}명"


sido_rows = df[df["구분"] == "시도"]

if selected_row is None:  # 전국
    male_series = get_age_series(sido_rows, "남", agg=True)
    female_series = get_age_series(sido_rows, "여", agg=True)
    total_series = get_age_series(sido_rows, "계", agg=True)
    total_pop = get_region_total(sido_rows, agg=True)
else:
    male_series = get_age_series(selected_row, "남")
    female_series = get_age_series(selected_row, "여")
    total_series = get_age_series(selected_row, "계")
    total_pop = get_region_total(selected_row)

youth = age_group_sum(total_series, 0, 14)
working = age_group_sum(total_series, 15, 64)
elderly = age_group_sum(total_series, 65, 100)
aging_index = (elderly / youth * 100) if youth > 0 else np.nan
elder_dependency = (elderly / working * 100) if working > 0 else np.nan
youth_dependency = (youth / working * 100) if working > 0 else np.nan


# ────────────────────────────────────────────────────────────────
# 헤더
# ────────────────────────────────────────────────────────────────
st.title("📊 대한민국 인구 데이터 탐험")
st.caption(f"📅 기준: {YEAR_LABEL}  |  📍 현재 보는 지역: **{region_label}**")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🏠 인구 한눈에 보기", "🗺️ 지역별 비교", "👶 출생율 반등 탐정단", "👵 고령화 리포트", "📋 원자료 탐색"]
)

# ══════════════════════════════════════════════════════════════
# TAB 1. 인구 한눈에 보기
# ══════════════════════════════════════════════════════════════
with tab1:
    st.subheader(f"🏠 {region_label} 인구, 한눈에 보기")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👨‍👩‍👧‍👦 총인구", format_num(total_pop))
    c2.metric("🧒 유소년인구 (0~14세)", format_num(youth), f"{youth/total_pop*100:.1f}%")
    c3.metric("💼 생산연령인구 (15~64세)", format_num(working), f"{working/total_pop*100:.1f}%")
    c4.metric("👴 고령인구 (65세 이상)", format_num(elderly), f"{elderly/total_pop*100:.1f}%")

    st.markdown("---")

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("#### 🎂 인구 피라미드 (남 vs 여)")
        st.caption("나이를 5살 단위로 묶어서 남녀 인구를 비교해요. 막대가 넓을수록 그 나이대 인구가 많다는 뜻이에요.")

        bins = list(range(0, 101, 5))
        bin_labels = [f"{b}~{b+4}세" if b < 100 else "100세+" for b in bins]

        def bucket_series(series):
            out = []
            for b in bins:
                if b == 100:
                    out.append(series[series.index >= 100].sum())
                else:
                    out.append(series[(series.index >= b) & (series.index < b + 5)].sum())
            return out

        male_binned = bucket_series(male_series)
        female_binned = bucket_series(female_series)

        fig_pyramid = go.Figure()
        fig_pyramid.add_trace(go.Bar(
            y=bin_labels, x=[-v for v in male_binned], orientation="h",
            name="남성", marker_color="#4C9AFF",
            hovertemplate="%{y} 남성: %{customdata:,}명<extra></extra>",
            customdata=male_binned,
        ))
        fig_pyramid.add_trace(go.Bar(
            y=bin_labels, x=female_binned, orientation="h",
            name="여성", marker_color="#FF7EB6",
            hovertemplate="%{y} 여성: %{x:,}명<extra></extra>",
        ))
        fig_pyramid.update_layout(
            barmode="relative", bargap=0.1, height=560,
            xaxis_title="인구수 (명)", yaxis_title="",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=30, b=10),
        )
        max_val = max(max(male_binned), max(female_binned))
        tick_vals = [-max_val, -max_val/2, 0, max_val/2, max_val]
        fig_pyramid.update_xaxes(
            tickvals=tick_vals,
            ticktext=[f"{int(abs(v)):,}" for v in tick_vals],
        )
        st.plotly_chart(fig_pyramid, width='stretch')

    with col_right:
        st.markdown("#### 🧮 부양비 지표")
        st.caption("생산연령인구(15~64세) 100명이 부양해야 하는 유소년·고령 인구 비율이에요.")

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=elder_dependency,
            title={"text": "노년부양비 (65세+ / 15~64세 × 100)"},
            number={"suffix": "명"},
            gauge={
                "axis": {"range": [0, max(50, elder_dependency * 1.3)]},
                "bar": {"color": "#FF6B6B"},
                "steps": [
                    {"range": [0, 15], "color": "#E8F5E9"},
                    {"range": [15, 30], "color": "#FFF9C4"},
                    {"range": [30, 100], "color": "#FFCDD2"},
                ],
            },
        ))
        fig_gauge.update_layout(height=260, margin=dict(l=20, r=20, t=60, b=10))
        st.plotly_chart(fig_gauge, width='stretch')

        st.metric("고령화지수 (65세+ / 0~14세 × 100)", f"{aging_index:,.1f}")
        st.metric("유소년부양비 (0~14세 / 15~64세 × 100)", f"{youth_dependency:,.1f}")

        with st.expander("📖 용어가 궁금해요"):
            st.markdown(
                "- **고령화지수**: 유소년 100명당 고령 인구 수. 100이 넘으면 아이보다 노인이 더 많다는 뜻이에요.\n"
                "- **노년부양비**: 일하는 사람 100명이 부양해야 할 고령 인구 수예요.\n"
                "- **유소년부양비**: 일하는 사람 100명이 부양해야 할 어린이 수예요."
            )

# ══════════════════════════════════════════════════════════════
# TAB 2. 지역별 비교
# ══════════════════════════════════════════════════════════════
with tab2:
    st.subheader("🗺️ 17개 시도, 무엇이 다를까?")

    sido_stats = sido_rows[["지역명", TOTAL_COL]].copy()
    sido_stats.columns = ["시도", "총인구"]

    youth_list, working_list, elderly_list = [], [], []
    for _, r in sido_rows.iterrows():
        s = get_age_series(r, "계")
        youth_list.append(age_group_sum(s, 0, 14))
        working_list.append(age_group_sum(s, 15, 64))
        elderly_list.append(age_group_sum(s, 65, 100))

    sido_stats["유소년인구"] = youth_list
    sido_stats["생산연령인구"] = working_list
    sido_stats["고령인구"] = elderly_list
    sido_stats["고령화지수"] = (sido_stats["고령인구"] / sido_stats["유소년인구"] * 100).round(1)
    sido_stats["선택됨"] = sido_stats["시도"] == region_label

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 📊 시도별 총인구")
        fig_bar = px.bar(
            sido_stats.sort_values("총인구", ascending=True),
            x="총인구", y="시도", orientation="h",
            color="선택됨", color_discrete_map={True: "#FFB020", False: "#4C9AFF"},
            text="총인구",
        )
        fig_bar.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig_bar.update_layout(height=560, showlegend=False, xaxis_title="총인구(명)", yaxis_title="")
        st.plotly_chart(fig_bar, width='stretch')

    with c2:
        st.markdown("#### 🌳 인구 규모 트리맵")
        st.caption("네모가 클수록 인구가 많고, 색이 진할수록 고령화지수가 높은 지역이에요.")
        fig_tree = px.treemap(
            sido_stats, path=["시도"], values="총인구", color="고령화지수",
            color_continuous_scale="RdYlGn_r",
            hover_data={"총인구": ":,", "고령화지수": ":.1f"},
        )
        fig_tree.update_layout(height=560, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_tree, width='stretch')

    st.markdown("#### 🔍 인구 규모 vs 고령화지수")
    fig_scatter = px.scatter(
        sido_stats, x="총인구", y="고령화지수", size="총인구", color="고령화지수",
        text="시도", color_continuous_scale="RdYlGn_r", size_max=60,
    )
    fig_scatter.update_traces(textposition="top center")
    fig_scatter.update_layout(height=520, xaxis_title="총인구(명)", yaxis_title="고령화지수")
    st.plotly_chart(fig_scatter, width='stretch')

# ══════════════════════════════════════════════════════════════
# TAB 3. 출생율 반등 탐정단 (핵심 인사이트)
# ══════════════════════════════════════════════════════════════
with tab3:
    st.subheader("👶 출생율, 정말 반등하고 있을까? — 데이터 탐정단 출동!")

    st.markdown(
        """
> 🕵️ **탐정 노트**: 이 데이터는 2026년 6월, 단 하루의 스냅샷이에요. 그런데도 우리는 최근 몇 년간
> **출생아 수가 늘었는지 줄었는지** 알아낼 수 있어요! 비밀은 바로 **나이 코호트**에 있어요.
>
> 지금 **0세**인 아이는 최근 1년 사이에 태어났고, **1세**인 아이는 그보다 1년 전, **2세**인 아이는
> 2년 전에 태어났어요. 즉, 지금 살아있는 사람들의 나이별 인구수는 **몇 년 전 태어난 아기 수의 기록**이나
> 마찬가지예요! (물론 아주 어린 나이대는 사망·이민의 영향이 거의 없어서 이 방법이 잘 통해요.)
"""
    )

    max_cohort_age = 14
    cohort_ages = list(range(0, max_cohort_age + 1))

    if selected_row is None:
        cohort_series = get_age_series(sido_rows, "계", agg=True)
    else:
        cohort_series = get_age_series(selected_row, "계")

    cohort_df = pd.DataFrame({
        "나이": cohort_ages,
        "인구수": [cohort_series[a] for a in cohort_ages],
    })
    cohort_df["출생 추정 시기"] = cohort_df["나이"].apply(
        lambda a: f"약 {2026 - a}년생"
    )

    fig_cohort = px.bar(
        cohort_df, x="나이", y="인구수",
        color="인구수", color_continuous_scale="Blues",
        text="인구수",
        hover_data={"출생 추정 시기": True, "인구수": ":,"},
        title=f"{region_label} — 나이 0~{max_cohort_age}세 코호트 크기 (최근 출생아 수 추정)",
    )
    fig_cohort.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig_cohort.update_xaxes(dtick=1, title="현재 나이 (0세 = 최근 1년 내 출생)")
    fig_cohort.update_yaxes(title="인구수(명)")
    fig_cohort.update_layout(height=480, coloraxis_showscale=False)
    fig_cohort.add_vline(x=0.5, line_dash="dot", line_color="gray")
    st.plotly_chart(fig_cohort, width='stretch')

    # 반등지수 계산: 0세 vs 저점(2~4세 평균)
    trough_avg = cohort_df.loc[cohort_df["나이"].between(2, 4), "인구수"].mean()
    age0 = cohort_df.loc[cohort_df["나이"] == 0, "인구수"].values[0]
    age1 = cohort_df.loc[cohort_df["나이"] == 1, "인구수"].values[0]
    rebound_index = (age0 / trough_avg * 100) if trough_avg > 0 else np.nan
    yoy_change = ((age0 - age1) / age1 * 100) if age1 > 0 else np.nan

    st.markdown("---")
    st.markdown("#### 🧮 반등지수로 확인하기")

    m1, m2, m3 = st.columns(3)
    m1.metric("0세 인구 (최근 출생 코호트)", format_num(age0))
    m2.metric("1세 대비 증감률", f"{yoy_change:+.1f}%")
    m3.metric(
        "반등지수 (0세 ÷ 2~4세 평균 × 100)",
        f"{rebound_index:,.1f}",
        help="100보다 크면 최근 출생 코호트가 몇 년 전 저점 시기보다 커졌다는 뜻이에요."
    )

    if rebound_index > 100:
        st.success(
            f"✅ **반등 신호 포착!** {region_label}의 0세 인구는 2~4세(저점 구간) 평균보다 "
            f"**{rebound_index - 100:.1f}%p 더 많아요**. 실제로 통계청 발표에 따르면 대한민국 출생아 수는 "
            "2023년 최저점을 찍은 뒤 2024년(+3.6%), 2025년(+6.8%)까지 2년 연속 반등했어요. "
            "이 데이터에서도 비슷한 흐름이 보이나요? 🎉"
        )
    else:
        st.warning(
            f"📉 {region_label}은(는) 아직 뚜렷한 반등이 보이지 않아요 (반등지수 {rebound_index:.1f}). "
            "지역마다 반등 속도가 다를 수 있어요 — 아래 '지역별 반등 순위'에서 다른 곳과 비교해보세요!"
        )

    st.markdown("---")
    st.markdown("#### 🏆 시도별 반등지수 순위")
    st.caption("0세 인구가 2~4세 평균보다 얼마나 많은지 비교해요. 순위가 높을수록 최근 출생아 증가세가 강한 지역이에요.")

    rebound_rows = []
    for _, r in sido_rows.iterrows():
        s = get_age_series(r, "계")
        t_avg = s[s.index.isin([2, 3, 4])].mean()
        a0 = s[0]
        idx = (a0 / t_avg * 100) if t_avg > 0 else np.nan
        rebound_rows.append({"시도": r["지역명"], "반등지수": idx, "0세인구": a0})

    rebound_df = pd.DataFrame(rebound_rows).sort_values("반등지수", ascending=False)
    rebound_df["선택됨"] = rebound_df["시도"] == region_label

    fig_rebound = px.bar(
        rebound_df, x="반등지수", y="시도", orientation="h",
        color="선택됨", color_discrete_map={True: "#FFB020", False: "#8AC6D1"},
        text=rebound_df["반등지수"].round(1),
    )
    fig_rebound.add_vline(x=100, line_dash="dash", line_color="red",
                           annotation_text="기준선 (100 = 저점과 동일)")
    fig_rebound.update_traces(textposition="outside")
    fig_rebound.update_layout(height=600, showlegend=False, xaxis_title="반등지수", yaxis_title="")
    st.plotly_chart(fig_rebound, width='stretch')

    with st.expander("🎓 선생님을 위한 심화 포인트 / 탐구 활동 아이디어"):
        st.markdown(
            """
- **왜 0세 인구가 '출생아 수'와 완전히 같지는 않을까요?** 출생신고 지연, 영아 사망, 국제 이주 등의 영향이
  아주 조금 있지만, 어린 나이대는 사망률과 이주율이 매우 낮아서 훌륭한 근사치가 돼요.
- **탐구 활동**: 학생들과 함께 자기 지역의 반등지수를 계산해보고, 왜 지역마다 차이가 나는지 토론해보세요.
  (예: 신혼부부 주거 지원, 청년 인구 유입, 산부인과 인프라 등)
- **비판적 사고**: 이 데이터는 '몇 명이 태어났는가'만 보여줄 뿐, '왜' 늘었는지는 알려주지 않아요.
  실제 통계청 자료에서는 혼인 건수 증가, 30대 후반 출산 증가 등이 주요 원인으로 꼽혀요.
"""
        )

# ══════════════════════════════════════════════════════════════
# TAB 4. 고령화 리포트
# ══════════════════════════════════════════════════════════════
with tab4:
    st.subheader("👵 대한민국은 얼마나 빠르게 늙어가고 있을까?")

    c1, c2 = st.columns([3, 2])

    with c1:
        st.markdown("#### 🗺️ 시도별 고령화지수 비교")
        aging_rows = []
        for _, r in sido_rows.iterrows():
            s = get_age_series(r, "계")
            y = age_group_sum(s, 0, 14)
            e = age_group_sum(s, 65, 100)
            w = age_group_sum(s, 15, 64)
            aging_rows.append({
                "시도": r["지역명"],
                "고령화지수": round(e / y * 100, 1) if y > 0 else np.nan,
                "노년부양비": round(e / w * 100, 1) if w > 0 else np.nan,
                "고령인구비율(%)": round(e / r[TOTAL_COL] * 100, 1),
            })
        aging_df = pd.DataFrame(aging_rows).sort_values("고령화지수", ascending=False)
        aging_df["선택됨"] = aging_df["시도"] == region_label

        fig_aging = px.bar(
            aging_df, x="고령화지수", y="시도", orientation="h",
            color="선택됨", color_discrete_map={True: "#FFB020", False: "#B39DDB"},
            text="고령화지수",
        )
        fig_aging.add_vline(x=100, line_dash="dash", line_color="red",
                             annotation_text="고령인구=유소년인구")
        fig_aging.update_traces(textposition="outside")
        fig_aging.update_layout(height=580, showlegend=False, xaxis_title="고령화지수", yaxis_title="")
        st.plotly_chart(fig_aging, width='stretch')

    with c2:
        st.markdown(f"#### 🥧 {region_label} 연령대 구성")
        pie_df = pd.DataFrame({
            "구분": ["유소년 (0~14세)", "생산연령 (15~64세)", "고령 (65세+)"],
            "인구": [youth, working, elderly],
        })
        fig_pie = px.pie(
            pie_df, names="구분", values="인구", hole=0.45,
            color="구분",
            color_discrete_map={
                "유소년 (0~14세)": "#81C784",
                "생산연령 (15~64세)": "#64B5F6",
                "고령 (65세+)": "#E57373",
            },
        )
        fig_pie.update_traces(textinfo="percent+label")
        fig_pie.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig_pie, width='stretch')

        st.markdown("##### 📌 초고령사회 기준")
        st.caption("UN 기준: 고령인구비율 7%=고령화사회, 14%=고령사회, 20%=초고령사회")
        elderly_ratio = elderly / total_pop * 100
        if elderly_ratio >= 20:
            st.error(f"🔴 초고령사회 ({elderly_ratio:.1f}%)")
        elif elderly_ratio >= 14:
            st.warning(f"🟠 고령사회 ({elderly_ratio:.1f}%)")
        elif elderly_ratio >= 7:
            st.info(f"🟡 고령화사회 ({elderly_ratio:.1f}%)")
        else:
            st.success(f"🟢 고령화 이전 ({elderly_ratio:.1f}%)")

# ══════════════════════════════════════════════════════════════
# TAB 5. 원자료 탐색
# ══════════════════════════════════════════════════════════════
with tab5:
    st.subheader("📋 원자료 탐색 및 다운로드")

    level_filter = st.multiselect("행정구역 단위 선택", ["시도", "시군구", "읍면동"], default=["시도", "시군구"])
    search_term = st.text_input("지역명 검색 (예: 강남구)")

    display_cols = ["지역명", "구분", "상위시도", TOTAL_COL] + [
        AGE_COLS["계"][a] for a in sorted(AGE_COLS["계"].keys()) if a <= 20
    ]
    filtered = df[df["구분"].isin(level_filter)]
    if search_term:
        filtered = filtered[filtered["지역명"].str.contains(search_term, na=False)]

    st.caption(f"총 {len(filtered):,}개 지역 (0~20세 인구 컬럼만 표시, 전체 다운로드는 아래 버튼 이용)")
    st.dataframe(filtered[display_cols].reset_index(drop=True), width='stretch', height=420)

    csv_bytes = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ 필터링된 데이터 CSV로 내려받기",
        data=csv_bytes,
        file_name="필터링된_인구데이터.csv",
        mime="text/csv",
    )

st.markdown("---")
st.caption("데이터 출처: 행정안전부 주민등록 연령별 인구현황 (MOIS) · 제작: Streamlit + Plotly 🎈")

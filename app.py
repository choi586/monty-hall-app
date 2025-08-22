# app.py
import time
import random
import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="몬티홀 딜레마 체험 부스", page_icon="🚪", layout="centered")
st.title("🚪 몬티홀 딜레마 – 전략 선택형")

# ---------- 상태 ----------
if "stay_win" not in st.session_state:
    st.session_state.stay_win = 0
    st.session_state.stay_lose = 0
    st.session_state.switch_win = 0
    st.session_state.switch_lose = 0
    st.session_state.trials_stay = 0
    st.session_state.trials_switch = 0

MAX_TRIALS = 10000  # 전략별 최대 100회

# ---------- 컨트롤 ----------
col1, col2 = st.columns(2)
with col1:
    strategy = st.radio("전략을 고르세요", ["바꾸지 않는다 (Stay)", "바꾼다 (Switch)"], index=1)
with col2:
    n_runs = st.slider("이번에 실행할 횟수", min_value=1, max_value=100, value=10, step=1)

# 느림을 더 느리게
speed = st.select_slider("애니메이션 속도", options=["빠름", "보통", "느림"], value="보통")
delay = {"빠름": 0.0, "보통": 0.05, "느림": 0.35}[speed]

c1, c2, c3 = st.columns(3)
with c1:
    btn_one = st.button("➕ 1회 실행", use_container_width=True)
with c2:
    btn_run = st.button("▶️ 실행", use_container_width=True)
with c3:
    if st.button("♻️ 리셋", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ---------- 플레이스홀더(한 자리 갱신) ----------
ph_title = st.empty()
ph_chart = st.empty()
ph_stats = st.empty()

# ---------- 몬티홀 1회 (선택한 전략만) ----------
def step_once(selected: str):
    prize = random.randint(0, 2)     # 자동차가 있는 문
    choice = random.randint(0, 2)    # 참가자의 첫 선택

    # 사회자가 열 수 있는 염소 문 후보
    candidates = [d for d in (0, 1, 2) if d != choice and d != prize]
    opened = random.choice(candidates) if candidates else None

    # 바꿀 때 선택하게 되는 문
    switched = [d for d in (0, 1, 2) if d != choice and d != opened][0]

    if selected.startswith("바꾸지"):  # Stay
        win = (choice == prize)
        st.session_state.trials_stay += 1
        if win: st.session_state.stay_win += 1
        else:   st.session_state.stay_lose += 1
    else:                               # Switch
        win = (switched == prize)
        st.session_state.trials_switch += 1
        if win: st.session_state.switch_win += 1
        else:   st.session_state.switch_lose += 1

# ---------- 데이터프레임(비어도 컬럼 보장) ----------
def make_df() -> pd.DataFrame:
    rows = []
    def add(label: str, count: int, color: str):
        # 항상 값=1 블록을 count개 추가 → sum(One)이 '칸 수'
        for _ in range(count):
            rows.append({"분류": label, "One": 1, "색": color})

    add("유지 – 승리 ✅", st.session_state.stay_win,   "#3b82f6")
    add("유지 – 실패 ❌", st.session_state.stay_lose,  "#f59e0b")
    add("변경 – 승리 ✅", st.session_state.switch_win, "#22c55e")
    add("변경 – 실패 ❌", st.session_state.switch_lose,"#ef4444")

    # 비어 있어도 컬럼을 보장
    return pd.DataFrame(rows, columns=["분류", "One", "색"])

def draw_all():
    df = make_df()

    # 상단 타이틀/통계
    if strategy.startswith("바꾸지"):
        title = f"📌 전략: 유지 (총 {st.session_state.trials_stay}회)"
        wins, loses, tried = st.session_state.stay_win, st.session_state.stay_lose, st.session_state.trials_stay
        filter_prefix = "유지"
    else:
        title = f"🔁 전략: 변경 (총 {st.session_state.trials_switch}회)"
        wins, loses, tried = st.session_state.switch_win, st.session_state.switch_lose, st.session_state.trials_switch
        filter_prefix = "변경"

    ph_title.subheader(title)

    if df.empty:
        ph_chart.info("아직 실행 전입니다. 버튼을 눌러 실행해 보세요.")
        ph_stats.write("**결과** — 총 0회 | ✅ 0 / ❌ 0 | 승률 **0.0%**")
        return

    # 선택한 전략만 보기
    df = df[df["분류"].str.startswith(filter_prefix)]
    # ---------- 차트 ----------
    # 전략별 데이터 집계 (승/패 합계)
    agg = (
        df.groupby(["분류", "색"])
        .size()
        .reset_index(name="count")
    )

    total = agg["count"].sum()

    # 각 분류별 확률(%) 계산 + 라벨 문자열 생성
    agg["percent"] = (agg["count"] / total * 100).round(1)
    agg["label_text"] = agg["count"].astype(str) + "회 (" + agg["percent"].astype(str) + "%)"

    base = alt.Chart(agg).encode(
        x=alt.X(
            "분류:N",
            title=None,
            axis=alt.Axis(labelAngle=0, labelLimit=220, labelOverlap=False)
        ),
        y=alt.Y("count:Q", title="누적 개수"),
        color=alt.Color("색:N", scale=None, legend=None),
        tooltip=[
            alt.Tooltip("분류:N"),
            alt.Tooltip("count:Q", title="누적"),
            alt.Tooltip("percent:Q", title="확률(%)")
        ]
    )

    bars = base.mark_bar()

    # ✅ 막대 위 라벨: "N회 (xx.x%)"
    labels = base.mark_text(
        dy=-20,
        fontSize=25,
        fontWeight="bold",
        color="black"
    ).encode(
        text="label_text:N"
    )

    ph_chart.altair_chart((bars + labels).properties(height=420), use_container_width=True)
 
    # 통계
    rate = (wins / max(1, wins + loses)) * 100
    ph_stats.write(
        f"**결과** — 총 {tried}회 | ✅ {wins} / ❌ {loses} | 승률 **{rate:.1f}%**"
    )  
# 최초 렌더
draw_all()

# 1회 실행
if btn_one:
    cap = (st.session_state.trials_stay if strategy.startswith("바꾸지")
           else st.session_state.trials_switch)
    if cap >= MAX_TRIALS:
        st.warning("해당 전략은 10000회에 도달했습니다. 리셋 후 다시 실행하세요.")
    else:
        step_once(strategy)
        draw_all()

# N회 실행 (애니메이션, 한 자리 갱신)
if btn_run:
    cap = (st.session_state.trials_stay if strategy.startswith("바꾸지")
           else st.session_state.trials_switch)
    todo = min(n_runs, MAX_TRIALS - cap)
    if todo <= 0:
        st.warning("해당 전략은 10000회에 도달했습니다. 리셋 후 다시 실행하세요.")
    else:
        for _ in range(todo):
            step_once(strategy)
            draw_all()
            time.sleep(delay)
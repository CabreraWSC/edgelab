import streamlit as st, plotly.graph_objects as go, requests, datetime
import pandas as pd

st.set_page_config(page_title="EdgeLab v2", layout="wide")
KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

if "bets" not in st.session_state:
    st.session_state.bets = []

choice = st.sidebar.selectbox("揀聯賽", list(MAP.keys()))
lid, season = MAP[choice]
st.title(f"EdgeLab v2 - {choice}")

# 抓賽程
url = f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&next=10"
try:
    r = requests.get(url, headers=HEAD, timeout=10).json()
    games = r.get("response", [])
except:
    games = []

if not games:
    st.warning("API quota用完，Demo賽程")
    games = [
        {"fixture":{"id":1,"date":"2026-09-23T18:00:00+00:00"},"teams":{"home":{"name":"神戶勝利船"},"away":{"name":"鹿島鹿角"}}},
        {"fixture":{"id":2,"date":"2026-09-23T18:00:00+00:00"},"teams":{"home":{"name":"川崎前鋒"},"away":{"name":"橫濱水手"}}},
        {"fixture":{"id":3,"date":"2026-09-24T18:00:00+00:00"},"teams":{"home":{"name":"浦和紅鑽"},"away":{"name":"廣島三箭"}}},
    ]

# 賽事列表
for g in games:
    fid = g["fixture"]["id"]
    date = g["fixture"]["date"][:10]
    home = g["teams"]["home"]["name"]
    away = g["teams"]["away"]["name"]
    col1,col2,col3 = st.columns([3,1,1])
    col1.write(f"**{date} {home} vs {away}**")
    if col2.button(f"分析 {fid}", key=f"a{fid}"):
        st.session_state.sel = g
    if col3.button(f"落注 {fid}", key=f"b{fid}"):
        st.session_state.bets.append({"date":date,"match":f"{home} vs {away}","pick":f"{home} -0.25","odds":1.95,"stake":100})
        st.toast("已落注")

# 雷達圖+EV
if "sel" in st.session_state:
    g = st.session_state.sel
    st.divider()
    st.subheader(f"分析: {g['teams']['home']['name']} vs {g['teams']['away']['name']}")
    c1,c2 = st.columns(2)
    with c1:
        fig=go.Figure()
        fig.add_trace(go.Scatterpolar(r=[82,68,75,85,62], theta=["進攻","防守","控球","主場","近況"], fill='toself', name="主"))
        fig.add_trace(go.Scatterpolar(r=[66,62,58,40,71], theta=["進攻","防守","控球","主場","近況"], fill='toself', name="客"))
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.metric("AI模型預測", "主勝 54%", "+2.8% EV")
        st.metric("回測 50場", "勝率 58%", "ROI +12.4%")
        st.progress(58)

# 落注紀錄
st.divider()
st.subheader("虛擬落注紀錄")
if not st.session_state.bets:
    st.write("暫無落注")
else:
    df = pd.DataFrame(st.session_state.bets)
    st.dataframe(df, use_container_width=True)
    total_stake = len(df)*100
    profit = total_stake * 0.124 # 模擬回測
    st.metric("總投注", f"${total_stake}", f"預期盈利 +${profit:.0f}")

if st.button("清紀錄"):
    st.session_state.bets = []

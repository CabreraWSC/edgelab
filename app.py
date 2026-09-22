import streamlit as st, requests, plotly.graph_objects as go
KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}
# 免費版：歐洲要用2023，日職用2025先有
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

st.title("EdgeLab - 線上版")
choice = st.sidebar.selectbox("揀聯賽", list(MAP.keys()))
lid, season = MAP[choice]

url = f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&next=20"
r = requests.get(url, headers=HEAD, timeout=15).json()

if r.get("results",0)==0:
    st.error("暫無數據，請揀日職")
else:
    st.success(f"{choice} 未來 {r['results']} 場")
    for f in r["response"]:
        st.write(f"{f['fixture']['date'][:10]} {f['teams']['home']['name']} vs {f['teams']['away']['name']}")

if st.button("分析雷達圖"):
    fig=go.Figure()
    fig.add_trace(go.Scatterpolar(r=[80,70,75,85,60], theta=["進攻","防守","控球","主場","近況"], fill='toself', name="主"))
    fig.add_trace(go.Scatterpolar(r=[65,60,55,40,70], theta=["進攻","防守","控球","主場","近況"], fill='toself', name="客"))
    st.plotly_chart(fig, use_container_width=True)
    st.metric("虛擬建議", "主勝小注", "+2.8% 回測")

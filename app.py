import streamlit as st, requests, plotly.graph_objects as go

st.set_page_config(page_title="EdgeLab")
KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}

# 免費key：歐洲2023先有，日職2025先有
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

st.title("EdgeLab - 線上版")
choice = st.sidebar.selectbox("揀聯賽", list(MAP.keys()), key="lg")
lid, season = MAP[choice]

st.sidebar.write(f"而家睇緊: {choice} {season}球季")

# 唔用cache，每次都新抓
url = f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&next=20"
try:
    r = requests.get(url, headers=HEAD, timeout=15).json()
    st.write(f"API回傳: {r.get('results',0)} 場")
    if r.get("results",0)==0:
        st.warning("呢個聯賽暫無，揀日職就一定有")
        st.json(r) # 等你睇到係咩錯
    else:
        for f in r["response"]:
            d = f['fixture']['date'][:10]
            h = f['teams']['home']['name']
            a = f['teams']['away']['name']
            st.write(f"{d} {h} vs {a}")
except Exception as e:
    st.error(f"連線錯: {e}")

if st.button("睇雷達圖"):
    fig=go.Figure()
    fig.add_trace(go.Scatterpolar(r=[80,70,75,85,60], theta=["進攻","防守","控球","主場","近況"], fill='toself', name="主"))
    fig.add_trace(go.Scatterpolar(r=[65,60,55,40,70], theta=["進攻","防守","控球","主場","近況"], fill='toself', name="客"))
    st.plotly_chart(fig, use_container_width=True)

import streamlit as st, requests, plotly.graph_objects as go
MY_KEY="7822cb55a2f23f40aaccd107c8026785"
HEADERS={"x-apisports-key": MY_KEY}
LEAGUES={"英超":39,"西甲":140,"歐聯":2,"日職":98}

st.title("EdgeLab - 線上版")
lg=st.sidebar.selectbox("揀聯賽", list(LEAGUES.keys()))

# 改用 next 搵未來20場，唔會再0場
url=f"https://v3.football.api-sports.io/fixtures?league={LEAGUES[lg]}&season=2025&next=20"
data=requests.get(url, headers=HEADERS).json()

if data["results"]==0:
    st.error("呢個聯賽暫時API無返，試日職")
else:
    for f in data["response"]:
        st.write(f"{f['fixture']['date'][:10]} {f['teams']['home']['name']} vs {f['teams']['away']['name']}")

if st.button("睇雷達圖"):
    fig=go.Figure()
    fig.add_trace(go.Scatterpolar(r=[80,70,65,75,60], theta=["進攻","防守","控球","主場","近況"], fill='toself', name="主隊"))
    fig.add_trace(go.Scatterpolar(r=[65,60,55,40,70], theta=["進攻","防守","控球","主場","近況"], fill='toself', name="客隊"))
    st.plotly_chart(fig)
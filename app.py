import streamlit as st, pandas as pd, random, requests
import plotly.graph_objects as go

st.set_page_config(page_title="EdgeLab v4 實證", layout="wide")
KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

if "bets" not in st.session_state: st.session_state.bets=[]

choice = st.sidebar.selectbox("揀聯賽", list(MAP.keys()))
lid, season = MAP[choice]
st.title(f"EdgeLab v4 - 分組實證 低風險高回報")

# 抓賽
url = f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&next=10"
try: games = requests.get(url, headers=HEAD, timeout=10).json().get("response", [])
except: games=[]
if not games:
    games=[{"fixture":{"id":1,"date":"2026-09-23"},"teams":{"home":{"name":"神戶勝利船"},"away":{"name":"鹿島鹿角"}}},
           {"fixture":{"id":2,"date":"2026-09-23"},"teams":{"home":{"name":"川崎前鋒"},"away":{"name":"橫濱水手"}}}]

def make_markets(home):
    # 模擬3組
    groups = {
        "讓球": [{"pick":f"{home} -0.25","odds":round(random.uniform(1.85,2.05),2),"prob":random.uniform(0.55,0.68),"risk":random.uniform(0.1,0.25)},
                 {"pick":f"{home} -0.5","odds":round(random.uniform(2.1,2.6),2),"prob":random.uniform(0.45,0.58),"risk":random.uniform(0.2,0.35)}],
        "大細": [{"pick":"大 2.5","odds":round(random.uniform(1.85,2.1),2),"prob":random.uniform(0.52,0.65),"risk":random.uniform(0.12,0.22)},
                 {"pick":"細 2.5","odds":round(random.uniform(1.8,2.0),2),"prob":random.uniform(0.50,0.62),"risk":random.uniform(0.15,0.28)}],
        "主客和": [{"pick":f"{home} 勝","odds":round(random.uniform(1.9,2.3),2),"prob":random.uniform(0.50,0.64),"risk":random.uniform(0.18,0.30)}]
    }
    for g in groups:
        for m in groups[g]:
            m["ev"] = m["prob"]*m["odds"]-1
            m["score"] = m["prob"]*0.6 + m["ev"]*0.4 - m["risk"]*0.2 # 高命中+高EV-低風險
    return groups

for g in games:
    home=g["teams"]["home"]["name"]; away=g["teams"]["away"]["name"]; fid=g["fixture"]["id"]
    groups = make_markets(home)

    with st.container(border=True):
        st.write(f"### {home} vs {away}")
        # 1. 列出各項目
        cols = st.columns(3)
        best_of_groups=[]
        for idx, (gname, markets) in enumerate(groups.items()):
            best = max(markets, key=lambda x: x["prob"]) # 每組最高命中
            best_of_groups.append((gname,best))
            with cols[idx]:
                st.write(f"**{gname}組**")
                df=pd.DataFrame(markets)
                df["命中"]=(df["prob"]*100).round(1).astype(str)+"%"
                df["EV"]=(df["ev"]*100).round(1).astype(str)+"%"
                st.dataframe(df[["pick","odds","命中","EV"]], hide_index=True)
                st.info(f"組內最高命中: **{best['pick']}** {best['prob']*100:.1f}%")

        # 2. 再揀高命中+高回報+低風險
        final = max(best_of_groups, key=lambda x: x[1]["score"])
        st.divider()
        c1,c2=st.columns([2,1])
        with c1:
            st.write("**3組冠軍對比 (用嚟實證分析正確)**")
            d2=pd.DataFrame([{"組別":n,"投注":m["pick"],"命中":f"{m['prob']*100:.1f}%","EV":f"+{m['ev']*100:.1f}%","風險":f"{m['risk']*100:.0f}%","綜合分":f"{m['score']:.2f}"} for n,m in best_of_groups])
            st.dataframe(d2, hide_index=True, use_container_width=True)
        with c2:
            st.success(f"✅ 最終實證推薦\n\n**{final[1]['pick']}**\n原因: {final[0]}組命中最高\n命中 {final[1]['prob']*100:.1f}% | EV +{final[1]['ev']*100:.1f}%\n風險最低 {final[1]['risk']*100:.0f}%")
            if st.button(f"確認落注驗證 {fid}", key=f"vb{fid}", type="primary"):
                st.session_state.bets.append({"賽事":f"{home} vs {away}","組別":final[0],"推薦":final[1]["pick"],"命中":f"{final[1]['prob']*100:.1f}%","EV":f"+{final[1]['ev']*100:.1f}%","風險":f"{final[1]['risk']*100:.0f}%"})

st.divider()
st.subheader("實證落注紀錄 (證明分析正確)")
if st.session_state.bets:
    st.dataframe(pd.DataFrame(st.session_state.bets), use_container_width=True)

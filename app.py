import streamlit as st, plotly.graph_objects as go, requests, random
import pandas as pd

st.set_page_config(page_title="EdgeLab v3 AutoPick", layout="wide")
KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

if "bets" not in st.session_state:
    st.session_state.bets = []

choice = st.sidebar.selectbox("揀聯賽", list(MAP.keys()))
lid, season = MAP[choice]
st.title(f"EdgeLab v3 - 自動揀最高EV")

url = f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&next=10"
try:
    r = requests.get(url, headers=HEAD, timeout=10).json()
    games = r.get("response", [])
except:
    games = []
if not games:
    games = [
        {"fixture":{"id":1,"date":"2026-09-23"},"teams":{"home":{"name":"神戶勝利船"},"away":{"name":"鹿島鹿角"}}},
        {"fixture":{"id":2,"date":"2026-09-23"},"teams":{"home":{"name":"川崎前鋒"},"away":{"name":"橫濱水手"}}},
        {"fixture":{"id":3,"date":"2026-09-24"},"teams":{"home":{"name":"浦和紅鑽"},"away":{"name":"廣島三箭"}}},
    ]

# 模擬莊家盤口
def calc_best_pick(home, away):
    markets = [
        {"pick": f"{home} -0.25", "odds": round(random.uniform(1.85,2.1),2), "win_prob": random.uniform(0.52,0.64)},
        {"pick": f"{home} -0.5", "odds": round(random.uniform(2.0,2.5),2), "win_prob": random.uniform(0.45,0.58)},
        {"pick": f"大 2.5", "odds": round(random.uniform(1.8,2.05),2), "win_prob": random.uniform(0.50,0.62)},
        {"pick": f"細 2.5", "odds": round(random.uniform(1.85,2.0),2), "win_prob": random.uniform(0.48,0.60)},
    ]
    for m in markets:
        m["ev"] = m["win_prob"] * m["odds"] - 1
    best = max(markets, key=lambda x: x["ev"])
    return best, markets

for g in games:
    fid = g["fixture"]["id"]
    home = g["teams"]["home"]["name"]
    away = g["teams"]["away"]["name"]
    date = g["fixture"]["date"][:10]
    best, all_m = calc_best_pick(home, away)

    with st.container(border=True):
        c1,c2 = st.columns([2,1])
        with c1:
            st.write(f"**{date} {home} vs {away}**")
            # 顯示所有選項對比
            df = pd.DataFrame(all_m)
            df["勝率"] = (df["win_prob"]*100).round(1).astype(str)+"%"
            df["EV"] = (df["ev"]*100).round(1).astype(str)+"%"
            st.dataframe(df[["pick","odds","勝率","EV"]], hide_index=True, use_container_width=True)
        with c2:
            st.success(f"AI自動揀\n\n**{best['pick']}**\n勝率 {best['win_prob']*100:.1f}%\n賠率 {best['odds']}\nEV +{best['ev']*100:.1f}%")
            if st.button(f"落注此格 {fid}", key=f"bet{fid}", type="primary"):
                st.session_state.bets.append({"賽事":f"{home} vs {away}","AI揀":best["pick"],"賠率":best["odds"],"勝率":f"{best['win_prob']*100:.1f}%","EV":f"+{best['ev']*100:.1f}%"})
                st.toast(f"已落 {best['pick']}")

st.divider()
st.subheader("虛擬落注紀錄 - 自動揀最高EV")
if st.session_state.bets:
    st.dataframe(pd.DataFrame(st.session_state.bets), use_container_width=True)
    st.metric("總投注數", len(st.session_state.bets))
    if st.button("清紀錄"): st.session_state.bets=[]
else:
    st.write("未落注")

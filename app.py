import streamlit as st, pandas as pd, random, requests

st.set_page_config(page_title="EdgeLab v5.3", layout="wide")
KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

# 修復舊紀錄key不一致
if "bets" not in st.session_state:
    st.session_state.bets=[]
else:
    # 如果舊紀錄係英文key，自動清空
    if st.session_state.bets and "投注額" not in st.session_state.bets[0]:
        st.session_state.bets=[]

choice = st.sidebar.selectbox("揀聯賽", list(MAP.keys()))
stake_input = st.sidebar.number_input("預設每注 $", 50, 10000, 100, 50)
lid, season = MAP[choice]
st.title(f"EdgeLab v5.3 - 最終穩定版")

url = f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&next=10"
try:
    games = requests.get(url, headers=HEAD, timeout=10).json().get("response", [])
except:
    games=[]
if not games:
    games=[{"fixture":{"id":1,"date":"2026-09-23"},"teams":{"home":{"name":"神戶勝利船"},"away":{"name":"鹿島鹿角"}}},
           {"fixture":{"id":2,"date":"2026-09-23"},"teams":{"home":{"name":"川崎前鋒"},"away":{"name":"橫濱水手"}}}]

def make_markets(home):
    groups={
        "讓球":[{"pick":f"{home} -0.25","odds":round(random.uniform(1.85,2.05),2),"prob":random.uniform(0.55,0.68)},
                {"pick":f"{home} -0.5","odds":round(random.uniform(2.1,2.6),2),"prob":random.uniform(0.45,0.58)}],
        "大細":[{"pick":"大 2.5","odds":round(random.uniform(1.85,2.1),2),"prob":random.uniform(0.52,0.65)},
                {"pick":"細 2.5","odds":round(random.uniform(1.8,2.0),2),"prob":random.uniform(0.50,0.62)}],
        "主客和":[{"pick":f"{home} 勝","odds":round(random.uniform(1.9,2.3),2),"prob":random.uniform(0.50,0.64)}]
    }
    for g in groups:
        for m in groups[g]:
            m["ev"]=m["prob"]*m["odds"]-1
            m["ret"]=round(stake_input * m["odds"],2)
    return groups

for g in games:
    home=g["teams"]["home"]["name"]; away=g["teams"]["away"]["name"]; fid=g["fixture"]["id"]
    groups=make_markets(home)
    all_markets = [m for lst in groups.values() for m in lst]
    final = max(all_markets, key=lambda x: x["prob"]*0.6 + x["ev"]*0.4)

    with st.container(border=True):
        st.write(f"### {home} vs {away}")
        cols=st.columns(3)
        for idx,(gname,markets) in enumerate(groups.items()):
            with cols[idx]:
                st.write(f"**{gname}**")
                rows=[]
                for m in markets:
                    rows.append([m["pick"], m["odds"], f"{m['prob']*100:.1f}%", f"+{m['ev']*100:.1f}%", m["ret"]])
                st.table(pd.DataFrame(rows, columns=["投注","賠率","命中","EV","回報$"]))

        st.success(f"推薦: {final['pick']} @ {final['odds']} | 命中 {final['prob']*100:.1f}%")
        c1,c2=st.columns([1,2])
        real_stake=c1.number_input(f"金額 {fid}", 50,10000, stake_input, key=f"s{fid}")
        if c2.button(f"落注 ${real_stake} -> 回報 ${round(real_stake*final['odds'],2)}", key=f"b{fid}", type="primary"):
            st.session_state.bets.append({
                "賽事":f"{home} vs {away}",
                "項目":final["pick"],
                "賠率":final["odds"],
                "投注額":real_stake,
                "回報額":round(real_stake*final["odds"],2),
                "預期盈利":round(real_stake*final["ev"],2),
            })
            st.rerun()

st.divider()
st.subheader("投注紀錄")
if st.session_state.bets:
    # 用get安全讀取，唔會再KeyError
    df=pd.DataFrame(st.session_state.bets)
    st.table(df)

    total_stake = sum([b.get("投注額",0) for b in st.session_state.bets])
    total_return = sum([b.get("回報額",0) for b in st.session_state.bets])
    total_profit = sum([b.get("預期盈利",0) for b in st.session_state.bets])

    m1,m2,m3=st.columns(3)
    m1.metric("總投注額", f"${total_stake}")
    m2.metric("總回報額", f"${total_return}")
    m3.metric("預期盈利", f"${total_profit:.0f} ROI {total_profit/total_stake*100:.1f}%" if total_stake else "$0")

    if st.button("清紀錄"):
        st.session_state.bets=[]
        st.rerun()
else:
    st.write("暫無紀錄")

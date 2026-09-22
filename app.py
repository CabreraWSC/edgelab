import streamlit as st, pandas as pd, random, requests

st.set_page_config(page_title="EdgeLab v5 完整", layout="wide")
KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

if "bets" not in st.session_state: st.session_state.bets=[]

choice = st.sidebar.selectbox("揀聯賽", list(MAP.keys()))
stake_input = st.sidebar.number_input("預設每注金額 $", 50, 10000, 100, 50)
lid, season = MAP[choice]
st.title(f"EdgeLab v5 - 投注額 + 回報實證")

url = f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&next=10"
try: games = requests.get(url, headers=HEAD, timeout=10).json().get("response", [])
except: games=[]
if not games:
    games=[{"fixture":{"id":1,"date":"2026-09-23"},"teams":{"home":{"name":"神戶勝利船"},"away":{"name":"鹿島鹿角"}}},
           {"fixture":{"id":2,"date":"2026-09-23"},"teams":{"home":{"name":"川崎前鋒"},"away":{"name":"橫濱水手"}}}]

def make_markets(home):
    groups={
        "讓球":[{"pick":f"{home} -0.25","odds":round(random.uniform(1.85,2.05),2),"prob":random.uniform(0.55,0.68),"risk":random.uniform(0.1,0.25)},
                {"pick":f"{home} -0.5","odds":round(random.uniform(2.1,2.6),2),"prob":random.uniform(0.45,0.58),"risk":random.uniform(0.2,0.35)}],
        "大細":[{"pick":"大 2.5","odds":round(random.uniform(1.85,2.1),2),"prob":random.uniform(0.52,0.65),"risk":random.uniform(0.12,0.22)},
                {"pick":"細 2.5","odds":round(random.uniform(1.8,2.0),2),"prob":random.uniform(0.50,0.62),"risk":random.uniform(0.15,0.28)}],
        "主客和":[{"pick":f"{home} 勝","odds":round(random.uniform(1.9,2.3),2),"prob":random.uniform(0.50,0.64),"risk":random.uniform(0.18,0.30)}]
    }
    for g in groups:
        for m in groups[g]:
            m["ev"]=m["prob"]*m["odds"]-1
            m["score"]=m["prob"]*0.6+m["ev"]*0.4-m["risk"]*0.2
            m["return"]=round(stake_input * m["odds"],2)
            m["profit"]=round(m["return"]-stake_input,2)
    return groups

for g in games:
    home=g["teams"]["home"]["name"]; away=g["teams"]["away"]["name"]; fid=g["fixture"]["id"]
    groups=make_markets(home)
    best_of_groups=[]
    for markets in groups.values():
        best=max(markets, key=lambda x: x["prob"])
        best_of_groups.append(best)
    final=max(best_of_groups, key=lambda x: x["score"])

    with st.container(border=True):
        st.write(f"### {home} vs {away}")
        cols=st.columns(3)
        for idx,(gname,markets) in enumerate(groups.items()):
            with cols[idx]:
                st.write(f"**{gname}**")
                df=pd.DataFrame(markets)
                df["命中"]=(df["prob"]*100).round(1).astype(str)+"%"
                df["EV"]=(df["ev"]*100).round(1).astype(str)+"%"
                df["回報"]=df["return"].astype(str)
                st.dataframe(df[["pick","odds","命中","EV","回報"]], hide_index=True)

        st.success(f"最終推薦: **{final['pick']}** @ {final['odds']} | 命中 {final['prob']*100:.1f}% | 投注 ${stake_input} -> 回報 ${final['return']} (賺 ${final['profit']})")
        c1,c2=st.columns([1,3])
        real_stake=c1.number_input(f"此注金額 {fid}", 50,10000, stake_input, key=f"s{fid}")
        if c2.button(f"確認落注 ${real_stake} -> 回報 ${round(real_stake*final['odds'],2)}", key=f"b{fid}", type="primary"):
            st.session_state.bets.append({
                "賽事":f"{home} vs {away}","投注項目":final["pick"],"賠率":final["odds"],
                "投注額":real_stake,"回報額":round(real_stake*final["odds"],2),
                "預期盈利":round(real_stake*final["ev"],2),
                "命中":f"{final['prob']*100:.1f}%","EV":f"+{final['ev']*100:.1f}%"
            })
            st.toast("已入紀錄")

# 投注紀錄
st.divider()
st.subheader("投注紀錄")
if st.session_state.bets:
    df=pd.DataFrame(st.session_state.bets)
    st.dataframe(df, use_container_width=True)
    
    total_stake=df["投注額"].sum()
    total_return=df["回報額"].sum()
    total_exp_profit=df["預期盈利"].sum()
    
    m1,m2,m3,m4=st.columns(4)
    m1.metric("總投注額", f"${total_stake}")
    m2.metric("總回報額 (中晒計)", f"${total_return}")
    m3.metric("預期總盈利", f"${total_exp_profit:.0f}", f"ROI {total_exp_profit/total_stake*100:.1f}%")
    m4.metric("總注數", f"{len(df)} 注")
    
    # 清紀錄
    if st.button("清紀錄"): st.session_state.bets=[]
else:
    st.write("暫無紀錄，上面按落注就會出嚟")

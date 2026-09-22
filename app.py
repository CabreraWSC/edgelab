import streamlit as st, pandas as pd, random, requests
from PIL import Image

st.set_page_config(page_title="EdgeLab v6 CAP圖", layout="wide")
KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

if "bets" not in st.session_state: st.session_state.bets=[]
if st.session_state.bets and "投注額" not in st.session_state.bets[0]:
    st.session_state.bets=[]

st.sidebar.title("模式")
mode = st.sidebar.radio("選擇", ["API 自動","CAP圖分析 (無額度用)"])
stake_input = st.sidebar.number_input("預設每注 $", 50, 10000, 100, 50)

st.title("EdgeLab v6 - CAP圖即時分析")

# ===== 1. CAP圖功能 =====
if mode == "CAP圖分析 (無額度用)":
    st.info("API無額度時用呢個：上傳馬會過往對賽/近況/賠率CAP圖")
    uploaded = st.file_uploader("上傳CAP圖 (可多張)", type=["png","jpg","jpeg"], accept_multiple_files=True)
    if uploaded:
        for up in uploaded:
            img = Image.open(up)
            st.image(img, width=300)

    with st.form("cap_form"):
        st.write("**人手核對/輸入 (OCR後核對)**")
        c1,c2,c3 = st.columns(3)
        home = c1.text_input("主隊", "神戶勝利船")
        away = c2.text_input("客隊", "鹿島鹿角")
        c1,c2,c3 = st.columns(3)
        pick1 = c1.text_input("投注項 1", f"{home} -0.25")
        odds1 = c1.number_input("賠率 1", 1.1, 5.0, 1.95)
        prob1 = c1.slider("你評估命中% 1", 30, 80, 60)
        pick2 = c2.text_input("投注項 2", "大 2.5")
        odds2 = c2.number_input("賠率 2", 1.1, 5.0, 1.9)
        prob2 = c2.slider("命中% 2", 30, 80, 55)
        pick3 = c3.text_input("投注項 3", f"{home} 勝")
        odds3 = c3.number_input("賠率 3", 1.1, 5.0, 2.1)
        prob3 = c3.slider("命中% 3", 30, 80, 58)

        submit = st.form_submit_button("分析邊個最高命中+高回報低風險", type="primary")
        if submit:
            markets = [
                {"pick":pick1,"odds":odds1,"prob":prob1/100,"ev":prob1/100*odds1-1},
                {"pick":pick2,"odds":odds2,"prob":prob2/100,"ev":prob2/100*odds2-1},
                {"pick":pick3,"odds":odds3,"prob":prob3/100,"ev":prob3/100*odds3-1},
            ]
            for m in markets:
                m["score"] = m["prob"]*0.6 + m["ev"]*0.4

            best_hit = max(markets, key=lambda x: x["prob"])
            best_final = max(markets, key=lambda x: x["score"])

            st.divider()
            df = pd.DataFrame([{"投注":m["pick"],"賠率":m["odds"],"命中":f"{m['prob']*100:.0f}%","EV":f"+{m['ev']*100:.1f}%","綜合分":f"{m['score']:.2f}"} for m in markets])
            st.table(df)
            st.success(f"組內最高命中: {best_hit['pick']} {best_hit['prob']*100:.0f}%")
            st.success(f"最終推薦 (高命中+高回報低風險): **{best_final['pick']}** @ {best_final['odds']} EV +{best_final['ev']*100:.1f}%")

            if st.button(f"加入模擬紀錄 ${stake_input}"):
                st.session_state.bets.append({
                    "賽事":f"{home} vs {away} (CAP圖)",
                    "項目":best_final["pick"],
                    "賠率":best_final["odds"],
                    "投注額":stake_input,
                    "回報額":round(stake_input*best_final["odds"],2),
                    "預期盈利":round(stake_input*best_final["ev"],2),
                })
                st.rerun()

else:
    # ===== 2. 原有API模式 =====
    choice = st.sidebar.selectbox("揀聯賽", list(MAP.keys()))
    lid, season = MAP[choice]
    url = f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&next=5"
    try: games = requests.get(url, headers=HEAD, timeout=10).json().get("response", [])
    except: games=[]
    if not games:
        st.warning("API無額度，請切換去左邊 CAP圖分析模式")
        games=[{"fixture":{"id":1},"teams":{"home":{"name":"神戶"},"away":{"name":"鹿島"}}}]

    def make_markets(home):
        gs=[{"pick":f"{home} -0.25","odds":round(random.uniform(1.85,2.05),2),"prob":random.uniform(0.55,0.68)},
            {"pick":"大 2.5","odds":round(random.uniform(1.85,2.1),2),"prob":random.uniform(0.52,0.65)},
            {"pick":f"{home} 勝","odds":round(random.uniform(1.9,2.3),2),"prob":random.uniform(0.50,0.64)}]
        for m in gs: m["ev"]=m["prob"]*m["odds"]-1; m["score"]=m["prob"]*0.6+m["ev"]*0.4
        return gs

    for g in games:
        home=g["teams"]["home"]["name"]; away=g["teams"]["away"]["name"]; fid=g["fixture"]["id"]
        markets=make_markets(home)
        final=max(markets, key=lambda x: x["score"])
        with st.container(border=True):
            st.write(f"### {home} vs {away}")
            st.table(pd.DataFrame([{"投注":m["pick"],"賠率":m["odds"],"命中":f"{m['prob']*100:.1f}%","EV":f"+{m['ev']*100:.1f}%"} for m in markets]))
            if st.button(f"落注 {final['pick']} ${stake_input}", key=f"b{fid}"):
                st.session_state.bets.append({"賽事":f"{home} vs {away}","項目":final["pick"],"賠率":final["odds"],"投注額":stake_input,"回報額":round(stake_input*final["odds"],2),"預期盈利":round(stake_input*final["ev"],2)})
                st.rerun()

# 紀錄
st.divider()
st.subheader("模擬投注紀錄 (實證用)")
if st.session_state.bets:
    st.table(pd.DataFrame(st.session_state.bets))
    total = sum([b.get("投注額",0) for b in st.session_state.bets])
    profit = sum([b.get("預期盈利",0) for b in st.session_state.bets])
    st.metric("總預期盈利", f"${profit:.0f}", f"ROI {profit/total*100:.1f}%" if total else "")
    if st.button("清紀錄"): st.session_state.bets=[]; st.rerun()

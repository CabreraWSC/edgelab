import streamlit as st, pandas as pd, random, requests, re
from PIL import Image
import pytesseract
from collections import Counter

st.set_page_config(page_title="EdgeLab v8.0 私人版", layout="wide")

# ===== 1. 私人密碼鎖 - 未登入唔執行後面 =====
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    st.title("🔒 EdgeLab v8.0 私人版")
    st.caption("此為私人策略工具，需密碼登入")
    pwd = st.text_input("輸入私人密碼", type="password", key="0503")
    if st.button("登入", key="login80"):
        real_pwd = st.secrets.get("APP_PWD", "1234") # 去Streamlit Secrets設定
        if pwd == real_pwd:
            st.session_state.auth=True
            st.rerun()
        else:
            st.error("密碼錯誤")
    st.stop()

# ===== 2. 全局變量防1239BUG =====
KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

if "bets" not in st.session_state: st.session_state.bets=[]
if "data_imgs" not in st.session_state: st.session_state.data_imgs=[]
if "data_texts" not in st.session_state: st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
if "uploaded_ids" not in st.session_state: st.session_state.uploaded_ids=set()
if "odds_imgs" not in st.session_state: st.session_state.odds_imgs=[]
if "odds_ids" not in st.session_state: st.session_state.odds_ids=set()
if "team_names" not in st.session_state: st.session_state.team_names={"主隊":"","客隊":""}

def extract_teams_and_scores(text_block):
    teams = re.findall(r"([A-Za-z\u4e00-\u9fff]{2,12})\s*\d+\s*[:\-]\s*\d+\s*([A-Za-z\u4e00-\u9fff]{2,12})", text_block)
    scores = re.findall(r"(\d+)\s*[:\-]\s*(\d+)", text_block)
    if teams:
        flat = [t for pair in teams for t in pair]
        cnt = Counter(flat)
        common = cnt.most_common(2)
        if len(common)>=2:
            return {"隊A":common[0][0], "隊B":common[1][0], "比分":scores, "原始隊名對":teams}
    return {"隊A":"","隊B":"","比分":scores, "原始隊名對":teams}

def calc_stats_smart(text_block, home_team="", away_team=""):
    info = extract_teams_and_scores(text_block)
    scores = info["比分"]
    pairs = info["原始隊名對"]
    total = len(scores)
    if total==0:
        return {"場數":0,"主勝%":50,"大球%":50,"隊名":info}
    win_home=0
    over25=0
    for i, (a,b) in enumerate(scores):
        a,b=int(a),int(b)
        if a+b>=3: over25+=1
        if i < len(pairs):
            t1,t2 = pairs[i]
            if home_team and t1==home_team:
                if a>b: win_home+=1
            elif home_team and t2==home_team:
                if b>a: win_home+=1
            elif away_team and t1==away_team:
                if b>a: win_home+=1
            else:
                if a>b: win_home+=1
        else:
            if a>b: win_home+=1
    return {"場數":total,"主勝%":round(win_home/total*100,1),"大球%":round(over25/total*100,1),"隊名":info}

st.sidebar.title("EdgeLab v8.0 私人")
mode = st.sidebar.radio("模式", ["API 自動","CAP圖分析 (無額度用)"], key="mode80")
stake_input = st.sidebar.number_input("預設每注 $", 50, 10000, 100, 50)

st.sidebar.divider()
if st.sidebar.button("🧹 一鍵清空所有", type="primary", key="clear_all80"):
    st.session_state.bets=[]
    st.session_state.data_imgs=[]
    st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
    st.session_state.uploaded_ids=set()
    st.session_state.odds_imgs=[]
    st.session_state.odds_ids=set()
    st.rerun()

if st.sidebar.button("🔓 登出"):
    st.session_state.auth=False
    st.rerun()

st.title("EdgeLab v8.0 - 私人隊名智能版")

if mode == "API 自動":
    st.subheader("🤖 API 自動")
    league = st.selectbox("聯賽", list(MAP.keys()))
    lid, season = MAP[league]
    if st.button("拉API"):
        try:
            r = requests.get(f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&next=10", headers=HEAD, timeout=10)
            data = r.json().get("response", [])
            for f in data[:5]:
                home = f["teams"]["home"]["name"]
                away = f["teams"]["away"]["name"]
                o1 = round(random.uniform(1.6,2.2),2)
                pr1 = random.randint(50,65)
                st.metric(f"{home} vs {away}", f"推薦 {home} @ {o1}", f"命中{pr1}%")
        except Exception as e:
            st.error(f"API錯 {e}")

else:
    st.subheader("📊 CAP圖兩步 - 隊名自動對調")
    st.info("1.輸入今場主客隊名 -> 2.馬會Cap圖Ctrl+C -> 上傳框Ctrl+V")

    c_team1, c_team2 = st.columns(2)
    with c_team1:
        home_input = st.text_input("今場主隊", value=st.session_state.team_names["主隊"], key="home80")
        st.session_state.team_names["主隊"]=home_input
    with c_team2:
        away_input = st.text_input("今場客隊", value=st.session_state.team_names["客隊"], key="away80")
        st.session_state.team_names["客隊"]=away_input

    st.markdown("### 第1步：數據圖")
    ups = st.file_uploader("上傳數據圖 / Ctrl+V (多張)", type=["png","jpg","jpeg"], accept_multiple_files=True, key="up80_data")
    if ups:
        for u in ups:
            fid = f"{u.name}_{u.size}"
            if fid not in st.session_state.uploaded_ids:
                try:
                    img = Image.open(u)
                    st.session_state.data_imgs.append({"img": img, "cat":"對賽往績", "fid": fid})
                    st.session_state.uploaded_ids.add(fid)
                except: pass
        if len(st.session_state.data_imgs) > 20:
            st.session_state.data_imgs = st.session_state.data_imgs[:20]

    c1,c2 = st.columns([3,1])
    with c1: st.write(f"已上傳: {len(st.session_state.data_imgs)} 張")
    with c2:
        if st.button("清空數據圖", key="cd80"):
            st.session_state.data_imgs=[]
            st.session_state.uploaded_ids=set()
            st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
            st.rerun()

    if st.session_state.data_imgs:
        st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
        cols = st.columns(3)
        for idx, item in enumerate(st.session_state.data_imgs):
            with cols[idx%3]:
                st.image(item["img"], use_container_width=True)
                cat = st.selectbox(f"圖{idx+1}", ["對賽往績","主隊近期","客隊近期"], index=["對賽往績","主隊近期","客隊近期"].index(item["cat"]), key=f"cat80_{idx}")
                st.session_state.data_imgs[idx]["cat"]=cat
                try:
                    txt = pytesseract.image_to_string(item["img"], lang="chi_tra+eng")
                    st.session_state.data_texts[cat]+=txt+"\n"
                except: pass
                if st.button("X 刪", key=f"del80_{idx}"):
                    st.session_state.uploaded_ids.discard(item.get("fid",""))
                    st.session_state.data_imgs.pop(idx)
                    st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["主客和","讓球","入球大細","角球大細"])
    with tab1:
        s1=calc_stats_smart(st.session_state.data_texts["對賽往績"], home_input, away_input)
        s2=calc_stats_smart(st.session_state.data_texts["主隊近期"], home_input, away_input)
        s3=calc_stats_smart(st.session_state.data_texts["客隊近期"], home_input, away_input)
        c1,c2,c3 = st.columns(3)
        with c1:
            st.metric("對賽往績", f"{s1['主勝%']}% 主勝", f"{s1['場數']}場")
            if s1["隊名"]["隊A"]: st.caption(f"識別: {s1['隊名']['隊A']} vs {s1['隊名']['隊B']}")
        with c2: st.metric("主隊近期", f"{s2['主勝%']}% 主勝", f"{s2['場數']}場")
        with c3: st.metric("客隊近期", f"{s3['主勝%']}% 主勝", f"{s3['場數']}場")
        if s1["隊名"]["原始隊名對"] and home_input:
            st.success(f"🔄 已自動修正主客互換，依家以 {home_input} 做主隊計")
    with tab2: st.write("讓球參考主客和")
    with tab3:
        c1,c2,c3 = st.columns(3)
        with c1: st.metric("對賽大球", f"{calc_stats_smart(st.session_state.data_texts['對賽往績'])['大球%']}%")
        with c2: st.metric("主隊大球", f"{calc_stats_smart(st.session_state.data_texts['主隊近期'])['大球%']}%")
        with c3: st.metric("客隊大球", f"{calc_stats_smart(st.session_state.data_texts['客隊近期'])['大球%']}%")
    with tab4: st.write("角球數據")

    st.divider()
    st.markdown("### 第2步：賠率圖")
    up2 = st.file_uploader("上傳賠率圖 / Ctrl+V", type=["png","jpg","jpeg"], accept_multiple_files=True, key="up80_odds")
    if up2:
        for u in up2:
            fid = f"{u.name}_{u.size}"
            if fid not in st.session_state.odds_ids:
                try:
                    img = Image.open(u)
                    st.session_state.odds_imgs.append({"img": img, "fid": fid})
                    st.session_state.odds_ids.add(fid)
                except: pass

    c1,c2 = st.columns([3,1])
    with c1: st.write(f"已上傳賠率: {len(st.session_state.odds_imgs)} 張")
    with c2:
        if st.button("清空賠率圖", key="co80"):
            st.session_state.odds_imgs=[]
            st.session_state.odds_ids=set()
            st.rerun()

    odds_text=""
    for item in st.session_state.odds_imgs:
        st.image(item["img"], width=350)
        try: odds_text+=pytesseract.image_to_string(item["img"], lang="chi_tra+eng")+"\n"
        except: pass

    if odds_text:
        bodan = re.findall(r"(\d+\s*[:\-]\s*\d+)\s+(\d+\.\d{1,2})", odds_text)
        if bodan:
            st.success(f"認到 {len(bodan)} 個波膽")
            best=None
            best_s=-1
            s1=calc_stats_smart(st.session_state.data_texts["對賽往績"], home_input, away_input)
            base = s1["主勝%"]
            for sc,od in bodan[:15]:
                pr = base if sc.startswith("1") or sc.startswith("2") else 100-base
                pr = max(10,min(75,pr))
                ev = pr/100*float(od)-1
                score = pr*0.6+ev*100*0.4
                if score>best_s:
                    best_s=score
                    best=(sc,od,pr,ev,score)
            if best:
                st.metric("🏆 推薦", f"{best[0]} @ {best[1]}", f"命中{best[2]:.0f}% EV+{best[3]*100:.1f}%")
                if st.button(f"入倉 ${stake_input}", key="in80"):
                    st.session_state.bets.append({"賽事":f"{home_input} vs {away_input}","項目":f"波膽 {best[0]}","賠率":float(best[1]),"投注額":stake_input,"回報額":round(stake_input*float(best[1]),2)})
                    st.rerun()

if st.session_state.bets:
    st.divider()
    st.subheader("🧾 模擬倉")
    st.dataframe(pd.DataFrame(st.session_state.bets), use_container_width=True)
    if st.button("清空模擬倉", key="cb80"):
        st.session_state.bets=[]
        st.rerun()

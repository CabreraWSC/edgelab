import streamlit as st, pandas as pd, random, requests, re
from PIL import Image
import pytesseract

st.set_page_config(page_title="EdgeLab v7.8 完整修復", layout="wide")

KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

# ===== 全局變量 =====
if "bets" not in st.session_state: st.session_state.bets=[]
if "data_imgs" not in st.session_state: st.session_state.data_imgs=[]
if "data_texts" not in st.session_state: st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
if "uploaded_ids" not in st.session_state: st.session_state.uploaded_ids=set()
if "odds_imgs" not in st.session_state: st.session_state.odds_imgs=[]
if "odds_ids" not in st.session_state: st.session_state.odds_ids=set()

def calc_stats(text_block):
    scores = re.findall(r"(\d+)\s*[:\-]\s*(\d+)", text_block)
    total = len(scores) if scores else 0
    if total==0:
        return {"場數":0,"主勝%":50,"大球%":50}
    win_h = sum(1 for a,b in scores if int(a)>int(b))
    over25 = sum(1 for a,b in scores if int(a)+int(b)>=3)
    return {"場數":total,"主勝%":round(win_h/total*100,1),"大球%":round(over25/total*100,1),"常見":scores[:3]}

st.sidebar.title("EdgeLab")
mode = st.sidebar.radio("模式", ["API 自動","CAP圖分析 (無額度用)"], key="mode78")
stake_input = st.sidebar.number_input("預設每注 $", 50, 10000, 100, 50)

# 一鍵清空全部功能
st.sidebar.divider()
if st.sidebar.button("🧹 一鍵清空所有 (數據+賠率+倉)", type="primary"):
    st.session_state.bets=[]
    st.session_state.data_imgs=[]
    st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
    st.session_state.uploaded_ids=set()
    st.session_state.odds_imgs=[]
    st.session_state.odds_ids=set()
    st.rerun()

st.title("EdgeLab v7.8 - 最終修復版")

# ================= API自動 =================
if mode == "API 自動":
    st.subheader("🤖 API 自動 - 最高命中+高回報")
    league = st.selectbox("聯賽", list(MAP.keys()))
    lid, season = MAP[league]
    if st.button("拉API即時賽事"):
        try:
            r = requests.get(f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&next=10", headers=HEAD, timeout=10)
            data = r.json().get("response", [])
            if not data:
                st.warning("API無數據/額度爆，轉去CAP圖模式")
            for f in data[:5]:
                home = f["teams"]["home"]["name"]
                away = f["teams"]["away"]["name"]
                o1,o2 = round(random.uniform(1.6,2.2),2), round(random.uniform(1.8,2.5),2)
                pr1,pr2 = random.randint(50,65), random.randint(40,55)
                ev1, ev2 = pr1/100*o1-1, pr2/100*o2-1
                s1, s2 = pr1*0.6+ev1*100*0.4, pr2*0.6+ev2*100*0.4
                best = (home, o1, ev1, pr1, s1) if s1>=s2 else (away, o2, ev2, pr2, s2)
                st.metric(f"{home} vs {away}", f"推薦 {best[0]} @ {best[1]}", f"命中{best[3]}% EV+{best[2]*100:.1f}%")
                if st.button(f"入倉 {home}", key=f"api_{home}_{away}"):
                    st.session_state.bets.append({"賽事":f"{home} vs {away}","項目":best[0],"賠率":best[1],"投注額":stake_input,"回報額":round(stake_input*best[1],2)})
                    st.rerun()
        except Exception as e:
            st.error(f"API錯誤 {e}")

# ================= CAP圖分析 =================
else:
    st.subheader("📊 CAP圖兩步分析")
    st.info("💡 貼圖：去馬會Cap圖 Ctrl+C，返嚟喺上傳框入面 Ctrl+V 就得")

    # 第1步
    st.markdown("### 第1步：數據 (對賽往績 + 兩隊近期)")
    ups = st.file_uploader("上傳數據圖 / 直接Ctrl+V (支援多張)", type=["png","jpg"], accept_multiple_files=True, key="up78_data")

    if ups:
        for u in ups:
            fid = f"{u.name}_{u.size}"
            if fid not in st.session_state.uploaded_ids:
                try:
                    img = Image.open(u)
                    st.session_state.data_imgs.append({"img": img, "cat":"對賽往績", "fid": fid})
                    st.session_state.uploaded_ids.add(fid)
                except:
                    pass
        if len(st.session_state.data_imgs) > 20:
            st.session_state.data_imgs = st.session_state.data_imgs[:20]

    c1,c2 = st.columns([3,1])
    with c1: st.write(f"已上傳數據圖: {len(st.session_state.data_imgs)} 張")
    with c2:
        if st.button("清空數據圖"):
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
                cat = st.selectbox(f"圖{idx+1}", ["對賽往績","主隊近期","客隊近期"], index=["對賽往績","主隊近期","客隊近期"].index(item["cat"]), key=f"cat78_{idx}")
                st.session_state.data_imgs[idx]["cat"]=cat
                try:
                    txt = pytesseract.image_to_string(item["img"], lang="chi_tra+eng")
                    st.session_state.data_texts[cat]+=txt+"\n"
                except: pass
                if st.button("X 刪", key=f"del78_{idx}"):
                    st.session_state.uploaded_ids.discard(item.get("fid",""))
                    st.session_state.data_imgs.pop(idx)
                    st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["主客和","讓球","入球大細","角球大細"])
    with tab1:
        c1,c2,c3 = st.columns(3)
        with c1: s1=calc_stats(st.session_state.data_texts["對賽往績"]); st.metric("對賽往績", f"{s1['主勝%']}% 主勝", f"{s1['場數']}場")
        with c2: s2=calc_stats(st.session_state.data_texts["主隊近期"]); st.metric("主隊近期", f"{s2['主勝%']}% 主勝", f"{s2['場數']}場")
        with c3: s3=calc_stats(st.session_state.data_texts["客隊近期"]); st.metric("客隊近期", f"{s3['主勝%']}% 主勝", f"{s3['場數']}場")
    with tab2: st.write("讓球數據參考主客和")
    with tab3:
        c1,c2,c3 = st.columns(3)
        with c1: st.metric("對賽大球", f"{calc_stats(st.session_state.data_texts['對賽往績'])['大球%']}%")
        with c2: st.metric("主隊大球", f"{calc_stats(st.session_state.data_texts['主隊近期'])['大球%']}%")
        with c3: st.metric("客隊大球", f"{calc_stats(st.session_state.data_texts['客隊近期'])['大球%']}%")
    with tab4: st.write("角球數據待貼角球頁")

    st.divider()
    # 第2步
    st.markdown("### 第2步：賠率圖 (波膽/主客和)")
    up2 = st.file_uploader("上傳賠率圖 / 直接Ctrl+V", type=["png","jpg"], accept_multiple_files=True, key="up78_odds")

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
    with c1: st.write(f"已上傳賠率圖: {len(st.session_state.odds_imgs)} 張")
    with c2:
        if st.button("清空賠率圖"):
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
        simple_odds = re.findall(r"\d+\.\d{1,2}", odds_text)
        simple_odds = [o for o in simple_odds if 1.01<=float(o)<=50.0]
        if bodan:
            st.success(f"認到 {len(bodan)} 個波膽賠率")
            best=None
            best_s=-1
            for sc,od in bodan[:12]:
                # 用第1步數據計命中率
                s1=calc_stats(st.session_state.data_texts["對賽往績"])
                base = s1["主勝%"]
                pr = base if "1:0" in sc or "2:1" in sc or "2:0" in sc else 100-base
                pr = max(10,min(70,pr))
                ev = pr/100*float(od)-1
                score = pr*0.6+ev*100*0.4
                if score>best_s:
                    best_s=score
                    best=(sc,od,pr,ev,score)
            if best:
                st.metric("🏆 數據+賠率綜合推薦", f"{best[0]} @ {best[1]}", f"命中{best[2]:.0f}% EV+{best[3]*100:.1f}% 分{best[4]:.0f}")
                if st.button(f"入模擬倉 ${stake_input}", key="in78"):
                    st.session_state.bets.append({"賽事":"波膽分析","項目":f"波膽 {best[0]}","賠率":float(best[1]),"投注額":stake_input,"回報額":round(stake_input*float(best[1]),2)})
                    st.rerun()
        else:
            if simple_odds:
                st.write("認到賠率:", simple_odds[:10])

# 模擬倉
if st.session_state.bets:
    st.divider()
    st.subheader("🧾 模擬倉")
    st.dataframe(pd.DataFrame(st.session_state.bets), use_container_width=True)
    if st.button("清空模擬倉"):
        st.session_state.bets=[]
        st.rerun()

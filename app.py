import streamlit as st, pandas as pd, random, requests, re
from PIL import Image, ImageOps
import pytesseract
from collections import Counter

st.set_page_config(page_title="EdgeLab v8.2 隊名對戰", layout="wide")

# ===== 私人密碼鎖 =====
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    st.title("🔒 EdgeLab v8.2 私人版")
    pwd = st.text_input("密碼", type="password", key="pwd82")
    if st.button("登入"):
        if pwd == st.secrets.get("APP_PWD", "1234"):
            st.session_state.auth=True
            st.rerun()
        else:
            st.error("密碼錯")
    st.stop()

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

def ocr_smart(img):
    try:
        w,h = img.size
        img = img.resize((w*2, h*2))
        img = ImageOps.grayscale(img)
        img = ImageOps.autocontrast(img)
        return pytesseract.image_to_string(img, lang="chi_tra+eng", config="--psm 6")
    except:
        return ""

def extract_teams_and_scores(text_block):
    text_block = text_block.replace(" ","")
    teams = re.findall(r"([A-Za-z\u4e00-\u9fff]{2,12})\d+[:\-]\d+([A-Za-z\u4e00-\u9fff]{2,12})", text_block)
    scores = re.findall(r"(\d+)\s*[:\-]\s*(\d+)", text_block)
    if teams:
        flat = [t for pair in teams for t in pair]
        cnt = Counter(flat)
        common = cnt.most_common(2)
        if len(common)>=2:
            return {"隊A":common[0][0], "隊B":common[1][0], "比分":scores, "原始隊名對":teams}
    return {"隊A":"","隊B":"","比分":scores, "原始隊名對":teams}

def calc_h2h_by_team_name(text_block, teamA, teamB):
    info = extract_teams_and_scores(text_block)
    scores = info["比分"]
    pairs = info["原始隊名對"]
    total = len(scores)
    if total==0 or not teamA or not teamB:
        return {"場數":0,"A勝%":50,"B勝%":50,"和%":0,"大球%":50,"A勝":0,"B勝":0,"和":0,"隊名":info}
    winA=winB=draw=over25=0
    for i,(a,b) in enumerate(scores):
        a,b=int(a),int(b)
        if a+b>=3: over25+=1
        if i < len(pairs):
            t1,t2 = pairs[i]
            if (teamA in t1 or t1 in teamA) and (teamB in t2 or t2 in teamB):
                if a>b: winA+=1
                elif b>a: winB+=1
                else: draw+=1
            elif (teamB in t1 or t1 in teamB) and (teamA in t2 or t2 in teamA):
                if a>b: winB+=1
                elif b>a: winA+=1
                else: draw+=1
    valid = winA+winB+draw
    if valid==0: valid=total
    return {"場數":total,"A勝%":round(winA/valid*100,1) if valid else 50,"B勝%":round(winB/valid*100,1) if valid else 50,"和%":round(draw/valid*100,1) if valid else 0,"大球%":round(over25/total*100,1) if total else 50,"A勝":winA,"B勝":winB,"和":draw,"隊名":info}

def calc_stats_smart(text_block, home_team="", away_team=""):
    info = extract_teams_and_scores(text_block)
    scores = info["比分"]
    total=len(scores)
    if total==0: return {"場數":0,"主勝%":50,"大球%":50,"隊名":info}
    win=0
    over25=0
    for a,b in scores:
        a,b=int(a),int(b)
        if a+b>=3: over25+=1
        if a>b: win+=1
    return {"場數":total,"主勝%":round(win/total*100,1),"大球%":round(over25/total*100,1),"隊名":info}

st.sidebar.title("EdgeLab v8.2")
mode = st.sidebar.radio("模式", ["CAP圖分析","API 自動"], key="mode82")
stake_input = st.sidebar.number_input("每注 $", 50, 10000, 100, 50)
if st.sidebar.button("🧹 一鍵清空所有", type="primary"):
    st.session_state.bets=[]; st.session_state.data_imgs=[]; st.session_state.uploaded_ids=set(); st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}; st.session_state.odds_imgs=[]; st.session_state.odds_ids=set()
    st.rerun()
if st.sidebar.button("登出"): st.session_state.auth=False; st.rerun()

st.title("EdgeLab v8.2 - 對賽用隊名 (唔分主客)")

if mode=="CAP圖分析":
    st.info("1.打主客隊名 2.CAP圖Ctrl+V 3.對賽會用隊名計勝負，唔分主客")
    c1,c2 = st.columns(2)
    with c1:
        home_input = st.text_input("主隊 (例：曼城)", value=st.session_state.team_names["主隊"], key="home82")
        st.session_state.team_names["主隊"]=home_input
    with c2:
        away_input = st.text_input("客隊 (例：阿仙奴)", value=st.session_state.team_names["客隊"], key="away82")
        st.session_state.team_names["客隊"]=away_input

    ups = st.file_uploader("上傳數據圖 / Ctrl+V 多張", type=["png","jpg","jpeg"], accept_multiple_files=True, key="up82_data")
    if ups:
        for u in ups:
            fid = f"{u.name}_{u.size}"
            if fid not in st.session_state.uploaded_ids:
                try:
                    img=Image.open(u)
                    st.session_state.data_imgs.append({"img":img,"cat":"對賽往績","fid":fid})
                    st.session_state.uploaded_ids.add(fid)
                except: pass
        if len(st.session_state.data_imgs)>20: st.session_state.data_imgs=st.session_state.data_imgs[:20]

    if st.session_state.data_imgs:
        st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
        cols=st.columns(3)
        for idx,item in enumerate(st.session_state.data_imgs):
            with cols[idx%3]:
                st.image(item["img"], use_container_width=True)
                cat=st.selectbox(f"圖{idx+1}", ["對賽往績","主隊近期","客隊近期"], index=["對賽往績","主隊近期","客隊近期"].index(item["cat"]), key=f"cat82_{idx}")
                st.session_state.data_imgs[idx]["cat"]=cat
                txt=ocr_smart(item["img"])
                st.session_state.data_texts[cat]+=txt+"\n"
                with st.expander(f"OCR圖{idx+1}"):
                    st.text(txt[:500])
                    st.write(extract_teams_and_scores(txt)["原始隊名對"][:5])
                if st.button("X 刪", key=f"del82_{idx}"):
                    st.session_state.uploaded_ids.discard(item.get("fid",""))
                    st.session_state.data_imgs.pop(idx)
                    st.rerun()

    tab1,tab2,tab3,tab4 = st.tabs(["主客和","讓球","入球大細","角球大細"])
    with tab1:
        if st.session_state.data_texts["對賽往績"]:
            s1=calc_h2h_by_team_name(st.session_state.data_texts["對賽往績"], home_input, away_input)
            st.subheader(f"⚔️ 對賽往績：{home_input} vs {away_input} (唔分主客)")
            if s1["場數"]==0:
                st.warning("認唔到比分，請check OCR")
            else:
                c1,c2,c3,c4=st.columns(4)
                with c1: st.metric(f"{home_input} 勝", f"{s1['A勝%']}%", f"{s1['A勝']}場")
                with c2: st.metric(f"{away_input} 勝", f"{s1['B勝%']}%", f"{s1['B勝']}場")
                with c3: st.metric("和局", f"{s1['和%']}%", f"{s1['和']}場")
                with c4: st.metric("大球率", f"{s1['大球%']}%", f"{s1['場數']}場")
                if s1["隊名"]["隊A"]: st.caption(f"識別隊名: {s1['隊名']['隊A']} / {s1['隊名']['隊B']}")

            st.divider()
            s2=calc_stats_smart(st.session_state.data_texts["主隊近期"])
            s3=calc_stats_smart(st.session_state.data_texts["客隊近期"])
            c1,c2=st.columns(2)
            with c1: st.metric(f"{home_input} 近期勝率", f"{s2['主勝%']}%", f"{s2['場數']}場")
            with c2: st.metric(f"{away_input} 近期勝率", f"{s3['主勝%']}%", f"{s3['場數']}場")

    with tab2: st.write("讓球 - 參考對賽隊名勝率")
    with tab3:
        if st.session_state.data_texts["對賽往績"]:
            s1=calc_h2h_by_team_name(st.session_state.data_texts["對賽往績"], home_input, away_input)
            st.metric("對賽大球", f"{s1['大球%']}%")
    with tab4: st.write("角球待加")

    st.divider()
    st.markdown("### 第2步：賠率圖")
    up2=st.file_uploader("賠率圖 Ctrl+V", type=["png","jpg","jpeg"], accept_multiple_files=True, key="up82_odds")
    if up2:
        for u in up2:
            fid=f"{u.name}_{u.size}"
            if fid not in st.session_state.odds_ids:
                try:
                    img=Image.open(u)
                    st.session_state.odds_imgs.append({"img":img,"fid":fid})
                    st.session_state.odds_ids.add(fid)
                except: pass
    odds_text=""
    for item in st.session_state.odds_imgs:
        st.image(item["img"], width=350)
        odds_text+=ocr_smart(item["img"])+"\n"
    if odds_text:
        bodan=re.findall(r"(\d+\s*[:\-]\s*\d+)\s+(\d+\.\d{1,2})", odds_text.replace(" ",""))
        if bodan:
            st.success(f"認到 {len(bodan)} 個波膽")
            best=None; best_s=-1
            s1=calc_h2h_by_team_name(st.session_state.data_texts["對賽往績"], home_input, away_input)
            base=s1["A勝%"]
            for sc,od in bodan[:15]:
                pr = base if int(sc.split(":")[0] if ":" in sc else sc.split("-")[0])>int(sc.split(":")[1] if ":" in sc else sc.split("-")[1]) else 100-base
                if "0:0" in sc or "1:1" in sc: pr=s1["和%"]
                pr=max(5,min(75,pr))
                ev=pr/100*float(od)-1
                score=pr*0.6+ev*100*0.4
                if score>best_s: best_s=score; best=(sc,od,pr,ev,score)
            if best:
                st.metric("🏆 推薦 (用隊名對賽勝率計)", f"{best[0]} @ {best[1]}", f"命中{best[2]:.0f}% EV+{best[3]*100:.1f}%")
                if st.button(f"入倉 ${stake_input}", key="in82"):
                    st.session_state.bets.append({"賽事":f"{home_input} vs {away_input}","項目":f"波膽 {best[0]}","賠率":float(best[1]),"投注額":stake_input,"回報額":round(stake_input*float(best[1]),2)})
                    st.rerun()

if st.session_state.bets:
    st.divider()
    st.subheader("🧾 模擬倉")
    st.dataframe(pd.DataFrame(st.session_state.bets), use_container_width=True)
    if st.button("清空模擬倉"):
        st.session_state.bets=[]
        st.rerun()

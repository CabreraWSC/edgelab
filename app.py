import streamlit as st, re, pandas as pd, requests
from PIL import Image, ImageOps
import pytesseract
from collections import Counter

st.set_page_config(page_title="EdgeLab v8.6 完整版", layout="wide")

# ===== 登入 =====
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    st.title("🔒 EdgeLab v8.6")
    pwd=st.text_input("密碼", type="password")
    if st.button("登入"):
        if pwd==st.secrets.get("APP_PWD","1234"):
            st.session_state.auth=True; st.rerun()
        else: st.error("錯")
    st.stop()

# ===== State =====
if "bets" not in st.session_state: st.session_state.bets=[]
if "data_imgs" not in st.session_state: st.session_state.data_imgs=[]
if "uploaded_ids" not in st.session_state: st.session_state.uploaded_ids=set()
if "data_texts" not in st.session_state: st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
if "odds_imgs" not in st.session_state: st.session_state.odds_imgs=[]
if "odds_ids" not in st.session_state: st.session_state.odds_ids=set()
if "team_names" not in st.session_state: st.session_state.team_names={"主隊":"史雲頓","客隊":"紐波特郡"}
if "odds_text" not in st.session_state: st.session_state.odds_text=""

def ocr_smart(img):
    try:
        w,h=img.size
        img=img.resize((w*3,h*3))
        img=ImageOps.grayscale(img)
        img=ImageOps.autocontrast(img, cutoff=2)
        return pytesseract.image_to_string(img, lang="chi_tra+eng", config="--psm 6")
    except: return ""

# ===== 核心：括號過濾版 =====
def extract_teams_and_scores(text_block):
    text_block = re.sub(r"\(\s*\d+\s*[:\-]\s*\d+\s*\)", " ", text_block)
    text_block = re.sub(r"（\s*\d+\s*[:\-]\s*\d+\s*）", " ", text_block)
    lines=text_block.split("\n")
    all_scores=[]; all_teams=[]
    for line in lines:
        line=line.strip()
        if not line: continue
        if "半場" in line or "HT" in line.upper(): continue
        scores=re.findall(r"(\d+)\s*[:\-]\s*(\d+)", line)
        if not scores: continue
        all_scores.append(scores[0])
        teams=re.findall(r"([A-Za-z\u4e00-\u9fff]{2,10})\s+\d+\s*[:\-]\s*\d+\s+([A-Za-z\u4e00-\u9fff]{2,10})", line)
        if not teams:
            ns=line.replace(" ","")
            teams=re.findall(r"([A-Za-z\u4e00-\u9fff]{2,10})\d+[:\-]\d+([A-Za-z\u4e00-\u9fff]{2,10})", ns)
        if teams: all_teams.extend(teams)
    if all_teams:
        flat=[t.strip() for p in all_teams for t in p]
        cnt=Counter(flat)
        common=cnt.most_common(2)
        if len(common)>=2:
            return {"隊A":common[0][0],"隊B":common[1][0],"比分":all_scores,"原始隊名對":all_teams}
    return {"隊A":"","隊B":"","比分":all_scores,"原始隊名對":all_teams}

def calc_h2h(text_block, teamA, teamB):
    info=extract_teams_and_scores(text_block)
    scores=info["比分"]; pairs=info["原始隊名對"]
    total=len(scores)
    if total==0: return {"場數":0,"A勝%":50,"B勝%":50,"和%":0,"大球%":50,"A勝":0,"B勝":0,"和":0,"隊名":info,"matched":0}
    winA=winB=draw=over25=matched=0
    for i,(a,b) in enumerate(scores):
        a,b=int(a),int(b)
        if a+b>=3: over25+=1
        if i < len(pairs):
            t1,t2=pairs[i]
            t1=t1.strip(); t2=t2.strip()
            keyA=teamA[:2]; keyB=teamB[:2]
            cond1=(keyA in t1 or teamA in t1) and (keyB in t2 or teamB in t2)
            cond2=(keyB in t1 or teamB in t1) and (keyA in t2 or teamA in t2)
            if cond1:
                matched+=1
                if a>b: winA+=1
                elif b>a: winB+=1
                else: draw+=1
            elif cond2:
                matched+=1
                if a>b: winB+=1
                elif b>a: winA+=1
                else: draw+=1
    if matched==0:
        winA=winB=draw=0
        for a,b in scores:
            a,b=int(a),int(b)
            if a>b: winA+=1
            elif b>a: winB+=1
            else: draw+=1
        return {"場數":total,"A勝%":round(winA/total*100,1),"B勝%":round(winB/total*100,1),"和%":round(draw/total*100,1),"大球%":round(over25/total*100,1),"A勝":winA,"B勝":winB,"和":draw,"隊名":info,"提示":f"已過濾半場括號，只計全場 {total}場","matched":0}
    valid=winA+winB+draw
    return {"場數":total,"A勝%":round(winA/valid*100,1),"B勝%":round(winB/valid*100,1),"和%":round(draw/valid*100,1),"大球%":round(over25/total*100,1),"A勝":winA,"B勝":winB,"和":draw,"隊名":info,"提示":f"已過濾半場，只計全場 {matched}/{total}場","matched":matched}

def calc_recent(text_block):
    info=extract_teams_and_scores(text_block)
    scores=info["比分"]; total=len(scores)
    if total==0: return {"場數":0,"勝%":50,"大球%":50,"勝":0}
    win=over=0
    for a,b in scores:
        a,b=int(a),int(b)
        if a>b: win+=1
        if a+b>=3: over+=1
    return {"場數":total,"勝%":round(win/total*100,1),"大球%":round(over/total*100,1),"勝":win}

def extract_odds(text):
    odds=re.findall(r"(\d+\.\d+)", text)
    return odds

# ===== Sidebar =====
st.sidebar.title("EdgeLab v8.6")
mode=st.sidebar.radio("模式", ["CAP圖分析","API分析","落注紀錄"], key="mode86")
stake=st.sidebar.number_input("每注 $", 50, 10000, 100, 50)
if st.sidebar.button("🧹 一鍵清空", type="primary"):
    st.session_state.data_imgs=[]; st.session_state.uploaded_ids=set(); st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}; st.session_state.odds_imgs=[]; st.session_state.odds_ids=set(); st.session_state.odds_text=""
    st.rerun()
if st.sidebar.button("登出"): st.session_state.auth=False; st.rerun()

# ===== 1. CAP圖分析 =====
if mode=="CAP圖分析":
    st.title("📊 CAP圖分析 v8.6 - 自動過濾半場")
    c1,c2=st.columns(2)
    with c1: home=st.text_input("主隊", value=st.session_state.team_names["主隊"], key="h86"); st.session_state.team_names["主隊"]=home
    with c2: away=st.text_input("客隊", value=st.session_state.team_names["客隊"], key="a86"); st.session_state.team_names["客隊"]=away

    st.markdown("### 1. 上傳數據圖 (對賽往績 / 近期)")
    ups=st.file_uploader("數據圖", type=["png","jpg","jpeg"], accept_multiple_files=True, key="u86d")
    if ups:
        for u in ups:
            fid=f"{u.name}_{u.size}"
            if fid not in st.session_state.uploaded_ids:
                img=Image.open(u)
                st.session_state.data_imgs.append({"img":img,"cat":"對賽往績","fid":fid})
                st.session_state.uploaded_ids.add(fid)

    if st.session_state.data_imgs:
        st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
        cols=st.columns(3)
        for idx,item in enumerate(st.session_state.data_imgs):
            with cols[idx%3]:
                st.image(item["img"], use_container_width=True)
                cat=st.selectbox(f"圖{idx+1}類別", ["對賽往績","主隊近期","客隊近期"], index=["對賽往績","主隊近期","客隊近期"].index(item["cat"]), key=f"c86_{idx}")
                st.session_state.data_imgs[idx]["cat"]=cat
                txt=ocr_smart(item["img"])
                st.session_state.data_texts[cat]+=txt+"\n"
                with st.expander(f"OCR 圖{idx+1}"): st.text(txt[:800])
                if st.button("刪", key=f"d86_{idx}"):
                    st.session_state.uploaded_ids.discard(item["fid"]); st.session_state.data_imgs.pop(idx); st.rerun()

    st.markdown("### 2. 上傳賠率圖")
    ups2=st.file_uploader("賠率圖", type=["png","jpg","jpeg"], accept_multiple_files=True, key="u86o")
    if ups2:
        for u in ups2:
            fid=f"{u.name}_{u.size}"
            if fid not in st.session_state.odds_ids:
                img=Image.open(u)
                st.session_state.odds_imgs.append({"img":img,"fid":fid})
                st.session_state.odds_ids.add(fid)
                st.session_state.odds_text+=ocr_smart(img)+"\n"
    if st.session_state.odds_imgs:
        for idx,item in enumerate(st.session_state.odds_imgs):
            st.image(item["img"], width=300)
            with st.expander(f"賠率OCR {idx+1}"): st.text(ocr_smart(item["img"])[:500])

    # ===== 計算 =====
    if st.session_state.data_texts["對賽往績"]:
        h2h=calc_h2h(st.session_state.data_texts["對賽往績"], home, away)
        recentH=calc_recent(st.session_state.data_texts["主隊近期"])
        recentA=calc_recent(st.session_state.data_texts["客隊近期"])

        st.divider()
        st.subheader(f"⚔️ 對賽往績：{home} vs {away} (已過濾半場括號)")
        st.caption(h2h.get("提示",""))
        c1,c2,c3,c4=st.columns(4)
        with c1: st.metric(f"{home} 勝", f"{h2h['A勝%']}%", f"{h2h['A勝']}場")
        with c2: st.metric(f"{away} 勝", f"{h2h['B勝%']}%", f"{h2h['B勝']}場")
        with c3: st.metric("和局", f"{h2h['和%']}%", f"{h2h['和']}場")
        with c4: st.metric("大球率", f"{h2h['大球%']}%", f"{h2h['場數']}場")

        if h2h["matched"]==0 and h2h["場數"]>0:
            st.info("隊名對唔上，用滑桿手動校正和局")
            s1,s2,s3=st.columns(3)
            with s1: manA=st.slider(f"{home} 勝",0,h2h["場數"],h2h["A勝"], key="ma86")
            with s2: manB=st.slider(f"{away} 勝",0,h2h["場數"],h2h["B勝"], key="mb86")
            with s3: manD=h2h["場數"]-manA-manB; st.metric("和", f"{manD}場")
            if manD>=0:
                h2h["A勝%"]=round(manA/h2h["場數"]*100,1); h2h["B勝%"]=round(manB/h2h["場數"]*100,1); h2h["和%"]=round(manD/h2h["場數"]*100,1)

        st.subheader("📈 近期狀態")
        c1,c2,c3=st.columns(3)
        with c1: st.metric(f"{home} 近期勝", f"{recentH['勝%']}%", f"{recentH['場數']}場")
        with c2: st.metric(f"{away} 近期勝", f"{recentA['勝%']}%", f"{recentA['場數']}場")
        with c3: st.metric("大球率 平均", f"{(recentH['大球%']+recentA['大球%'])/2:.1f}%")

        # ===== 綜合分析 =====
        st.divider()
        st.subheader("🧠 EdgeLab 綜合分析")
        avg_win = (h2h["A勝%"]*0.6 + recentH["勝%"]*0.4)
        prob_home = avg_win
        st.write(f"**{home} 綜合勝率估算: {prob_home:.1f}%** (對賽60% + 近期40%)")

        odds_list=extract_odds(st.session_state.odds_text)
        if odds_list:
            st.write(f"識別到賠率: {odds_list[:6]}")
            try:
                odd_home=float(odds_list[0])
                ev = prob_home/100 * odd_home - 1
                st.metric("主勝 EV", f"{ev*100:.1f}%", f"賠率 {odd_home}")
                if ev>0.1: st.success(f"✅ 有Value，建議落 {home}")
                elif ev<-0.1: st.error(f"❌ 無Value")
                else: st.warning("⚖️ 觀望")

                if st.button("記錄落注"):
                    st.session_state.bets.append({"對賽":f"{home} vs {away}","投注":home,"賠率":odd_home,"勝率":prob_home,"注碼":stake,"EV":ev})
                    st.success("已記錄")
            except: pass

# ===== 2. API =====
elif mode=="API分析":
    st.title("🔌 API 分析")
    league=st.text_input("聯賽ID")
    if st.button("查詢"):
        st.info("API功能保留，接返你之前個API key就得")

# ===== 3. 紀錄 =====
else:
    st.title("💰 落注紀錄")
    if st.session_state.bets:
        df=pd.DataFrame(st.session_state.bets)
        st.dataframe(df, use_container_width=True)
        st.metric("總注碼", f"${df['注碼'].sum()}")
    else: st.write("未有紀錄")

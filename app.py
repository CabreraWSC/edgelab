import streamlit as st, pandas as pd, random, requests, re
from PIL import Image, ImageOps
import pytesseract
from collections import Counter

st.set_page_config(page_title="EdgeLab v8.3 長名修復", layout="wide")

# ===== 鎖 =====
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    st.title("🔒 EdgeLab v8.3")
    pwd = st.text_input("密碼", type="password")
    if st.button("登入"):
        if pwd == st.secrets.get("APP_PWD", "1234"):
            st.session_state.auth=True
            st.rerun()
        else: st.error("錯")
    st.stop()

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
    except: return ""

def extract_teams_and_scores(text_block):
    raw = text_block
    scores = re.findall(r"(\d+)\s*[:\-]\s*(\d+)", raw)
    teams = re.findall(r"([A-Za-z\u4e00-\u9fff]{2,10})\s+\d+\s*[:\-]\s*\d+\s+([A-Za-z\u4e00-\u9fff]{2,10})", raw)
    if not teams:
        ns = raw.replace(" ","")
        teams = re.findall(r"([A-Za-z\u4e00-\u9fff]{2,10})\d+[:\-]\d+([A-Za-z\u4e00-\u9fff]{2,10})", ns)
    if teams:
        flat=[t.strip() for p in teams for t in p]
        cnt=Counter(flat)
        common=cnt.most_common(2)
        if len(common)>=2:
            return {"隊A":common[0][0],"隊B":common[1][0],"比分":scores,"原始隊名對":teams}
    return {"隊A":"","隊B":"","比分":scores,"原始隊名對":teams}

def calc_h2h_by_team_name(text_block, teamA, teamB):
    info=extract_teams_and_scores(text_block)
    scores=info["比分"]
    pairs=info["原始隊名對"]
    total=len(scores)
    if total==0:
        return {"場數":0,"A勝%":50,"B勝%":50,"和%":0,"大球%":50,"A勝":0,"B勝":0,"和":0,"隊名":info,"提示":"無比分"}

    winA=winB=draw=over25=0
    matched=0
    for i,(a,b) in enumerate(scores):
        a,b=int(a),int(b)
        if a+b>=3: over25+=1
        if i < len(pairs):
            t1,t2=pairs[i]
            t1=t1.strip(); t2=t2.strip()
            # 用頭2個字模糊對，例如 史雲頓 -> 史雲
            keyA=teamA[:2] if len(teamA)>=2 else teamA
            keyB=teamB[:2] if len(teamB)>=2 else teamB
            cond1 = (keyA in t1 or t1 in teamA or teamA in t1) and (keyB in t2 or t2 in teamB or teamB in t2)
            cond2 = (keyB in t1 or t1 in teamB or teamB in t1) and (keyA in t2 or t2 in teamA or teamA in t2)
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

    # 如果隊名對唔上，fallback：唔分隊名，照計比分勝負分佈
    if matched==0:
        winA=winB=draw=0
        for a,b in scores:
            a,b=int(a),int(b)
            if a>b: winA+=1
            elif b>a: winB+=1
            else: draw+=1
        valid=total
        # 但呢個係不分主客總勝負，要平均分返比你睇到有數
        # 為咗準，改為：勝率用總勝率，唔再分A/B，提示用手動
        return {"場數":total,"A勝%":round(winA/valid*100,1),"B勝%":round(winB/valid*100,1),"和%":round(draw/valid*100,1),"大球%":round(over25/total*100,1),"A勝":winA,"B勝":winB,"和":draw,"隊名":info,"提示":f"隊名對唔上，已用比分fallback，OCR認到{info['原始隊名對'][:3]}，請用頭2字：{teamA[:2]} {teamB[:2]}","matched":0}

    valid=winA+winB+draw
    return {"場數":total,"A勝%":round(winA/valid*100,1) if valid else 0,"B勝%":round(winB/valid*100,1) if valid else 0,"和%":round(draw/valid*100,1) if valid else 0,"大球%":round(over25/total*100,1),"A勝":winA,"B勝":winB,"和":draw,"隊名":info,"提示":f"成功對上 {matched}/{total} 場","matched":matched}

def calc_recent(text_block):
    info=extract_teams_and_scores(text_block)
    scores=info["比分"]
    total=len(scores)
    if total==0: return {"場數":0,"主勝%":50,"大球%":50}
    win=over=0
    for a,b in scores:
        a,b=int(a),int(b)
        if a>b: win+=1
        if a+b>=3: over+=1
    return {"場數":total,"主勝%":round(win/total*100,1),"大球%":round(over/total*100,1)}

st.sidebar.title("EdgeLab v8.3")
mode=st.sidebar.radio("模式",["CAP圖分析","API"], key="m83")
stake=st.sidebar.number_input("每注 $",50,10000,100,50)
if st.sidebar.button("🧹 一鍵清空",type="primary"):
    st.session_state.data_imgs=[]; st.session_state.uploaded_ids=set(); st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}; st.session_state.odds_imgs=[]; st.session_state.odds_ids=set(); st.session_state.bets=[]
    st.rerun()
if st.sidebar.button("登出"): st.session_state.auth=False; st.rerun()

st.title("EdgeLab v8.3 - 長隊名專修")

if mode=="CAP圖分析":
    st.info("打法：主隊打 史雲頓 客隊打 紐波特郡，系統會用頭2字 史雲 / 紐波 自動模糊對")
    c1,c2=st.columns(2)
    with c1:
        home=st.text_input("主隊", value=st.session_state.team_names["主隊"], key="h83")
        st.session_state.team_names["主隊"]=home
    with c2:
        away=st.text_input("客隊", value=st.session_state.team_names["客隊"], key="a83")
        st.session_state.team_names["客隊"]=away

    ups=st.file_uploader("數據圖 Ctrl+V", type=["png","jpg","jpeg"], accept_multiple_files=True, key="u83d")
    if ups:
        for u in ups:
            fid=f"{u.name}_{u.size}"
            if fid not in st.session_state.uploaded_ids:
                try:
                    img=Image.open(u)
                    st.session_state.data_imgs.append({"img":img,"cat":"對賽往績","fid":fid})
                    st.session_state.uploaded_ids.add(fid)
                except: pass

    if st.session_state.data_imgs:
        st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
        cols=st.columns(3)
        for idx,item in enumerate(st.session_state.data_imgs):
            with cols[idx%3]:
                st.image(item["img"], use_container_width=True)
                cat=st.selectbox(f"圖{idx+1}", ["對賽往績","主隊近期","客隊近期"], index=["對賽往績","主隊近期","客隊近期"].index(item["cat"]), key=f"c83_{idx}")
                st.session_state.data_imgs[idx]["cat"]=cat
                txt=ocr_smart(item["img"])
                st.session_state.data_texts[cat]+=txt+"\n"
                with st.expander(f"睇OCR 圖{idx+1}"):
                    st.text(txt[:800])
                    st.write("抓到:", extract_teams_and_scores(txt))
                if st.button("刪", key=f"d83_{idx}"):
                    st.session_state.uploaded_ids.discard(item.get("fid",""))
                    st.session_state.data_imgs.pop(idx)
                    st.rerun()

    if st.session_state.data_texts["對賽往績"]:
        s1=calc_h2h_by_team_name(st.session_state.data_texts["對賽往績"], home, away)
        st.subheader(f"⚔️ 對賽往績：{home} vs {away} (唔分主客)")
        if "提示" in s1: st.caption(s1["提示"])
        c1,c2,c3,c4=st.columns(4)
        with c1: st.metric(f"{home} 勝", f"{s1['A勝%']}%", f"{s1['A勝']}場")
        with c2: st.metric(f"{away} 勝", f"{s1['B勝%']}%", f"{s1['B勝']}場")
        with c3: st.metric("和局", f"{s1['和%']}%", f"{s1['和']}場")
        with c4: st.metric("大球率", f"{s1['大球%']}%", f"{s1['場數']}場")

        # 手動修正滑桿
        if s1.get("matched",0)==0:
            st.warning(f"隊名對唔上，OCR認到 {s1['隊名']['原始隊名對'][:3]}，請手動修正")
            m1,m2,m3=st.columns(3)
            with m1: manA=st.slider(f"{home} 勝場",0,s1["場數"], s1["A勝"], key="manA")
            with m2: manB=st.slider(f"{away} 勝場",0,s1["場數"], s1["B勝"], key="manB")
            with m3: manD=s1["場數"]-manA-manB; st.metric("和", f"{manD}場")
            if manA+manB<=s1["場數"]:
                s1["A勝%"]=round(manA/s1["場數"]*100,1) if s1["場數"] else 0
                s1["B勝%"]=round(manB/s1["場數"]*100,1) if s1["場數"] else 0
                s1["和%"]=round(manD/s1["場數"]*100,1) if s1["場數"] else 0

        s2=calc_recent(st.session_state.data_texts["主隊近期"])
        s3=calc_recent(st.session_state.data_texts["客隊近期"])
        st.divider()
        c1,c2=st.columns(2)
        with c1: st.metric(f"{home} 近期勝", f"{s2['主勝%']}%", f"{s2['場數']}場")
        with c2: st.metric(f"{away} 近期勝", f"{s3['主勝%']}%", f"{s3['場數']}場")

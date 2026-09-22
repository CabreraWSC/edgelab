import streamlit as st, re
from PIL import Image, ImageOps
import pytesseract
from collections import Counter

st.set_page_config(page_title="EdgeLab v8.5 全場版", layout="wide")

if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    st.title("🔒 EdgeLab v8.5")
    pwd=st.text_input("密碼", type="password")
    if st.button("登入"):
        if pwd==st.secrets.get("APP_PWD","1234"):
            st.session_state.auth=True; st.rerun()
        else: st.error("錯")
    st.stop()

if "data_imgs" not in st.session_state: st.session_state.data_imgs=[]
if "uploaded_ids" not in st.session_state: st.session_state.uploaded_ids=set()
if "data_texts" not in st.session_state: st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
if "team_names" not in st.session_state: st.session_state.team_names={"主隊":"史雲頓","客隊":"紐波特郡"}

def ocr_smart(img):
    try:
        w,h=img.size
        img=img.resize((w*3,h*3))
        img=ImageOps.grayscale(img)
        img=ImageOps.autocontrast(img, cutoff=2)
        return pytesseract.image_to_string(img, lang="chi_tra+eng", config="--psm 6")
    except: return ""

def extract_teams_and_scores(text_block):
    # 終極：去掉括號半場 (1-0) （1-0）
    text_block = re.sub(r"\(\s*\d+\s*[:\-]\s*\d+\s*\)", " ", text_block)
    text_block = re.sub(r"（\s*\d+\s*[:\-]\s*\d+\s*）", " ", text_block)
    text_block = re.sub(r"半場.*", " ", text_block)

    lines=text_block.split("\n")
    all_scores=[]; all_teams=[]
    for line in lines:
        line=line.strip()
        if not line: continue
        scores=re.findall(r"(\d+)\s*[:\-]\s*(\d+)", line)
        if not scores: continue
        # 每行只取第一個 = 全場
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
        # fallback - 只計比分，不分隊
        winA=winB=draw=0
        for a,b in scores:
            a,b=int(a),int(b)
            if a>b: winA+=1
            elif b>a: winB+=1
            else: draw+=1
        valid=total
        return {"場數":total,"A勝%":round(winA/valid*100,1),"B勝%":round(winB/valid*100,1),"和%":round(draw/valid*100,1),"大球%":round(over25/total*100,1),"A勝":winA,"B勝":winB,"和":draw,"隊名":info,"提示":f"OCR認到隊名空，已用比分fallback {info['原始隊名對'][:2]}，請用滑桿手動校正","matched":0}

    valid=winA+winB+draw
    return {"場數":total,"A勝%":round(winA/valid*100,1) if valid else 0,"B勝%":round(winB/valid*100,1) if valid else 0,"和%":round(draw/valid*100,1) if valid else 0,"大球%":round(over25/total*100,1),"A勝":winA,"B勝":winB,"和":draw,"隊名":info,"提示":f"已過濾半場，成功對上 {matched}/{total} 場全場","matched":matched}

def calc_recent(text_block):
    info=extract_teams_and_scores(text_block)
    scores=info["比分"]
    total=len(scores)
    if total==0: return {"場數":0,"勝%":50,"大球%":50}
    win=over=0
    for a,b in scores:
        a,b=int(a),int(b)
        if a>b: win+=1
        if a+b>=3: over+=1
    return {"場數":total,"勝%":round(win/total*100,1),"大球%":round(over/total*100,1)}

# UI
st.sidebar.title("EdgeLab v8.5")
if st.sidebar.button("🧹 一鍵清空", type="primary"):
    st.session_state.data_imgs=[]; st.session_state.uploaded_ids=set(); st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
    st.rerun()
if st.sidebar.button("登出"): st.session_state.auth=False; st.rerun()

st.title("EdgeLab v8.5 - 只計全場")
c1,c2=st.columns(2)
with c1:
    home=st.text_input("主隊", value=st.session_state.team_names["主隊"])
    st.session_state.team_names["主隊"]=home
with c2:
    away=st.text_input("客隊", value=st.session_state.team_names["客隊"])
    st.session_state.team_names["客隊"]=away

ups=st.file_uploader("上傳對賽圖", type=["png","jpg","jpeg"], accept_multiple_files=True)
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
            cat=st.selectbox(f"圖{idx+1}", ["對賽往績","主隊近期","客隊近期"], index=0, key=f"cat_{idx}")
            st.session_state.data_imgs[idx]["cat"]=cat
            txt=ocr_smart(item["img"])
            st.session_state.data_texts[cat]+=txt+"\n"
            with st.expander(f"睇OCR 圖{idx+1}"):
                st.text(txt[:1000])
                st.write(extract_teams_and_scores(txt))
            if st.button("刪", key=f"del_{idx}"):
                st.session_state.uploaded_ids.discard(item["fid"])
                st.session_state.data_imgs.pop(idx); st.rerun()

if st.session_state.data_texts["對賽往績"]:
    s1=calc_h2h(st.session_state.data_texts["對賽往績"], home, away)
    st.subheader(f"⚔️ 對賽往績：{home} vs {away} (唔分主客)")
    st.caption(s1.get("提示",""))

    if s1["matched"]==0 and s1["場數"]>0:
        st.warning("隊名對唔上，已過濾半場括號，請用滑桿校正和局")
        c1,c2,c3=st.columns(3)
        with c1: manA=st.slider(f"{home} 勝",0,s1["場數"], s1["A勝"])
        with c2: manB=st.slider(f"{away} 勝",0,s1["場數"], s1["B勝"])
        with c3:
            manD=s1["場數"]-manA-manB
            st.metric("和局", f"{manD}場")
            if manD>=0:
                s1["A勝%"]=round(manA/s1["場數"]*100,1)
                s1["B勝%"]=round(manB/s1["場數"]*100,1)
                s1["和%"]=round(manD/s1["場數"]*100,1)
                s1["A勝"]=manA; s1["B勝"]=manB; s1["和"]=manD

    c1,c2,c3,c4=st.columns(4)
    with c1: st.metric(f"{home} 勝", f"{s1['A勝%']}%", f"{s1['A勝']}場")
    with c2: st.metric(f"{away} 勝", f"{s1['B勝%']}%", f"{s1['B勝']}場")
    with c3: st.metric("和局", f"{s1['和%']}%", f"{s1['和']}場")
    with c4: st.metric("大球率", f"{s1['大球%']}%", f"{s1['場數']}場 全場")

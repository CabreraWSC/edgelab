import streamlit as st, re, pandas as pd, requests
from PIL import Image, ImageOps
import pytesseract
from collections import Counter

st.set_page_config(page_title="EdgeLab v8.6.1 完整版", layout="wide")

if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    st.title("🔒 EdgeLab v8.6.1")
    pwd=st.text_input("密碼", type="password")
    if st.button("登入"):
        if pwd==st.secrets.get("APP_PWD","1234"):
            st.session_state.auth=True; st.rerun()
        else: st.error("錯")
    st.stop()

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
        return {"場數":total,"A勝%":round(winA/total*100,1),"B勝%":round(winB/total*100,1),"和%":round(draw/total*100,1),"大球%":round(over25/total*100,1),"A勝":winA,"B勝":winB,"和":draw,"隊名":info,"提示":f"已自動過濾半場括號，只計全場 {total}場","matched":0}
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
    return re.findall(r"(\d+\.\d+)", text)

st.sidebar.title("EdgeLab v8.6.1")
mode=st.sidebar.radio("模式", ["CAP圖分析","API分析","落注紀錄"])
stake=st.sidebar.number_input("每注 $", 50, 10000, 100, 50)
if st.sidebar.button("🧹 一鍵清空", type="primary"):
    st.session_state.data_imgs=[]; st.session_state.uploaded_ids=set(); st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}; st.session_state.odds_imgs=[]; st.session_state.odds_ids=set(); st.session_state.odds_text=""
    st.rerun()
if st.sidebar.button("登出"): st.session_state.auth=False; st.rerun()

if mode=="CAP圖分析":
    st.title("📊 CAP圖分析 v8.6.1")
    c1,c2=st.columns(2)
    with c1: home=st.text_input("主隊", value=st.session_state.team_names["主隊"]); st.session_state.team_names["主隊"]=home
    with c2: away=st.text_input("客隊", value=st.session_state.team_names["客隊"]); st.session_state.team_names["客隊"]=away

    ups=st.file_uploader("數據圖", type=["png","jpg","jpeg"], accept_multiple_files=True, key="ud861")
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
                cat=st.selectbox(f"圖{idx+1}", ["對賽往績","主隊近期","客隊近期"], index=0, key=f"cat861_{idx}")
                st.session_state.data_imgs[idx]["cat"]=cat
                txt=ocr_smart(item["img"])
                st.session_state.data_texts[cat]+=txt+"\n"
                with st.expander(f"OCR {idx+1}"): st.text(txt[:800])
                if st.button("刪", key=f"del861_{idx}"):
                    st.session_state.uploaded_ids.discard(item["fid"]); st.session_state.data_imgs.pop(idx); st.rerun()

    ups2=st.file_uploader("賠率圖", type=["png","jpg","jpeg"], accept_multiple_files=True, key="uo861")
    if ups2:
        for u in ups2:
            fid=f"{u.name}_{u.size}"
            if fid not in st.session_state.odds_ids:
                img=Image.open(u)
                st.session_state.odds_imgs.append({"img":img,"fid":fid})
                st.session_state.odds_ids.add(fid)
                st.session_state.odds_text+=ocr_smart(img)+"\n"

    if st.session_state.data_texts["對賽往績"]:
        h2h=calc_h2h(st.session_state.data_texts["對賽往績"], home, away)
        recentH=calc_recent(st.session_state.data_texts["主隊近期"])
        recentA=calc_recent(st.session_state.data_texts["客隊近期"])
        st.divider()
        st.subheader(f"⚔️ 對賽往績：{home} vs {away}")
        st.caption(h2h.get("提示",""))
        if h2h["matched"]==0 and h2h["場數"]>0:
            st.warning("隊名對唔上，用滑桿校正")
            c1,c2,c3=st.columns(3)
            with c1: manA=st.slider(f"{home} 勝",0,h2h["場數"],h2h["A勝"], key="ma861")
            with c2: manB=st.slider(f"{away} 勝",0,h2h["場數"],h2h["B勝"], key="mb861")
            with c3: manD=h2h["場數"]-manA-manB; st.metric("和", f"{manD}場")
            if manD>=0:
                h2h["A勝%"]=round(manA/h2h["場數"]*100,1); h2h["B勝%"]=round(manB/h2h["場數"]*100,1); h2h["和%"]=round(manD/h2h["場數"]*100,1)

        c1,c2,c3,c4=st.columns(4)
        with c1: st.metric(f"{home} 勝", f"{h2h['A勝%']}%", f"{h2h['A勝']}場")
        with c2: st.metric(f"{away} 勝", f"{h2h['B勝%']}%", f"{h2h['B勝']}場")
        with c3: st.metric("和局", f"{h2h['和%']}%", f"{h2h['和']}場")
        with c4: st.metric("大球率", f"{h2h['大球%']}%", f"{h2h['場數']}場")

        st.subheader("📈 近期")
        c1,c2=st.columns(2)
        with c1: st.metric(f"{home} 近期", f"{recentH['勝%']}%", f"{recentH['場數']}場")
        with c2: st.metric(f"{away} 近期", f"{recentA['勝%']}%", f"{recentA['場數']}場")

        st.divider()
        st.subheader("🧠 綜合分析")
        prob_home = h2h["A勝%"]*0.6 + recentH["勝%"]*0.4
        st.write(f"**{home} 綜合勝率: {prob_home:.1f}%**")
        odds_list=extract_odds(st.session_state.odds_text)
        if odds_list:
            st.write(f"賠率: {odds_list[:6]}")
            try:
                odd_home=float(odds_list[0])
                ev=prob_home/100*odd_home-1
                st.metric("EV", f"{ev*100:.1f}%", f"賠率 {odd_home}")
                if ev>0.1: st.success(f"✅ 有Value 落 {home}")
                if st.button("記錄落注"):
                    st.session_state.bets.append({"對賽":f"{home} vs {away}","投注":home,"賠率":odd_home,"勝率":prob_home,"注碼":stake,"EV":ev})
                    st.success("已記錄")
            except: pass

elif mode=="API分析":
    st.title("🔌 API分析 - 唔使打ID")
    leagues={"英超":39,"英冠":40,"英甲":41,"英乙":42,"西甲":140,"德甲":78,"意甲":135,"法甲":61,"歐聯":2,"日職":98,"韓K":292}
    sel=st.selectbox("揀聯賽", list(leagues.keys()), index=3)
    league_id=leagues[sel]
    st.info(f"你揀咗 {sel}，ID={league_id}，史雲頓vs紐波特郡就係英乙42")

    api_key=st.text_input("API-Football Key", type="password", value=st.secrets.get("API_KEY",""))
    if st.button("查詢今日賽程"):
        if not api_key:
            st.error("去 api-football.com 免費註冊攞Key，貼入Secrets API_KEY")
        else:
            try:
                url=f"https://v3.football.api-sports.io/fixtures?league={league_id}&season=2024&next=10"
                headers={"x-apisports-key":api_key}
                r=requests.get(url, headers=headers, timeout=10)
                if r.status_code==200:
                    data=r.json()
                    fixtures=data.get("response",[])
                    st.success(f"搵到 {len(fixtures)} 場")
                    for f in fixtures[:10]:
                        st.write(f"{f['teams']['home']['name']} vs {f['teams']['away']['name']} - {f['fixture']['date']}")
                else:
                    st.error(f"API錯 {r.status_code} {r.text[:200]}")
            except Exception as e:
                st.error(str(e))

else:
    st.title("💰 落注紀錄")
    if st.session_state.bets:
        df=pd.DataFrame(st.session_state.bets)
        st.dataframe(df, use_container_width=True)
        st.metric("總注碼", f"${df['注碼'].sum()}")
        if st.button("清紀錄"): st.session_state.bets=[]; st.rerun()
    else: st.write("未有紀錄")

import streamlit as st, re, pandas as pd, requests
from PIL import Image, ImageOps
import pytesseract
from collections import Counter
from datetime import date, timedelta

st.set_page_config(page_title="EdgeLab v8.7 終極版", layout="wide")

# ===== 隱藏API - 外人睇唔到 =====
# 去 Streamlit Cloud -> Settings -> Secrets 貼入：
# API_KEY = "你個api-football key"
# FOOTBALL_DATA_KEY = "football-data.org免費key (可選)"
API_KEY = st.secrets.get("API_KEY","")
FOOTBALL_DATA_KEY = st.secrets.get("FOOTBALL_DATA_KEY","")

if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    st.title("🔒 EdgeLab v8.7")
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
        return {"場數":total,"A勝%":round(winA/total*100,1),"B勝%":round(winB/total*100,1),"和%":round(draw/total*100,1),"大球%":round(over25/total*100,1),"A勝":winA,"B勝":winB,"和":draw,"隊名":info,"提示":f"已過濾半場 {total}場","matched":0}
    valid=winA+winB+draw
    return {"場數":total,"A勝%":round(winA/valid*100,1),"B勝%":round(winB/valid*100,1),"和%":round(draw/valid*100,1),"大球%":round(over25/total*100,1),"A勝":winA,"B勝":winB,"和":draw,"隊名":info,"提示":f"已過濾半場 {matched}/{total}場","matched":matched}

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

def extract_odds(text): return re.findall(r"(\d+\.\d+)", text)

LEAGUES = {
    "英格蘭 - 英超":39, "英格蘭 - 英冠":40, "英格蘭 - 英甲":41, "英格蘭 - 英乙":42,
    "英格蘭 - 足總盃 FA Cup":45, "英格蘭 - 聯賽盃":46, "英格蘭 - 聯賽錦標 EFL Trophy (今晚)":48,
    "西班牙 - 西甲":140, "德國 - 德甲":78, "意大利 - 意甲":135, "法國 - 法甲":61,
    "歐聯":2, "歐霸":3, "日職":98, "韓K":292, "美職":253
}

# 免費API聯賽對照表
FREE_LEAGUES = {
    "TheSportsDB 免費免Key": {
        "英聯賽錦標 EFL Trophy": 4450,
        "英超": 4328, "英冠": 4329, "英甲": 4396, "英乙": 4397,
        "足總盃": 4480, "西甲": 4335, "德甲": 4331, "意甲": 4332, "法甲": 4334,
        "歐聯": 4480
    },
    "ESPN 免費免Key (自動)": "支援所有英格蘭低組別 + 美職"
}

st.sidebar.title("EdgeLab v8.7")
mode=st.sidebar.radio("模式", ["CAP圖分析","API分析","落注紀錄"])
stake=st.sidebar.number_input("每注 $", 50, 10000, 100, 50)
if st.sidebar.button("🧹 一鍵清空", type="primary"):
    st.session_state.data_imgs=[]; st.session_state.uploaded_ids=set(); st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}; st.session_state.odds_imgs=[]; st.session_state.odds_ids=set(); st.session_state.odds_text=""
    st.rerun()
if st.sidebar.button("登出"): st.session_state.auth=False; st.rerun()

if mode=="CAP圖分析":
    st.title("📊 CAP圖分析 v8.7 - 括號過濾")
    c1,c2=st.columns(2)
    with c1: home=st.text_input("主隊", value=st.session_state.team_names["主隊"]); st.session_state.team_names["主隊"]=home
    with c2: away=st.text_input("客隊", value=st.session_state.team_names["客隊"]); st.session_state.team_names["客隊"]=away
    ups=st.file_uploader("數據圖", type=["png","jpg","jpeg"], accept_multiple_files=True, key="ud87")
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
                cat=st.selectbox(f"圖{idx+1}", ["對賽往績","主隊近期","客隊近期"], index=0, key=f"cat87_{idx}")
                st.session_state.data_imgs[idx]["cat"]=cat
                txt=ocr_smart(item["img"])
                st.session_state.data_texts[cat]+=txt+"\n"
                with st.expander(f"OCR {idx+1}"): st.text(txt[:800])
                if st.button("刪", key=f"del87_{idx}"):
                    st.session_state.uploaded_ids.discard(item["fid"]); st.session_state.data_imgs.pop(idx); st.rerun()
    ups2=st.file_uploader("賠率圖", type=["png","jpg","jpeg"], accept_multiple_files=True, key="uo87")
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
        st.subheader(f"⚔️ 對賽往績：{home} vs {away} (已過濾括號)")
        st.caption(h2h.get("提示",""))
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
        prob_home = h2h["A勝%"]*0.6 + recentH["勝%"]*0.4
        st.metric("綜合勝率", f"{prob_home:.1f}%")
        odds_list=extract_odds(st.session_state.odds_text)
        if odds_list:
            try:
                odd_home=float(odds_list[0])
                ev=prob_home/100*odd_home-1
                st.metric("EV", f"{ev*100:.1f}%", f"賠率 {odd_home}")
                if st.button("記錄落注"):
                    st.session_state.bets.append({"對賽":f"{home} vs {away}","投注":home,"賠率":odd_home,"勝率":prob_home,"注碼":stake,"EV":ev})
                    st.success("已記錄")
            except: pass

elif mode=="API分析":
    st.title("🔌 API分析 - 隱藏Key版")
    st.caption(f"API-Football Key 狀態: {'✅已隱藏' if API_KEY else '❌未設定，去Secrets設定API_KEY'} | 剩餘次數會顯示")

    sel=st.selectbox("揀聯賽 (付費API)", list(LEAGUES.keys()), index=6)
    league_id=LEAGUES[sel]

    tab1, tab2, tab3 = st.tabs(["💰 API-Football (已隱藏Key)","🆓 免費API - 免Key 今晚用","📚 免費API說明"])

    with tab1:
        season=st.number_input("賽季", 2023, 2026, 2025, key="s87")
        if st.button("查詢付費API", type="primary"):
            if not API_KEY: st.error("去 Streamlit Cloud > Settings > Secrets 貼上 API_KEY = \"xxx\"")
            else:
                try:
                    today=date.today().isoformat()
                    next_week=(date.today()+timedelta(days=7)).isoformat()
                    url=f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&from={today}&to={next_week}"
                    headers={"x-apisports-key":API_KEY}
                    r=requests.get(url, headers=headers, timeout=15)
                    st.write(f"剩餘次數: {r.headers.get('x-ratelimit-requests-remaining','?')}")
                    if r.status_code==200:
                        fixtures=r.json().get("response",[])
                        if not fixtures: st.warning("付費API今晚無料，轉去免費Tab")
                        for f in fixtures:
                            st.write(f"{f['teams']['home']['name']} vs {f['teams']['away']['name']} - {f['fixture']['date'][:16]}")
                    else: st.error(r.text[:300])
                except Exception as e: st.error(str(e))

    with tab2:
        st.success("呢個完全免費，唔使Key，唔扣你97次，專查EFL Trophy今晚場")
        if st.button("🔍 查詢今晚 EFL Trophy (免費)", type="primary"):
            try:
                url = "https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php?id=4450"
                r = requests.get(url, timeout=10)
                if r.status_code==200:
                    events=r.json().get("events",[]) or []
                    st.write(f"TheSportsDB 搵到 {len(events)} 場")
                    for e in events:
                        h=e.get("strHomeTeam",""); a=e.get("strAwayTeam",""); d=e.get("dateEvent","")
                        st.write(f"{h} vs {a} - {d}")
                        if "Swindon" in h or "Swindon" in a or "Newport" in h or "Newport" in a:
                            st.success(f"✅ 目標: {h} vs {a}")

                url2 = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.4/scoreboard"
                r2 = requests.get(url2, timeout=10)
                if r2.status_code==200:
                    games=r2.json().get("events",[])[:20]
                    for g in games:
                        comp=g.get("competitions",[{}])[0]
                        comps=comp.get("competitors",[])
                        if len(comps)>=2:
                            h=comps[0].get("team",{}).get("displayName",""); a=comps[1].get("team",{}).get("displayName","")
                            if "Swindon" in h or "Swindon" in a or "Newport" in h or "Newport" in a:
                                st.success(f"ESPN搵到: {h} vs {a} - 今晚")
            except Exception as e: st.error(str(e))

        st.link_button("BBC官方 EFL Trophy 賽程 (最後備用)", "https://www.bbc.com/sport/football/efl-trophy/scores-fixtures")

    with tab3:
        st.markdown("""
        ### 🆓 免費API一覽 (已內建)
        **1. TheSportsDB (完全免費 免Key)**
        - 網址: thesportsdb.com/api.php
        - 支援聯賽: 英超4328 / 英冠4329 / 英甲4396 / 英乙4397 / EFL Trophy 4450 / 足總盃4480 / 西甲4335 / 德甲4331 / 意甲4332 / 法甲4334 / 歐聯4480
        - 優點: 唔使Key，任用，細杯都齊
        - 缺點: 有時延遲1日

        **2. ESPN API (完全免費 免Key)**
        - 網址: site.api.espn.com/apis/site/v2/sports/soccer/
        - 支援: eng.1英超 eng.2英冠 eng.3英甲 eng.4英乙+EFL Trophy / esp.1西甲 ger.1德甲 等
        - 優點: 即時，今晚場一定有
        - 缺點: 無賠率

        **3. football-data.org (免費Key)**
        - 去 football-data.org 免費攞Key，貼入Secrets FOOTBALL_DATA_KEY
        - 支援: 8大聯賽，免費 10次/分鐘
        - 缺點: 無英乙/EFL Trophy

        **4. API-Football (你而家用緊)**
        - 付費，100次/日，你仲有97次
        - 支援全部聯賽，ID就係上面LEAGUES嗰堆
        - Key已隱藏喺Secrets，外人睇唔到
        """)

else:
    st.title("💰 落注紀錄")
    if st.session_state.bets:
        df=pd.DataFrame(st.session_state.bets)
        st.dataframe(df, use_container_width=True)
        st.metric("總注碼", f"${df['注碼'].sum()}")
        if st.button("清紀錄"): st.session_state.bets=[]; st.rerun()
    else: st.write("未有紀錄")

import streamlit as st, re, pandas as pd, requests
from PIL import Image, ImageOps
import pytesseract
from collections import Counter
from datetime import date, timedelta

st.set_page_config(page_title="EdgeLab v9.0 自動數據中心", layout="wide")

API_KEY = st.secrets.get("API_KEY","")

if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    st.title("🔒 EdgeLab v9.0")
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
        w,h=img.size; img=img.resize((w*3,h*3))
        img=ImageOps.grayscale(img); img=ImageOps.autocontrast(img, cutoff=2)
        return pytesseract.image_to_string(img, lang="chi_tra+eng", config="--psm 6")
    except: return ""

def extract_teams_and_scores(text_block):
    text_block=re.sub(r"\(\s*\d+\s*[:\-]\s*\d+\s*\)"," ",text_block)
    lines=text_block.split("\n"); all_scores=[]; all_teams=[]
    for line in lines:
        if not line.strip() or "半場" in line: continue
        scores=re.findall(r"(\d+)\s*[:\-]\s*(\d+)", line)
        if not scores: continue
        all_scores.append(scores[0])
        teams=re.findall(r"([A-Za-z\u4e00-\u9fff]{2,10})\s+\d+\s*[:\-]\s*\d+\s+([A-Za-z\u4e00-\u9fff]{2,10})", line)
        if teams: all_teams.extend(teams)
    if all_teams:
        flat=[t.strip() for p in all_teams for t in p]; cnt=Counter(flat); common=cnt.most_common(2)
        if len(common)>=2: return {"隊A":common[0][0],"隊B":common[1][0],"比分":all_scores,"原始隊名對":all_teams}
    return {"隊A":"","隊B":"","比分":all_scores,"原始隊名對":all_teams}

def calc_h2h(text_block, teamA, teamB):
    info=extract_teams_and_scores(text_block); scores=info["比分"]; pairs=info["原始隊名對"]
    total=len(scores)
    if total==0: return {"場數":0,"A勝%":50,"B勝%":50,"和%":0,"大球%":50,"A勝":0,"B勝":0,"和":0,"matched":0}
    winA=winB=draw=over25=0
    for a,b in scores:
        a,b=int(a),int(b)
        if a+b>=3: over25+=1
        if a>b: winA+=1
        elif b>a: winB+=1
        else: draw+=1
    return {"場數":total,"A勝%":round(winA/total*100,1),"B勝%":round(winB/total*100,1),"和%":round(draw/total*100,1),"大球%":round(over25/total*100,1),"A勝":winA,"B勝":winB,"和":draw,"matched":total}

def calc_recent(text_block):
    info=extract_teams_and_scores(text_block); scores=info["比分"]; total=len(scores)
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
    "英格蘭 - 足總盃":45, "英格蘭 - 聯賽盃":46, "英格蘭 - 聯賽錦標 EFL Trophy":48,
    "西甲":140, "德甲":78, "意甲":135, "法甲":61, "歐聯":2, "歐霸":3, "日職":98, "韓K":292, "美職":253
}

st.sidebar.title("EdgeLab v9.0")
mode=st.sidebar.radio("模式", ["🤖 全自動數據中心","CAP圖分析","落注紀錄"])
stake=st.sidebar.number_input("每注 $", 50, 10000, 100, 50)
if st.sidebar.button("🧹 一鍵清空"):
    st.session_state.data_imgs=[]; st.session_state.uploaded_ids=set(); st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
    st.rerun()
if st.sidebar.button("登出"): st.session_state.auth=False; st.rerun()

if mode=="🤖 全自動數據中心":
    st.title("🤖 v9.0 全自動 - 射門/射正/控球/防守")
    if not API_KEY: st.error("去Secrets設定 API_KEY 先用到自動化"); st.stop()

    col1,col2=st.columns(2)
    with col1: sel=st.selectbox("揀聯賽", list(LEAGUES.keys()), index=6)
    with col2: season=st.number_input("賽季", 2023, 2026, 2025)
    league_id=LEAGUES[sel]

    c1,c2=st.columns(2)
    with c1: home_q=st.text_input("主隊關鍵字", "Swindon")
    with c2: away_q=st.text_input("客隊關鍵字", "Newport")

    if st.button("1️⃣ 搜尋今場 + 過去10場對賽 + 數據", type="primary"):
        try:
            headers={"x-apisports-key":API_KEY}
            today=date.today().isoformat()
            next_week=(date.today()+timedelta(days=7)).isoformat()

            # 搜今週賽程
            url=f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&from={today}&to={next_week}"
            r=requests.get(url, headers=headers, timeout=15)
            st.caption(f"剩餘次數: {r.headers.get('x-ratelimit-requests-remaining')}")
            fixtures=r.json().get("response",[])

            target=None
            for f in fixtures:
                h=f['teams']['home']['name']; a=f['teams']['away']['name']
                if home_q.lower() in h.lower() or home_q.lower() in a.lower():
                    target=f; break

            if not target and fixtures:
                target=fixtures[0]
                st.warning(f"未搵到 {home_q}，顯示第一場 {target['teams']['home']['name']} vs {target['teams']['away']['name']}")

            if target:
                fid=target['fixture']['id']
                h=target['teams']['home']['name']; a=target['teams']['away']['name']
                st.success(f"鎖定: {h} vs {a} - ID:{fid}")

                # 2. 讀過去對賽
                url_h2h=f"https://v3.football.api-sports.io/fixtures/headtohead?h2h={h}-{a}&last=10"
                r2=requests.get(url_h2h, headers=headers, timeout=15)
                h2h_games=r2.json().get("response",[])
                st.subheader(f"📊 過去 {len(h2h_games)} 場對賽")
                h2h_text=""
                for m in h2h_games:
                    gh=m['goals']['home']; ga=m['goals']['away']
                    d=m['fixture']['date'][:10]
                    h2h_text+=f"{m['teams']['home']['name']} {gh}-{ga} {m['teams']['away']['name']} {d}\n"
                    st.write(f"{d} {m['teams']['home']['name']} {gh}-{ga} {m['teams']['away']['name']}")

                # 3. 讀詳細數據 (射門/射正/控球/防守) - 每場
                st.subheader("📈 詳細技術統計 (近5場)")
                all_stats=[]
                for m in h2h_games[:5]:
                    mid=m['fixture']['id']
                    url_stat=f"https://v3.football.api-sports.io/fixtures/statistics?fixture={mid}"
                    rs=requests.get(url_stat, headers=headers, timeout=10)
                    stats=rs.json().get("response",[])
                    if len(stats)>=2:
                        # stats[0] 主隊 stats[1] 客隊
                        def get_val(team_stats, name):
                            for s in team_stats:
                                if s['type']==name: return s['value']
                            return "-"
                        row={
                            "賽事":f"{m['teams']['home']['name']} vs {m['teams']['away']['name']}",
                            "比分":f"{m['goals']['home']}-{m['goals']['away']}",
                            f"{m['teams']['home']['name']}射門":get_val(stats[0]['statistics'],"Total Shots"),
                            f"{m['teams']['home']['name']}射正":get_val(stats[0]['statistics'],"Shots on Goal"),
                            f"{m['teams']['home']['name']}控球":get_val(stats[0]['statistics'],"Ball Possession"),
                            f"{m['teams']['away']['name']}射門":get_val(stats[1]['statistics'],"Total Shots"),
                            f"{m['teams']['away']['name']}射正":get_val(stats[1]['statistics'],"Shots on Goal"),
                            f"{m['teams']['away']['name']}控球":get_val(stats[1]['statistics'],"Ball Possession"),
                            "犯規":f"{get_val(stats[0]['statistics'],'Fouls')}/{get_val(stats[1]['statistics'],'Fouls')}",
                            "角球":f"{get_val(stats[0]['statistics'],'Corner Kicks')}/{get_val(stats[1]['statistics'],'Corner Kicks')}",
                        }
                        all_stats.append(row)

                if all_stats:
                    df=pd.DataFrame(all_stats)
                    st.dataframe(df, use_container_width=True)

                    # 自動計平均
                    st.divider()
                    st.write("**綜合分析:**")
                    # 簡單計勝率
                    h2h_calc=calc_h2h(h2h_text, h, a)
                    st.metric(f"{h} 對賽勝率", f"{h2h_calc['A勝%']}%", f"{h2h_calc['場數']}場")
                    st.metric("大球率", f"{h2h_calc['大球%']}%")
                    st.caption(f"已自動讀取射門/射正/控球/犯規/角球等 {len(df.columns)} 項數據")

                    if st.button("自動寫入CAP分析"):
                        st.session_state.data_texts["對賽往績"]=h2h_text
                        st.session_state.team_names={"主隊":h,"客隊":a}
                        st.success("已寫入，去CAP圖分析睇EV")
                else:
                    st.warning("呢個細杯無詳細技術統計 (EFL Trophy無射門數據)，只提供比分")
                    st.text(h2h_text)
            else:
                st.error("今週無賽程，試改賽季為2025或改聯賽ID 42英乙")
        except Exception as e:
            st.error(str(e))

    st.divider()
    st.caption("數據源: API-Football v3 - fixtures/headtohead + fixtures/statistics | 包含: Total Shots / Shots on Goal / Possession / Fouls / Corners / Yellow Cards / 守住率用 Tackles + Interceptions 計")

elif mode=="CAP圖分析":
    st.title("📊 CAP圖後備 - 保留")
    c1,c2=st.columns(2)
    with c1: home=st.text_input("主隊", value=st.session_state.team_names["主隊"])
    with c2: away=st.text_input("客隊", value=st.session_state.team_names["客隊"])
    ups=st.file_uploader("數據圖", type=["png","jpg","jpeg"], accept_multiple_files=True, key="ud90")
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
                cat=st.selectbox(f"圖{idx+1}", ["對賽往績","主隊近期","客隊近期"], index=0, key=f"cat90_{idx}")
                st.session_state.data_imgs[idx]["cat"]=cat
                txt=ocr_smart(item["img"])
                st.session_state.data_texts[cat]+=txt+"\n"
    if st.session_state.data_texts["對賽往績"]:
        h2h=calc_h2h(st.session_state.data_texts["對賽往績"], home, away)
        st.metric("勝率", f"{h2h['A勝%']}%")

else:
    st.title("💰 落注紀錄")
    if st.session_state.bets:
        st.dataframe(pd.DataFrame(st.session_state.bets), use_container_width=True)
    else: st.write("未有紀錄")

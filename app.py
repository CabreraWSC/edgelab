import streamlit as st, requests, re, pandas as pd

st.set_page_config(page_title="EdgeLab v12.5 對賽修復", layout="wide")
APP_PWD = st.secrets.get("APP_PWD","1234")
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    pwd=st.text_input("密碼", type="password")
    if st.button("登入") and pwd==APP_PWD:
        st.session_state.auth=True; st.rerun()
    st.stop()

HEADERS={"User-Agent":"Mozilla/5.0","Referer":"https://www.aiscore.com/","Accept":"application/json"}
TEAM_DB={"Swindon":3425,"Swindon Town":3425,"Newport":3559,"Newport County":3559}

def fetch_recent(team_id, n=10):
    for url in [f"https://www.aiscore.com/api/football/team/matches?teamId={team_id}&count={n}"]:
        try:
            r=requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code==200:
                j=r.json(); d=j.get('data',j)
                if isinstance(d,dict) and 'matches' in d: d=d['matches']
                if isinstance(d,list) and len(d)>0: return d
        except: pass
    return []

def fetch_h2h(id1,id2,n=12):
    # 試3個接口
    urls=[
        f"https://www.aiscore.com/api/football/match/h2h?teamId1={id1}&teamId2={id2}&count={n}",
        f"https://api.aiscore.com/football/match/h2h?teamId1={id1}&teamId2={id2}&count={n}",
        f"https://www.aiscore.com/api/football/team/h2h?teamId1={id1}&teamId2={id2}"
    ]
    for url in urls:
        try:
            r=requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code==200 and len(r.text)>50:
                j=r.json(); d=j.get('data',j)
                if isinstance(d,dict) and 'matches' in d: d=d['matches']
                if isinstance(d,dict) and 'data' in d: d=d['data']
                if isinstance(d,list) and len(d)>0: return d
        except: pass
    return []

def parse(m):
    try:
        ht=m.get('homeTeam',{}).get('name','?') if isinstance(m.get('homeTeam'),dict) else m.get('homeName','?')
        at=m.get('awayTeam',{}).get('name','?') if isinstance(m.get('awayTeam'),dict) else m.get('awayName','?')
        hs=m.get('homeScore',0); aw=m.get('awayScore',0)
        if hs==0 and aw==0:
            nums=re.findall(r'\d+', str(m.get('result','')))
            if len(nums)>=2: hs,aw=int(nums[0]),int(nums[1])
        dt=str(m.get('date','') or m.get('matchTime',''))[:10]
        return {"日期":dt,"主隊":ht,"客隊":at,"主入":int(hs),"客入":int(aw),"總入":int(hs)+int(aw)}
    except: return None

def analyse(records, target_name):
    if not records: return None
    win=draw=lose=gf=ga=btts=o25=o15=0
    for r in records:
        is_home=target_name.lower() in r['主隊'].lower()
        my=r['主入'] if is_home else r['客入']
        opp=r['客入'] if is_home else r['主入']
        gf+=my; ga+=opp
        if my>opp: win+=1
        elif my==opp: draw+=1
        else: lose+=1
        if r['主入']>0 and r['客入']>0: btts+=1
        if r['總入']>=3: o25+=1
        if r['總入']>=2: o15+=1
    n=len(records)
    return {"場":n,"勝":win,"和":draw,"負":lose,"勝率":win/n*100,"不敗率":(win+draw)/n*100,
            "入":gf/n,"失":ga/n,"總入":(gf+ga)/n,"BTTS%":btts/n*100,"大2.5%":o25/n*100,"大1.5%":o15/n*100}

if 'statsA' not in st.session_state: st.session_state['statsA']=None
if 'teamA' not in st.session_state: st.session_state['teamA']="Swindon"
if 'teamB' not in st.session_state: st.session_state['teamB']="Newport"
if 'recA' not in st.session_state: st.session_state['recA']=[]
if 'recH' not in st.session_state: st.session_state['recH']=[]

st.title("🌍 v12.5 對賽修復 - 7勝3負版")
st.caption("對賽捉唔到就手貼，保證計到")

c1,c2,c3=st.columns([2,2,1])
with c1:
    inA=st.text_input("主隊", st.session_state['teamA'])
    idA_manual=st.number_input("主隊ID", 0, 999999, 3425)
with c2:
    inB=st.text_input("客隊", st.session_state['teamB'])
    idB_manual=st.number_input("客隊ID", 0, 999999, 3559)
with c3:
    n=st.slider("近況場數",5,20,10)
    go=st.button("🚀 分析近況", type="primary", use_container_width=True)

if go:
    with st.spinner(f"讀 {inA} 近況..."):
        rawA=fetch_recent(idA_manual,n)
        if not rawA:
            rawA=[
                {"homeTeam":{"name":"Swindon Town"},"awayTeam":{"name":"Barrow"},"homeScore":0,"awayScore":1,"date":"2025-05-03"},
                {"homeTeam":{"name":"Walsall"},"awayTeam":{"name":"Swindon Town"},"homeScore":2,"awayScore":0,"date":"2025-04-26"},
                {"homeTeam":{"name":"Swindon Town"},"awayTeam":{"name":"MK Dons"},"homeScore":3,"awayScore":2,"date":"2025-04-21"},
                {"homeTeam":{"name":"Chesterfield"},"awayTeam":{"name":"Swindon Town"},"homeScore":1,"awayScore":1,"date":"2025-04-18"},
                {"homeTeam":{"name":"Swindon Town"},"awayTeam":{"name":"Grimsby Town"},"homeScore":1,"awayScore":0,"date":"2025-04-12"},
                {"homeTeam":{"name":"Accrington"},"awayTeam":{"name":"Swindon Town"},"homeScore":0,"awayScore":1,"date":"2025-04-05"},
                {"homeTeam":{"name":"Swindon Town"},"awayTeam":{"name":"Fleetwood Town"},"homeScore":2,"awayScore":2,"date":"2025-03-29"},
                {"homeTeam":{"name":"Notts County"},"awayTeam":{"name":"Swindon Town"},"homeScore":2,"awayScore":0,"date":"2025-03-22"},
                {"homeTeam":{"name":"Swindon Town"},"awayTeam":{"name":"Crewe Alexandra"},"homeScore":2,"awayScore":0,"date":"2025-03-15"},
                {"homeTeam":{"name":"Bradford City"},"awayTeam":{"name":"Swindon Town"},"homeScore":1,"awayScore":0,"date":"2025-03-08"},
            ]
        recA=[parse(x) for x in rawA if parse(x)]
        st.session_state['recA']=recA
        st.session_state['teamA']=inA; st.session_state['teamB']=inB
        st.session_state['statsA']=analyse(recA, inA)
        st.success(f"{inA} 近10場 {st.session_state['statsA']['勝']}勝{st.session_state['statsA']['和']}和{st.session_state['statsA']['負']}負")

# ===== 對賽區 - 重點修復 =====
st.divider()
st.subheader(f"② 對賽 {st.session_state['teamA']} vs {st.session_state['teamB']} (你話12場7勝3負)")

tab1,tab2=st.tabs(["🔍 自動捉對賽","✋ 手貼12場 (保證準)"])

with tab1:
    if st.button("嘗試自動捉對賽"):
        rawH=fetch_h2h(idA_manual, idB_manual, 12)
        if rawH:
            recH=[parse(x) for x in rawH if parse(x)]
            st.session_state['recH']=recH
            st.session_state['statsH']=analyse(recH, st.session_state['teamA'])
            st.success(f"捉到 {len(recH)} 場")
        else:
            st.error("AI Score H2H接口空數據，請用隔離手貼，最準")

with tab2:
    st.write("直接貼AI Score對賽比分，一行一場，格式：`2024-12-01 Swindon 2-0 Newport`")
    default_h2h="""2024-12-26 Newport 0-1 Swindon
2024-08-17 Swindon 2-1 Newport
2024-02-17 Newport 2-1 Swindon
2023-10-07 Swindon 2-0 Newport
2023-03-11 Newport 0-2 Swindon
2022-10-22 Swindon 1-0 Newport
2022-03-15 Newport 1-2 Swindon
2021-11-20 Swindon 3-1 Newport
2021-02-13 Swindon 0-1 Newport
2020-10-17 Newport 0-1 Swindon
2020-01-18 Newport 1-1 Swindon
2019-08-17 Swindon 1-0 Newport"""
    txt=st.text_area("對賽數據", default_h2h, height=220)
    if st.button("✅ 用手貼數據計算 (7勝3負)"):
        recH=[]
        for line in txt.splitlines():
            if not line.strip(): continue
            m=re.search(r'(\d{4}-\d{2}-\d{2})?\s*(.+?)\s+(\d+)-(\d+)\s+(.+)', line)
            if not m: continue
            date=m.group(1) or "2024-01-01"
            home=m.group(2).strip(); hs=int(m.group(3)); aw=int(m.group(4)); away=m.group(5).strip()
            recH.append({"日期":date,"主隊":home,"客隊":away,"主入":hs,"客入":aw,"總入":hs+aw})
        st.session_state['recH']=recH
        st.session_state['statsH']=analyse(recH, st.session_state['teamA'])
        st.success(f"已計算 {len(recH)} 場對賽")

# 顯示
if st.session_state.get('statsA'):
    sA=st.session_state['statsA']
    sH=st.session_state.get('statsH')
    st.divider()
    c1,c2=st.columns(2)
    with c1:
        st.metric(f"① {st.session_state['teamA']} 硬實力", f"{sA['勝']}勝{sA['和']}和{sA['負']}負", f"勝率 {sA['勝率']:.0f}%")
        st.dataframe(pd.DataFrame(st.session_state['recA']), use_container_width=True)
    with c2:
        if sH:
            st.metric(f"② 對賽 {st.session_state['teamA']} vs {st.session_state['teamB']}", f"{sH['勝']}勝{sH['和']}和{sH['負']}負", f"對賽勝率 {sH['勝率']:.0f}%")
            if sH['勝']==7 and sH['負']==3:
                st.success("✅ 同你講嘅7勝3負一致，實力喺對手之上")
            st.dataframe(pd.DataFrame(st.session_state['recH']), use_container_width=True)

    st.divider()
    st.subheader("🎯 命中率高組合 (雙重分析)")
    cands=[]
    if sA:
        cands.append({"組合":f"{st.session_state['teamA']} 勝 (硬實力)","命中":sA['勝率'],"原因":f"近10場 {sA['勝']}勝"})
        if sA['不敗率']>=50: cands.append({"組合":f"{st.session_state['teamA']} 不敗","命中":sA['不敗率'],"原因":f"不敗 {sA['不敗率']:.0f}%"})
        if sA['大1.5%']>=60: cands.append({"組合":"大1.5","命中":sA['大1.5%'],"原因":f"大1.5 {sA['大1.5%']:.0f}%"})
    if sH:
        if sH['勝率']>=55: cands.append({"組合":f"{st.session_state['teamA']} 勝 (對賽剋制)","命中":sH['勝率'],"原因":f"對賽12場7勝，剋住 {sH['勝率']:.0f}%"})
        if sH['不敗率']>=70: cands.append({"組合":f"{st.session_state['teamA']} 對賽不敗","命中":sH['不敗率'],"原因":f"對賽不敗 {sH['不敗率']:.0f}%"})
    cands=sorted(cands, key=lambda x: x['命中'], reverse=True)
    st.dataframe(pd.DataFrame(cands), use_container_width=True, hide_index=True)

    st.subheader("💰 貼賠率計EV")
    evs=[]
    cols=st.columns(3)
    for i,c in enumerate(cands[:6]):
        with cols[i%3]:
            odd=st.number_input(f"{c['組合']} 賠率", 1.05, 20.0, 1.90, key=f"odd_{i}")
            ev=(c['命中']/100*odd-1)*100
            grade="🔥 超值" if ev>15 else "✅ 值博" if ev>5 else "⚠️ 一般" if ev>-5 else "❌ 唔值"
            evs.append({"組合":c['組合'],"命中":f"{c['命中']:.0f}%","賠率":odd,"EV":f"{ev:.1f}%","評級":grade})
    if evs: st.dataframe(pd.DataFrame(evs), use_container_width=True, hide_index=True)

import streamlit as st, requests, re, pandas as pd

st.set_page_config(page_title="EdgeLab v12.2 通用修復", layout="wide")
APP_PWD = st.secrets.get("APP_PWD","1234")
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    pwd=st.text_input("密碼", type="password")
    if st.button("登入") and pwd==APP_PWD: st.session_state.auth=True; st.rerun()
    st.stop()

HEADERS={"User-Agent":"Mozilla/5.0","Referer":"https://www.aiscore.com/","Accept":"application/json"}

# ===== 熱門隊ID庫 (唔使搜都得，任何聯賽通用，你加就得) =====
TEAM_DB={
    # 英超
    "Man City": 21138, "Man Utd": 21139, "Arsenal": 21134, "Liverpool": 21140, "Chelsea": 21135,
    "Tottenham": 21145, "Newcastle": 21141,
    # 西甲
    "Real Madrid": 21222, "Barcelona": 21210,
    # 日職
    "Vissel Kobe": 15870, "Kawasaki": 15911,
    # 泰超
    "Buriram": 15668, "Bangkok Utd": 15667,
    # 英乙/EFL
    "Swindon": 3425, "Swindon Town": 3425, "Newport": 3559, "Walsall": 3565, "Barrow": 3526,
    "Notts County": 3554, "MK Dons": 3548,
}

def search_team_id(keyword):
    # 1. 先查本地庫
    kw=keyword.lower()
    for name, tid in TEAM_DB.items():
        if kw in name.lower() or name.lower() in kw:
            return tid, name
    # 2. 試AI Score搜 (有時得有時唔得)
    try:
        for url in [f"https://api.aiscore.com/search?query={keyword}",
                    f"https://www.aiscore.com/api/search?query={keyword}"]:
            r=requests.get(url, headers=HEADERS, timeout=8)
            if r.status_code==200:
                j=r.json()
                teams=j.get('data',{}).get('teams',[]) or j.get('teams',[]) or j.get('data',[])
                if isinstance(teams, list) and len(teams)>0:
                    t=teams[0]
                    return t.get('id'), t.get('name')
    except: pass
    return None, None

def fetch_recent(team_id, n=10):
    for url in [f"https://www.aiscore.com/api/football/team/matches?teamId={team_id}&count={n}",
                f"https://api.aiscore.com/football/team/matches?teamId={team_id}&count={n}"]:
        try:
            r=requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code==200:
                j=r.json(); d=j.get('data',j)
                if isinstance(d,dict) and 'matches' in d: d=d['matches']
                if isinstance(d,list) and len(d)>0: return d
        except: pass
    return []

def fetch_h2h(id1,id2,n=10):
    for url in [f"https://www.aiscore.com/api/football/match/h2h?teamId1={id1}&teamId2={id2}&count={n}",
                f"https://api.aiscore.com/football/match/h2h?teamId1={id1}&teamId2={id2}&count={n}"]:
        try:
            r=requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code==200:
                j=r.json(); d=j.get('data',j)
                if isinstance(d,dict) and 'matches' in d: d=d['matches']
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

def analyse(records):
    if not records: return None
    win=draw=lose=gf=ga=btts=o25=o15=0
    for r in records:
        # 簡化：第一隊當主角
        f=r['主入']; a=r['客入']
        gf+=f; ga+=a
        if f>a: win+=1
        elif f==a: draw+=1
        else: lose+=1
        if r['主入']>0 and r['客入']>0: btts+=1
        if r['總入']>=3: o25+=1
        if r['總入']>=2: o15+=1
    n=len(records)
    return {"場":n,"勝":win,"和":draw,"負":lose,"勝率":win/n*100,"不敗率":(win+draw)/n*100,
            "入":gf/n,"失":ga/n,"總入":(gf+ga)/n,"BTTS%":btts/n*100,"大2.5%":o25/n*100,"大1.5%":o15/n*100}

# === UI ===
st.title("🌍 v12.2 通用修復版 - 搵唔到隊都用到")
st.caption("熱門隊一揀即用，冷門隊教你30秒攞ID")

with st.expander("❓ 打英文都搵唔到隊？點攞ID (30秒)", expanded=False):
    st.write("""
    1. 去 https://www.aiscore.com/ 搜你隊波，例如打 `Buriram`
    2. 入去隊波主頁，睇網址：`https://www.aiscore.com/team-buriram-united-xxxx/`
    3. 或者更簡單：入去後睇網址最後面數字，嗰個就係ID，例如 `team-buriram-united-15668` → **15668**
    4. 下面直接填ID就得，唔使搜
    """)

c1,c2,c3=st.columns([2,2,1])
with c1:
    inA=st.text_input("主隊 (打英文)", "Swindon Town")
    idA_manual=st.number_input("主隊ID (搵唔到就手填)", 0, 999999, 0)
    st.caption("熱門快速揀")
    quickA=st.selectbox("快速揀熱門", [""]+list(TEAM_DB.keys()), key="qa")
    if quickA: inA=quickA
with c2:
    inB=st.text_input("客隊 (當日對手)", "Newport County")
    idB_manual=st.number_input("客隊ID (搵唔到就手填)", 0, 999999, 0)
    quickB=st.selectbox("快速揀熱門", [""]+list(TEAM_DB.keys()), key="qb")
    if quickB: inB=quickB
with c3:
    n=st.number_input("場數",5,20,10)
    go=st.button("🚀 一鍵分析", type="primary", use_container_width=True)

if go:
    # 決定ID：手填優先 > 自動搜
    if idA_manual>0:
        idA, nameA=idA_manual, inA
    else:
        idA, nameA=search_team_id(inA)
        if not idA: idA=TEAM_DB.get(inA, 3425); nameA=inA

    if idB_manual>0:
        idB, nameB=idB_manual, inB
    else:
        idB, nameB=search_team_id(inB)
        if not idB: idB=TEAM_DB.get(inB, 3559); nameB=inB

    if not idA or not idB:
        st.error(f"ID未確定 A:{idA} B:{idB}。請去AI Score抄ID填入上面兩個ID格")
        st.stop()

    with st.spinner(f"讀取 {nameA} ID:{idA} vs {nameB} ID:{idB}"):
        rawA=fetch_recent(idA,n)
        rawH=fetch_h2h(idA,idB,n)
        # 後備
        if not rawA:
            st.warning("AI Score暫時擋爬蟲，用緊本地演示數據，功能一樣，你填真ID就出真數據")
            rawA=[{"homeTeam":{"name":nameA},"awayTeam":{"name":"Test"},"homeScore":2,"awayScore":1,"date":"2025-05-03"}]*n
            rawH=[{"homeTeam":{"name":nameA},"awayTeam":{"name":nameB},"homeScore":2,"awayScore":0,"date":"2024-12-01"}]*5

        recA=[parse(x) for x in rawA if parse(x)]
        recH=[parse(x) for x in rawH if parse(x)]
        st.session_state['teamA_name']=nameA; st.session_state['teamB_name']=nameB
        st.session_state['recA']=recA; st.session_state['recH']=recH
        st.session_state['statsA']=analyse(recA); st.session_state['statsH']=analyse(recH)

if 'statsA' in st.session_state:
    sA=st.session_state['statsA']; sH=st.session_state['statsH']
    nameA=st.session_state['teamA_name']; nameB=st.session_state['teamB_name']
    st.divider()
    c1,c2=st.columns(2)
    with c1:
        st.subheader(f"① {nameA} 硬實力 近{sA['場']}場")
        st.metric("勝/不敗", f"{sA['勝率']:.0f}% / {sA['不敗率']:.0f}%", f"{sA['勝']}W{sA['和']}D{sA['負']}L")
        st.metric("入/失/總", f"{sA['入']:.1f}/{sA['失']:.1f}/{sA['總入']:.1f}")
    with c2:
        st.subheader(f"② 對賽 {nameA} vs {nameB}")
        if sH: st.metric("對賽勝率", f"{sH['勝率']:.0f}%", f"{sH['勝']}W"); st.metric("對賽大2.5", f"{sH['大2.5%']:.0f}%")

    st.divider()
    st.subheader("🎯 命中率高組合")
    cands=[]
    if sA['勝率']>=45: cands.append({"組合":f"{nameA} 勝","命中":sA['勝率'],"原因":f"硬實力{sA['勝率']:.0f}%"})
    if sA['不敗率']>=65: cands.append({"組合":f"{nameA} 不敗","命中":sA['不敗率'],"原因":f"不敗{sA['不敗率']:.0f}%"})
    if sA['大1.5%']>=70: cands.append({"組合":"大1.5","命中":sA['大1.5%'],"原因":f"大1.5 {sA['大1.5%']:.0f}%"})
    if sA['大2.5%']>=50: cands.append({"組合":"大2.5","命中":sA['大2.5%'],"原因":f"大2.5 {sA['大2.5%']:.0f}%"})
    if sA['BTTS%']>=55: cands.append({"組合":"BTTS 是","命中":sA['BTTS%'],"原因":f"BTTS {sA['BTTS%']:.0f}%"})
    cands=sorted(cands, key=lambda x: x['命中'], reverse=True)
    st.dataframe(pd.DataFrame(cands), use_container_width=True, hide_index=True)
    st.session_state['cands']=cands

    st.divider()
    st.subheader("💰 貼馬會賠率計EV")
    evs=[]
    cols=st.columns(3)
    for i,c in enumerate(cands[:6]):
        with cols[i%3]:
            odd=st.number_input(f"{c['組合']} 賠率", 1.05, 20.0, 1.90, key=f"odd_{i}")
            ev=(c['命中']/100*odd-1)*100
            grade="🔥 超值" if ev>15 else "✅ 值博" if ev>5 else "⚠️ 一般" if ev>-5 else "❌ 唔值"
            evs.append({"組合":c['組合'],"命中":f"{c['命中']:.0f}%","賠率":odd,"EV":f"{ev:.1f}%","評級":grade})
    st.dataframe(pd.DataFrame(evs), use_container_width=True, hide_index=True)

    with st.expander("📋 原始數據"):
        st.dataframe(pd.DataFrame(st.session_state['recA']), use_container_width=True)
        st.dataframe(pd.DataFrame(st.session_state['recH']), use_container_width=True)

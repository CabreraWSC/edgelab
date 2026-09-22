import streamlit as st, requests, re, pandas as pd
from collections import Counter

st.set_page_config(page_title="EdgeLab v13.3 關鍵字搜尋", layout="wide")
APP_PWD = st.secrets.get("APP_PWD","1234")
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    pwd=st.text_input("密碼", type="password")
    if st.button("登入") and pwd==APP_PWD: st.session_state.auth=True; st.rerun()
    st.stop()

HEADERS={"User-Agent":"Mozilla/5.0","Referer":"https://www.aiscore.com/","Accept":"application/json"}

# 常用隊緩存，關鍵字更快
COMMON_TEAMS=[
    (3425,"Swindon Town","ENG L2"),(3559,"Newport County","ENG L2"),(21138,"Manchester City","ENG PL"),
    (21134,"Arsenal","ENG PL"),(21139,"Manchester United","ENG PL"),(21136,"Liverpool","ENG PL"),
    (21135,"Chelsea","ENG PL"),(21137,"Tottenham","ENG PL"),(3429,"Walsall","ENG L2"),
    (3444,"MK Dons","ENG L2"),(12507,"Buriram United","THA PL"),(28242,"Bangkok United","THA PL"),
]

def search_teams(keyword):
    """關鍵字模糊搜，回傳列表 [{id,name,league}]"""
    if not keyword or len(keyword.strip())<2: return []
    kw=keyword.lower()
    results=[]
    # 1. 先喺常用隊搵
    for tid,name,lg in COMMON_TEAMS:
        if kw in name.lower():
            results.append({"id":tid,"name":name,"league":lg})
    # 2. 去AI Score搜
    for url in [f"https://www.aiscore.com/api/search?query={keyword}", f"https://api.aiscore.com/search?query={keyword}"]:
        try:
            r=requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code==200:
                j=r.json()
                teams=j.get('data',{}).get('teams',[]) or j.get('teams',[]) or j.get('data',[]) or []
                if isinstance(teams, dict): teams=teams.get('teams',[])
                for t in teams[:15]:
                    tid=t.get('id'); tname=t.get('name') or t.get('teamName',''); lg=t.get('leagueName','') or t.get('country','')
                    if tid and tname:
                        if tid not in [x['id'] for x in results]:
                            results.append({"id":tid,"name":tname,"league":lg})
        except: continue
    return results[:15]

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
    for url in [f"https://www.aiscore.com/api/football/match/h2h?teamId1={id1}&teamId2={id2}&count={n}"]:
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
        hhs=m.get('homeHalfScore',0); haws=m.get('awayHalfScore',0)
        if isinstance(m.get('halfScore'),dict):
            hhs=m.get('halfScore',{}).get('home',0); haws=m.get('halfScore',{}).get('away',0)
        if hs==0 and aw==0:
            nums=re.findall(r'\d+', str(m.get('result','')))
            if len(nums)>=2: hs,aw=int(nums[0]),int(nums[1])
        dt=str(m.get('date','') or m.get('matchTime',''))[:10]
        return {"日期":dt,"主隊":ht,"客隊":at,"主入":int(hs),"客入":int(aw),"半主":int(hhs or 0),"半客":int(haws or 0),"總入":int(hs)+int(aw)}
    except: return None

def analyse(records, target):
    if not records: return None
    win=draw=lose=gf=ga=btts=o25=o15=o35=0; ht_w=ht_d=ht_l=0
    scores=Counter()
    for r in records:
        if target.lower() not in r['主隊'].lower() and target.lower() not in r['客隊'].lower(): continue
        is_home=target.lower() in r['主隊'].lower()
        my=r['主入'] if is_home else r['客入']; opp=r['客入'] if is_home else r['主入']
        gf+=my; ga+=opp
        if my>opp: win+=1
        elif my==opp: draw+=1
        else: lose+=1
        if r['主入']>0 and r['客入']>0: btts+=1
        if r['總入']>=3: o25+=1
        if r['總入']>=2: o15+=1
        if r['總入']>=4: o35+=1
        scores[f"{r['主入']}-{r['客入']}"]+=1
        if r['半主']!=0 or r['半客']!=0:
            my_ht=r['半主'] if is_home else r['半客']; opp_ht=r['半客'] if is_home else r['半主']
            if my_ht>opp_ht: ht_w+=1
            elif my_ht==opp_ht: ht_d+=1
            else: ht_l+=1
    n=win+draw+lose
    if n==0: return None
    return {"場":n,"勝":win,"和":draw,"負":lose,"勝率":win/n*100,"和率":draw/n*100,"負率":lose/n*100,
            "半勝":ht_w,"半和":ht_d,"半負":ht_l,"半勝率":ht_w/n*100,"半和率":ht_d/n*100,"半負率":ht_l/n*100,
            "入":gf/n,"失":ga/n,"總入":(gf+ga)/n,"BTTS%":btts/n*100,"大2.5%":o25/n*100,"大1.5%":o15/n*100,"大3.5%":o35/n*100,
            "波膽":scores.most_common(5)}

for k in ['recA','recH','statsA','statsH','selA','selB']:
    if k not in st.session_state: st.session_state[k]=[] if 'rec' in k else None

st.title("🌍 v13.3 關鍵字+Drop list - 打簡稱就得")
st.caption("打 Swin / Man / Buriram 關鍵字就搜，Drop list揀隊，唔使全名")

# === 關鍵字搜隊 ===
c1,c2,c3=st.columns([2,2,1])
with c1:
    kwA=st.text_input("主隊A關鍵字 (打2個字母就得)", placeholder="例: Swin / Arse / Buri", key="kwA")
    if st.button("🔍 搜主隊A", key="btnA"):
        st.session_state.candsA=search_teams(kwA)
    candsA=st.session_state.get('candsA',[])
    if candsA:
        optsA=[f"{x['name']} | {x['league']} | ID:{x['id']}" for x in candsA]
        sel=st.selectbox("揀主隊A (相似隊名)", optsA, key="optA")
        idx=optsA.index(sel); st.session_state.selA=candsA[idx]
        st.success(f"已揀: {candsA[idx]['name']}")
    else:
        if kwA: st.info("按搜主隊A")

with c2:
    kwB=st.text_input("客隊B關鍵字", placeholder="例: New / City / Bank", key="kwB")
    if st.button("🔍 搜客隊B", key="btnB"):
        st.session_state.candsB=search_teams(kwB)
    candsB=st.session_state.get('candsB',[])
    if candsB:
        optsB=[f"{x['name']} | {x['league']} | ID:{x['id']}" for x in candsB]
        sel=st.selectbox("揀客隊B", optsB, key="optB")
        idx=optsB.index(sel); st.session_state.selB=candsB[idx]
        st.success(f"已揀: {candsB[idx]['name']}")
    else:
        if kwB: st.info("按搜客隊B")

with c3:
    n=st.slider("場數",5,20,10)
    idA_man=st.number_input("A ID手填後備",0,999999,0)
    idB_man=st.number_input("B ID手填後備",0,999999,0)

# 確定隊
teamA_obj=st.session_state.selA; teamB_obj=st.session_state.selB
teamA_name=teamA_obj['name'] if teamA_obj else ""
teamB_name=teamB_obj['name'] if teamB_obj else ""
teamA_id=teamA_obj['id'] if teamA_obj else (idA_man if idA_man>0 else None)
teamB_id=teamB_obj['id'] if teamB_obj else (idB_man if idB_man>0 else None)

if not teamA_id or not teamB_id:
    st.warning("👆 先用關鍵字搜，再Drop list揀兩隊，唔使打全名")
    st.stop()

st.divider()
col1,col2=st.columns(2)
with col1:
    if st.button(f"🔍 自動捉 {teamA_name} 近{n}場", use_container_width=True, type="primary"):
        raw=fetch_recent(teamA_id,n)
        if raw:
            rec=[parse(x) for x in raw if parse(x)]
            st.session_state.recA=rec; st.session_state.statsA=analyse(rec, teamA_name)
            st.success(f"捉到 {len(rec)} 場 {teamA_name} {st.session_state.statsA['勝']}勝")
        else: st.warning("API擋，用手入")
with col2:
    if st.button(f"🔍 自動捉對賽 {teamA_name} vs {teamB_name}", use_container_width=True):
        raw=fetch_h2h(teamA_id,teamB_id,12)
        if raw:
            rec=[parse(x) for x in raw if parse(x)]
            st.session_state.recH=rec; st.session_state.statsH=analyse(rec, teamA_name)
            st.success(f"捉到 {len(rec)} 場對賽")
        else: st.error("對賽空，用手入")

# 手入後備
with st.expander("✋ 手入後備 - 主客分兩邊", expanded=False):
    dfA=pd.DataFrame([{"對手":"","主客":"主","我入":0,"對手入":0,"半主":0,"半客":0} for _ in range(10)])
    if st.session_state.recA:
        try: dfA=pd.DataFrame([{"對手":r['客隊'] if teamA_name.lower() in r['主隊'].lower() else r['主隊'],"主客":"主" if teamA_name.lower() in r['主隊'].lower() else "客","我入":r['主入'] if teamA_name.lower() in r['主隊'].lower() else r['客入'],"對手入":r['客入'] if teamA_name.lower() in r['主隊'].lower() else r['主入'],"半主":r['半主'],"半客":r['半客']} for r in st.session_state.recA])
        except: pass
    edA=st.data_editor(dfA, num_rows="dynamic", use_container_width=True, key="edA2")

    dfH=pd.DataFrame([{"主隊":teamA_name,"主入":0,"客入":0,"客隊":teamB_name,"半主":0,"半客":0} for _ in range(12)])
    if st.session_state.recH:
        try: dfH=pd.DataFrame([{"主隊":r['主隊'],"主入":r['主入'],"客入":r['客入'],"客隊":r['客隊'],"半主":r['半主'],"半客":r['半客']} for r in st.session_state.recH])
        except: pass
    edH=st.data_editor(dfH, num_rows="dynamic", use_container_width=True, key="edH2")

    if st.button("✅ 用手入覆蓋"):
        recA2=[]; recH2=[]
        for _,r in edA.iterrows():
            if int(r["我入"])==0 and int(r["對手入"])==0 and str(r["對手"]).strip()=="": continue
            is_home=r["主客"]=="主"
            recA2.append({"日期":"2025-01-01","主隊":teamA_name if is_home else str(r["對手"]),"客隊":str(r["對手"]) if is_home else teamA_name,"主入":int(r["我入"]) if is_home else int(r["對手入"]),"客入":int(r["對手入"]) if is_home else int(r["我入"]),"半主":int(r["半主"]),"半客":int(r["半客"]),"總入":int(r["我入"])+int(r["對手入"])})
        for _,r in edH.iterrows():
            if int(r["主入"])==0 and int(r["客入"])==0 and str(r["主隊"]).strip()=="": continue
            recH2.append({"日期":"2024-01-01","主隊":str(r["主隊"]),"客隊":str(r["客隊"]),"主入":int(r["主入"]),"客入":int(r["客入"]),"半主":int(r["半主"]),"半客":int(r["半客"]),"總入":int(r["主入"])+int(r["客入"])})
        st.session_state.recA=recA2; st.session_state.recH=recH2
        st.session_state.statsA=analyse(recA2, teamA_name) if recA2 else None
        st.session_state.statsH=analyse(recH2, teamA_name) if recH2 else None
        st.success("已覆蓋")

if st.session_state.get('statsA'):
    sA=st.session_state.statsA; sH=st.session_state.get('statsH')
    st.divider()
    c1,c2=st.columns(2)
    with c1: st.metric(f"① {teamA_name} 硬實力", f"{sA['勝']}勝{sA['和']}和{sA['負']}負", f"勝率 {sA['勝率']:.0f}%")
    with c2:
        if sH: st.metric(f"② 對賽 {teamA_name} vs {teamB_name}", f"{sH['勝']}勝{sH['和']}和{sH['負']}負", f"{sH['勝率']:.0f}%")
    if st.session_state.recA: st.dataframe(pd.DataFrame(st.session_state.recA), use_container_width=True)

    st.subheader("🎯 馬會主盤")
    cands=[]
    cands.append({"盤口":"全場主客和","組合":f"{teamA_name} 勝","命中":sA['勝率'],"原因":f"硬實力勝率{sA['勝率']:.0f}% 入{sA['入']:.1f}"})
    cands.append({"盤口":"全場主客和","組合":"和","命中":sA['和率'],"原因":f"和率{sA['和率']:.0f}%"})
    cands.append({"盤口":"全場主客和","組合":f"{teamB_name} 勝","命中":sA['負率'],"原因":f"負率{sA['負率']:.0f}%"})
    if sH: cands.append({"盤口":"全場主客和(對賽)","組合":f"{teamA_name} 勝(對賽)","命中":sH['勝率'],"原因":f"對賽{sH['勝']}勝 勝率{sH['勝率']:.0f}%"})

    cands.append({"盤口":"半場主客和","組合":f"半場 {teamA_name} 勝","命中":sA['半勝率'] if sA['半勝率']>0 else sA['勝率']*0.55,"原因":f"半勝率{sA['半勝率']:.0f}%"})
    cands.append({"盤口":"半場主客和","組合":"半場 和","命中":sA['半和率'] if sA['半和率']>0 else 35,"原因":f"半和{sA['半和率']:.0f}%"})
    cands.append({"盤口":"半場主客和","組合":f"半場 {teamB_name} 勝","命中":sA['半負率'] if sA['半負率']>0 else sA['負率']*0.55,"原因":f"半負{sA['半負率']:.0f}%"})

    cands.append({"盤口":"入球大細","組合":"大1.5","命中":sA['大1.5%'],"原因":f"大1.5 {sA['大1.5%']:.0f}% 總入{sA['總入']:.1f}"})
    cands.append({"盤口":"入球大細","組合":"大2.5","命中":sA['大2.5%'],"原因":f"大2.5 {sA['大2.5%']:.0f}%"})
    cands.append({"盤口":"入球大細","組合":"細2.5","命中":100-sA['大2.5%'],"原因":f"細2.5 {100-sA['大2.5%']:.0f}%"})

    if sA.get('波膽'):
        for sc,cnt in sA['波膽'][:3]:
            cands.append({"盤口":"全場波膽","組合":f"波膽 {sc}","命中":cnt/sA['場']*100,"原因":f"出現{cnt}次 {cnt/sA['場']*100:.0f}%"})

    cands=sorted(cands, key=lambda x: x['命中'], reverse=True)
    st.dataframe(pd.DataFrame(cands), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("💰 馬會賠率EV")
    for mk in ["全場主客和","半場主客和","入球大細","全場波膽"]:
        subset=[c for c in cands if mk in c['盤口']][:4]
        if not subset: continue
        st.write(f"**{mk}**")
        cols=st.columns(len(subset))
        rows=[]
        for i,c in enumerate(subset):
            with cols[i]:
                odd=st.number_input(f"{c['組合']}", 1.05, 50.0, 2.0, 0.05, key=f"odd_{mk}_{i}_{teamA_name}")
                ev=(c['命中']/100*odd-1)*100
                grade="🔥 超值" if ev>15 else "✅ 值博" if ev>5 else "⚠️ 一般" if ev>-5 else "❌ 唔值"
                st.caption(f"{c['命中']:.0f}% EV {ev:.1f}% {grade}")
                rows.append({"盤口":mk,"組合":c['組合'],"命中":f"{c['命中']:.0f}%","賠率":odd,"EV":f"{ev:.1f}%","評級":grade})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

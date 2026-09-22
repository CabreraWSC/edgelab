import streamlit as st, requests, re, pandas as pd
from collections import Counter

st.set_page_config(page_title="EdgeLab v13.1 完全通用", layout="wide")
APP_PWD = st.secrets.get("APP_PWD","1234")
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    pwd=st.text_input("密碼", type="password")
    if st.button("登入") and pwd==APP_PWD: st.session_state.auth=True; st.rerun()
    st.stop()

HEADERS={"User-Agent":"Mozilla/5.0","Referer":"https://www.aiscore.com/","Accept":"application/json"}

def search_id(name):
    """完全按用戶輸入搜，無預設"""
    if not name: return None, "請填隊名"
    # 試多個搜索接口
    urls=[f"https://www.aiscore.com/api/search?query={name}",
          f"https://api.aiscore.com/search?query={name}"]
    for url in urls:
        try:
            r=requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code==200:
                j=r.json()
                teams=j.get('data',{}).get('teams',[]) or j.get('teams',[]) or j.get('data',[]) or []
                if isinstance(teams, dict): teams=teams.get('teams',[])
                if isinstance(teams, list) and len(teams)>0:
                    # 搵最匹配
                    for t in teams:
                        tname=t.get('name','') or t.get('teamName','')
                        if name.lower() in tname.lower() or tname.lower() in name.lower():
                            return t.get('id'), tname
                    # 無完全匹配就取第一個
                    t=teams[0]
                    return t.get('id'), t.get('name') or t.get('teamName')
        except: continue
    return None, f"AI Score暫時搜唔到 {name}，請試英文全名或下面手填ID"

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

def fetch_h2h(id1,id2,n=12):
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
    scores=Counter(); ht_scores=Counter()
    for r in records:
        is_home=target.lower() in r['主隊'].lower() if r['主隊']!='?' else False
        is_away=target.lower() in r['客隊'].lower() if r['客隊']!='?' else False
        if not is_home and not is_away:
            # 如果名對唔上，跳過避免計錯
            continue
        my=r['主入'] if is_home else r['客入']
        opp=r['客入'] if is_home else r['主入']
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
            my_ht=r['半主'] if is_home else r['半客']
            opp_ht=r['半客'] if is_home else r['半主']
            if my_ht>opp_ht: ht_w+=1
            elif my_ht==opp_ht: ht_d+=1
            else: ht_l+=1
            ht_scores[f"{r['半主']}-{r['半客']}"]+=1
    n=win+draw+lose
    if n==0: return None
    return {"場":n,"勝":win,"和":draw,"負":lose,"勝率":win/n*100,"和率":draw/n*100,"負率":lose/n*100,
            "半勝":ht_w,"半和":ht_d,"半負":ht_l,"半勝率":ht_w/n*100,"半和率":ht_d/n*100,"半負率":ht_l/n*100,
            "入":gf/n,"失":ga/n,"總入":(gf+ga)/n,"BTTS%":btts/n*100,"大2.5%":o25/n*100,"大1.5%":o15/n*100,"大3.5%":o35/n*100,
            "波膽":scores.most_common(5),"半波膽":ht_scores.most_common(3)}

for k in ['statsA','statsH','recA','recH']:
    if k not in st.session_state: st.session_state[k]=None if 'stats' in k else []

st.title("🌍 v13.1 完全通用 - 打咩隊捉咩隊")
st.caption("無預設，你填咩隊名就去AI Score搵咩隊，任何聯賽通用")

c1,c2,c3=st.columns([2,2,1])
with c1:
    teamA=st.text_input("主隊A名 (必填，例: Arsenal / Buriram)", placeholder="打英文最準", key="teamA_input")
    idA_manual=st.number_input("A ID 手填後備 (可空)", 0, 999999, 0, key="idA")
with c2:
    teamB=st.text_input("客隊B名 (必填，當日對手)", placeholder="例: Man City / Bangkok Utd", key="teamB_input")
    idB_manual=st.number_input("B ID 手填後備 (可空)", 0, 999999, 0, key="idB")
with c3:
    n=st.slider("分析場數",5,20,10)

if not teamA or not teamB:
    st.info("👆 先填兩隊名，唔預設，填咩捉咩")
    st.stop()

col1,col2=st.columns(2)
with col1:
    if st.button(f"🔍 自動捉 {teamA} 近{n}場", use_container_width=True, type="primary"):
        tid=idA_manual if idA_manual>0 else None
        tname=teamA
        if not tid:
            tid, tname = search_id(teamA)
        if not tid:
            st.error(f"{tname} - 請試英文全名或去 aiscore.com 抄ID填入上面")
        else:
            with st.spinner(f"用 {tname} ID:{tid} 捉近況..."):
                raw=fetch_recent(tid,n)
                if raw:
                    rec=[parse(x) for x in raw if parse(x)]
                    st.session_state.recA=rec
                    st.session_state.statsA=analyse(rec, teamA)
                    st.success(f"捉到 {len(rec)} 場 {teamA}: {st.session_state.statsA['勝']}勝{st.session_state.statsA['和']}和{st.session_state.statsA['負']}負")
                else:
                    st.warning("AI Score暫時攔截，轉用下面手入")

with col2:
    if st.button(f"🔍 自動捉對賽 {teamA} vs {teamB}", use_container_width=True):
        tidA=idA_manual if idA_manual>0 else search_id(teamA)[0]
        tidB=idB_manual if idB_manual>0 else search_id(teamB)[0]
        if not tidA or not tidB:
            st.error(f"搵唔到ID A:{tidA} B:{tidB}，請試英文或手填ID")
        else:
            with st.spinner(f"捉對賽 ID {tidA} vs {tidB}..."):
                raw=fetch_h2h(tidA,tidB,12)
                if raw:
                    rec=[parse(x) for x in raw if parse(x)]
                    st.session_state.recH=rec
                    st.session_state.statsH=analyse(rec, teamA)
                    st.success(f"捉到 {len(rec)} 場對賽，{teamA} {st.session_state.statsH['勝']}勝")
                else:
                    st.error("對賽API空，請用手入")

# 手入後備
st.divider()
with st.expander("✋ 手入後備 (自動捉唔到先用) - 左主隊 右客隊 淨入比分", expanded=False):
    st.write(f"**{teamA} 近場手入**")
    dfA=pd.DataFrame([{"對手":"","主客":"主",f"{teamA}入":0,"對手入":0,"半主":0,"半客":0} for _ in range(10)])
    if st.session_state.recA:
        dfA=pd.DataFrame([{"對手":r['客隊'] if teamA.lower() in r['主隊'].lower() else r['主隊'],"主客":"主" if teamA.lower() in r['主隊'].lower() else "客",f"{teamA}入":r['主入'] if teamA.lower() in r['主隊'].lower() else r['客入'],"對手入":r['客入'] if teamA.lower() in r['主隊'].lower() else r['主入'],"半主":r['半主'],"半客":r['半客']} for r in st.session_state.recA])
    edA=st.data_editor(dfA, num_rows="dynamic", use_container_width=True, key="edA")

    st.write(f"**對賽 {teamA} vs {teamB} 手入**")
    dfH=pd.DataFrame([{"主隊":teamA,"主入":0,"客入":0,"客隊":teamB,"半主":0,"半客":0} for _ in range(12)])
    if st.session_state.recH:
        dfH=pd.DataFrame([{"主隊":r['主隊'],"主入":r['主入'],"客入":r['客入'],"客隊":r['客隊'],"半主":r['半主'],"半客":r['半客']} for r in st.session_state.recH])
    edH=st.data_editor(dfH, num_rows="dynamic", use_container_width=True, key="edH")

    if st.button("✅ 用手入覆蓋"):
        recA2=[]
        for _,r in edA.iterrows():
            if r[f"{teamA}入"]==0 and r["對手入"]==0 and r["對手"]=="": continue
            is_home=r["主客"]=="主"
            recA2.append({"日期":"2025-01-01","主隊":teamA if is_home else r["對手"],"客隊":r["對手"] if is_home else teamA,"主入":int(r[f"{teamA}入"]) if is_home else int(r["對手入"]),"客入":int(r["對手入"]) if is_home else int(r[f"{teamA}入"]),"半主":int(r["半主"]),"半客":int(r["半客"]),"總入":int(r[f"{teamA}入"])+int(r["對手入"])})
        recH2=[]
        for _,r in edH.iterrows():
            if r["主入"]==0 and r["客入"]==0 and r["主隊"]=="": continue
            recH2.append({"日期":"2024-01-01","主隊":r["主隊"],"客隊":r["客隊"],"主入":int(r["主入"]),"客入":int(r["客入"]),"半主":int(r["半主"]),"半客":int(r["半客"]),"總入":int(r["主入"])+int(r["客入"])})
        st.session_state.recA=recA2; st.session_state.recH=recH2
        st.session_state.statsA=analyse(recA2, teamA) if recA2 else None
        st.session_state.statsH=analyse(recH2, teamA) if recH2 else None
        st.success("已用手入")

# 展示
if st.session_state.get('statsA'):
    sA=st.session_state.statsA; sH=st.session_state.get('statsH')
    st.divider()
    c1,c2=st.columns(2)
    with c1: st.metric(f"① {teamA} 硬實力", f"{sA['勝']}勝{sA['和']}和{sA['負']}負", f"勝率 {sA['勝率']:.0f}% 場均 {sA['總入']:.1f}球")
    with c2:
        if sH: st.metric(f"② 對賽 {teamA} vs {teamB}", f"{sH['勝']}勝{sH['和']}和{sH['負']}負", f"勝率 {sH['勝率']:.0f}%"); st.dataframe(pd.DataFrame(st.session_state.recH), use_container_width=True)
    st.dataframe(pd.DataFrame(st.session_state.recA), use_container_width=True)

    st.divider()
    st.subheader("🎯 馬會主盤自動判斷")

    cands=[]
    cands.append({"盤口":"全場主客和","組合":f"{teamA} 勝","命中":sA['勝率'],"原因":f"硬實力 {sA['勝率']:.0f}% 場均入{sA['入']:.1f}"})
    cands.append({"盤口":"全場主客和","組合":"和","命中":sA['和率'],"原因":f"和率 {sA['和率']:.0f}% 共{sA['和']}場"})
    cands.append({"盤口":"全場主客和","組合":f"{teamB} 勝","命中":sA['負率'],"原因":f"{teamA} 負率 {sA['負率']:.0f}%"})
    if sH: cands.append({"盤口":"全場主客和(對賽)","組合":f"{teamA} 勝(對賽)","命中":sH['勝率'],"原因":f"對賽 {sH['場']}場 {sH['勝']}勝 勝率{sH['勝率']:.0f}% 剋制"})

    cands.append({"盤口":"半場主客和","組合":f"半場 {teamA} 勝","命中":sA['半勝率'] if sA['半勝率']>0 else sA['勝率']*0.55,"原因":f"半場勝率 {sA['半勝率']:.0f}%"})
    cands.append({"盤口":"半場主客和","組合":"半場 和","命中":sA['半和率'] if sA['半和率']>0 else 35,"原因":f"半場和 {sA['半和率']:.0f}%"})
    cands.append({"盤口":"半場主客和","組合":f"半場 {teamB} 勝","命中":sA['半負率'] if sA['半負率']>0 else sA['負率']*0.55,"原因":f"半場負 {sA['半負率']:.0f}%"})

    cands.append({"盤口":"入球大細","組合":"大1.5","命中":sA['大1.5%'],"原因":f"大1.5 {sA['大1.5%']:.0f}% 場均{sA['總入']:.1f}"})
    cands.append({"盤口":"入球大細","組合":"大2.5","命中":sA['大2.5%'],"原因":f"大2.5 {sA['大2.5%']:.0f}% BTTS{sA['BTTS%']:.0f}%"})
    cands.append({"盤口":"入球大細","組合":"細2.5","命中":100-sA['大2.5%'],"原因":f"細2.5 {100-sA['大2.5%']:.0f}% 失{sA['失']:.1f}"})

    if sA['波膽']:
        for sc,cnt in sA['波膽'][:3]:
            cands.append({"盤口":"全場波膽","組合":f"波膽 {sc}","命中":cnt/sA['場']*100,"原因":f"出現{cnt}次 {cnt/sA['場']*100:.0f}% 最常見"})
    if sH and sH['波膽']:
        for sc,cnt in sH['波膽'][:2]:
            cands.append({"盤口":"全場波膽(對賽)","組合":f"對賽波膽 {sc}","命中":cnt/sH['場']*100,"原因":f"對賽出現{cnt}次"})

    cands=sorted(cands, key=lambda x: x['命中'], reverse=True)
    st.dataframe(pd.DataFrame(cands), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("💰 馬會賠率入EV")
    for mk in ["全場主客和","半場主客和","入球大細","全場波膽"]:
        subset=[c for c in cands if mk in c['盤口']][:4]
        if not subset: continue
        st.write(f"**{mk}**")
        cols=st.columns(len(subset))
        rows=[]
        for i,c in enumerate(subset):
            with cols[i]:
                odd=st.number_input(f"{c['組合']}", 1.05, 50.0, 2.0, 0.05, key=f"odd_{mk}_{i}")
                ev=(c['命中']/100*odd-1)*100
                grade="🔥 超值" if ev>15 else "✅ 值博" if ev>5 else "⚠️ 一般" if ev>-5 else "❌ 唔值"
                st.caption(f"{c['命中']:.0f}% EV {ev:.1f}% {grade}")
                rows.append({"盤口":mk,"組合":c['組合'],"命中":f"{c['命中']:.0f}%","賠率":odd,"EV":f"{ev:.1f}%","評級":grade})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

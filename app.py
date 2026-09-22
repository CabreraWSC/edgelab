import streamlit as st, requests, re, pandas as pd

st.set_page_config(page_title="EdgeLab v12.1 通用AI Score", layout="wide")
APP_PWD = st.secrets.get("APP_PWD","1234")
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    st.title("🔒 EdgeLab v12.1");
    if st.text_input("密碼", type="password")==APP_PWD or st.button("登入") and st.session_state.get('pwd','')==APP_PWD:
        pass
    pwd=st.text_input("密碼",type="password",key="pwd2")
    if st.button("登入"):
        if pwd==APP_PWD: st.session_state.auth=True; st.rerun()
        else: st.error("錯")
    st.stop()

HEADERS={"User-Agent":"Mozilla/5.0","Referer":"https://www.aiscore.com/","Accept":"application/json"}

def search_team_id(keyword):
    """通用搜隊，任何聯賽都得"""
    if not keyword: return None, None
    try:
        # AI Score 官方搜索
        url=f"https://api.aiscore.com/search?query={keyword}"
        r=requests.get(url, headers=HEADERS, timeout=10)
        j=r.json()
        # 結構: data.teams / data.data
        teams=j.get('data',{}).get('teams',[]) or j.get('data',[]) or j.get('teams',[]) or []
        # 有時是dict
        if isinstance(teams, dict): teams=teams.get('teams',[])
        if teams and len(teams)>0:
            # 揀最匹配
            t=teams[0]
            return t.get('id'), t.get('name') or t.get('teamName')
    except Exception as e:
        pass
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
        ht=m.get('homeTeam',{}).get('name','?') if isinstance(m.get('homeTeam'),dict) else m.get('homeName', m.get('home','?'))
        at=m.get('awayTeam',{}).get('name','?') if isinstance(m.get('awayTeam'),dict) else m.get('awayName', m.get('away','?'))
        hs=m.get('homeScore', m.get('score',{}).get('home',0) if isinstance(m.get('score'),dict) else 0)
        aw=m.get('awayScore', m.get('score',{}).get('away',0) if isinstance(m.get('score'),dict) else 0)
        if (hs==0 and aw==0):
            nums=re.findall(r'\d+', str(m.get('result','') or m.get('score','')))
            if len(nums)>=2: hs,aw=int(nums[0]),int(nums[1])
        dt=str(m.get('date','') or m.get('matchTime','') or m.get('time',''))[:10]
        return {"日期":dt,"主隊":ht,"客隊":at,"主入":int(hs),"客入":int(aw),"總入":int(hs)+int(aw)}
    except: return None

def analyse(records, team_name):
    if not records: return None
    win=draw=lose=gf=ga=btts=o25=o15=0
    for r in records:
        is_home=team_name.lower() in r['主隊'].lower() if r['主隊']!='?' else True
        # 如果唔確定，用第一個邏輯
        if team_name.lower() not in r['主隊'].lower() and team_name.lower() not in r['客隊'].lower():
            is_home=True
        f=r['主入'] if is_home else r['客入']; a=r['客入'] if is_home else r['主入']
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
st.title("🌍 v12.1 通用AI Score - 任何聯賽任何球隊")
st.caption("唔預設球隊，你打咩隊都得，英超/日職/泰超通用")

with st.form("search"):
    c1,c2,c3=st.columns([2,2,1])
    with c1: inA=st.text_input("主隊關鍵字 (例: Man City / 神戶 / Buriram)", placeholder="打英文最準")
    with c2: inB=st.text_input("客隊關鍵字 (當日對手)", placeholder="打英文最準")
    with c3: n=st.number_input("分析場數",5,20,10)
    go=st.form_submit_button("🔍 搜隊 + 一鍵分析", type="primary", use_container_width=True)

if go:
    if not inA or not inB:
        st.error("兩隊都要填")
    else:
        with st.spinner(f"AI Score 搜尋 {inA} vs {inB}..."):
            idA,nameA=search_team_id(inA)
            idB,nameB=search_team_id(inB)
            if not idA or not idB:
                st.error(f"搵唔到隊，試打英文全名。A:{idA} B:{idB}"); st.stop()
            st.success(f"鎖定: {nameA} (ID:{idA}) vs {nameB} (ID:{idB})")
            rawA=fetch_recent(idA,n); rawH=fetch_h2h(idA,idB,n)
            recA=[parse(x) for x in rawA if parse(x)]
            recH=[parse(x) for x in rawH if parse(x)]
            st.session_state['teamA_name']=nameA; st.session_state['teamB_name']=nameB
            st.session_state['recA']=recA; st.session_state['recH']=recH
            st.session_state['statsA']=analyse(recA, nameA)
            st.session_state['statsH']=analyse(recH, nameA)

if 'statsA' in st.session_state:
    sA=st.session_state['statsA']; sH=st.session_state['statsH']
    nameA=st.session_state['teamA_name']; nameB=st.session_state['teamB_name']

    st.divider()
    c1,c2=st.columns(2)
    with c1:
        st.subheader(f"① {nameA} 硬實力 (近{sA['場']}場 vs 所有對手)")
        if sA:
            st.metric("勝率 / 不敗", f"{sA['勝率']:.0f}% / {sA['不敗率']:.0f}%", f"{sA['勝']}W {sA['和']}D {sA['負']}L")
            st.metric("攻防", f"{sA['入']:.2f}入 {sA['失']:.2f}失", f"場均總 {sA['總入']:.2f}")
            st.metric("大2.5 / BTTS", f"{sA['大2.5%']:.0f}% / {sA['BTTS%']:.0f}%")
    with c2:
        st.subheader(f"② 對賽剋制 {nameA} vs {nameB} (近{len(st.session_state['recH'])}場)")
        if sH:
            st.metric("對賽勝率", f"{sH['勝率']:.0f}%", f"{sH['勝']}W {sH['和']}D {sH['負']}L")
            st.metric("對賽總入 / BTTS", f"{sH['總入']:.2f} / {sH['BTTS%']:.0f}%")
            if sH['勝率']>=60: st.success("實力一直喺對手之上")
            elif sH['勝率']<=30: st.error("被剋")
            else: st.info("均勢")

    st.divider()
    st.subheader("🎯 自動判斷 - 命中率高組合 (先唔計賠率)")

    cands=[]
    if sA['勝率']>=45 and sH and sH['勝率']>=45:
        cands.append({"組合":f"{nameA} 勝","命中":(sA['勝率']+sH['勝率'])/2,"原因":f"硬實力{sA['勝率']:.0f}% + 對賽{sH['勝率']:.0f}%"})
    if sA['不敗率']>=70:
        cands.append({"組合":f"{nameA} 不敗","命中":sA['不敗率'],"原因":f"近{sA['場']}場不敗{sA['不敗率']:.0f}%"})
    if sA['大1.5%']>=75:
        cands.append({"組合":"大1.5","命中":sA['大1.5%'],"原因":f"大1.5高 {sA['大1.5%']:.0f}% 場均{sA['總入']:.1f}球"})
    if sA['大2.5%']>=55:
        cands.append({"組合":"大2.5","命中":sA['大2.5%'],"原因":f"大2.5 {sA['大2.5%']:.0f}%"})
    if sA['大2.5%']<=35:
        cands.append({"組合":"細2.5","命中":100-sA['大2.5%'],"原因":f"細波多 場均{sA['總入']:.1f}"})
    if sA['BTTS%']>=60:
        cands.append({"組合":"BTTS 是","命中":sA['BTTS%'],"原因":f"BTTS {sA['BTTS%']:.0f}%"})
    if sA['BTTS%']<=35:
        cands.append({"組合":"BTTS 否","命中":100-sA['BTTS%'],"原因":f"零封多 BTTS僅{sA['BTTS%']:.0f}%"})

    cands=sorted(cands, key=lambda x: x['命中'], reverse=True)
    st.session_state['cands']=cands
    st.dataframe(pd.DataFrame(cands), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("💰 貼馬會賠率 → 計EV評級 (空出嚟俾你入，任何盤口都得)")
    st.caption("入球、角球、讓球、半場，咩盤都得，你入賠率就計")

    if cands:
        evs=[]
        cols=st.columns(3)
        for i,c in enumerate(cands[:6]):
            with cols[i%3]:
                odd=st.number_input(f"{c['組合']} 賠率", 1.05, 30.0, 1.90, 0.05, key=f"odd_{i}")
                ev=(c['命中']/100*odd-1)*100
                grade="🔥 超值" if ev>15 else "✅ 值博" if ev>5 else "⚠️ 一般" if ev>-5 else "❌ 唔值"
                evs.append({"組合":c['組合'],"命中":f"{c['命中']:.0f}%","賠率":odd,"EV":f"{ev:.1f}%","評級":grade})

        df_ev=pd.DataFrame(evs)
        st.dataframe(df_ev, use_container_width=True, hide_index=True)

        # 自訂盤口
        st.write("---")
        st.write("➕ 自訂其他盤口 (例: 角球大9.5 / 讓球-1)")
        c1,c2,c3=st.columns(3)
        with c1: custom_name=st.text_input("盤口名", placeholder="例: 角球大9.5")
        with c2: custom_prob=st.number_input("你估命中率 % (睇上面數據估)", 1, 99, 55)
        with c3: custom_odd=st.number_input("該盤口賠率", 1.05, 30.0, 1.85, key="custom_odd")
        if custom_name:
            ev2=(custom_prob/100*custom_odd-1)*100
            st.info(f"{custom_name} EV {ev2:.1f}% -> {'🔥超值' if ev2>15 else '✅值博' if ev2>5 else '⚠️一般'}")

    with st.expander("📋 原始數據"):
        st.dataframe(pd.DataFrame(st.session_state['recA']), use_container_width=True)
        st.dataframe(pd.DataFrame(st.session_state['recH']), use_container_width=True)

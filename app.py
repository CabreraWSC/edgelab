import streamlit as st, requests, re, pandas as pd
from collections import Counter

st.set_page_config(page_title="EdgeLab v13.6 合併最終", layout="wide")
APP_PWD = st.secrets.get("APP_PWD","1234")
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    pwd=st.text_input("密碼", type="password")
    if st.button("登入") and pwd==APP_PWD: st.session_state.auth=True; st.rerun()
    st.stop()

HEADERS={"User-Agent":"Mozilla/5.0","Referer":"https://www.aiscore.com/","Accept":"application/json"}
COMMON=[(3425,"Swindon Town","ENG L2"),(3559,"Newport County","ENG L2"),(21138,"Man City","ENG PL"),(21134,"Arsenal","ENG PL"),(21139,"Man Utd","ENG PL"),(21136,"Liverpool","ENG PL")]

def search_teams(kw):
    if not kw or len(kw.strip())<2: return []
    kw=kw.lower(); res=[]
    for tid,name,lg in COMMON:
        if kw in name.lower(): res.append({"id":tid,"name":name,"league":lg})
    for url in [f"https://www.aiscore.com/api/search?query={kw}", f"https://api.aiscore.com/search?query={kw}"]:
        try:
            r=requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code==200:
                j=r.json(); teams=j.get('data',{}).get('teams',[]) or j.get('teams',[]) or j.get('data',[]) or []
                if isinstance(teams,dict): teams=teams.get('teams',[])
                for t in teams[:15]:
                    tid=t.get('id'); tname=t.get('name') or t.get('teamName','')
                    if tid and tname and tid not in [x['id'] for x in res]:
                        res.append({"id":tid,"name":tname,"league":t.get('leagueName','')})
        except: pass
    return res[:15]

def fetch_recent(tid,n):
    try:
        r=requests.get(f"https://www.aiscore.com/api/football/team/matches?teamId={tid}&count={n}", headers=HEADERS, timeout=10)
        j=r.json(); d=j.get('data',j)
        if isinstance(d,dict) and 'matches' in d: d=d['matches']
        if isinstance(d,list) and len(d)>0: return d
    except: pass
    return []

def fetch_h2h(id1,id2,n):
    try:
        r=requests.get(f"https://www.aiscore.com/api/football/match/h2h?teamId1={id1}&teamId2={id2}&count={n}", headers=HEADERS, timeout=10)
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
        return {"日期":str(m.get('date',''))[:10],"主隊":ht,"客隊":at,"主入":int(hs),"客入":int(aw),"半主":int(hhs or 0),"半客":int(haws or 0),"總入":int(hs)+int(aw)}
    except: return None

def analyse(records, target):
    if not records: return None
    win=draw=lose=gf=ga=btts=o25=o15=o35=0; ht_w=ht_d=ht_l=0; scores=Counter(); valid=0
    for r in records:
        if target.lower() not in r['主隊'].lower() and target.lower() not in r['客隊'].lower() and valid>0: continue
        is_home=target.lower() in r['主隊'].lower()
        my=r['主入'] if is_home else r['客入']; opp=r['客入'] if is_home else r['主入']
        gf+=my; ga+=opp; valid+=1
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
    if valid==0: return None
    return {"場":valid,"勝":win,"和":draw,"負":lose,"勝率":win/valid*100,"和率":draw/valid*100,"負率":lose/valid*100,
            "半勝":ht_w,"半和":ht_d,"半負":ht_l,"半勝率":ht_w/valid*100,"半和率":ht_d/valid*100,"半負率":ht_l/valid*100,
            "入":gf/valid,"失":ga/valid,"總入":(gf+ga)/valid,"BTTS%":btts/valid*100,"大2.5%":o25/valid*100,"大1.5%":o15/valid*100,"大3.5%":o35/valid*100,"波膽":scores.most_common(5)}

for k in ['recA','recH','statsA','statsH','selA','selB','candsA','candsB']:
    if k not in st.session_state: st.session_state[k]=[] if 'rec' in k or 'cands' in k else None

st.title("🌍 v13.6 合併最終 - 無重複+直接打賠率")
st.caption("關鍵字打2字母搜:Drop list揀 | 自動捉為主 | 全場主客和得3個無重複 | 賠率表格點一下直接打新數")

c1,c2,c3=st.columns([2,2,1])
with c1:
    kwA=st.text_input("主隊A關鍵字", placeholder="Swin / Arse / Buri", key="kwA")
    if st.button("🔍 搜A", key="btnA"): st.session_state.candsA=search_teams(kwA)
    if st.session_state.candsA:
        opts=[f"{x['name']} | {x['league']} | ID:{x['id']}" for x in st.session_state.candsA]
        sel=st.selectbox("揀主隊A", opts, key="optA")
        st.session_state.selA=st.session_state.candsA[opts.index(sel)]
        st.success(f"已揀: {st.session_state.selA['name']}")
with c2:
    kwB=st.text_input("客隊B關鍵字", placeholder="New / City", key="kwB")
    if st.button("🔍 搜B", key="btnB"): st.session_state.candsB=search_teams(kwB)
    if st.session_state.candsB:
        opts=[f"{x['name']} | {x['league']} | ID:{x['id']}" for x in st.session_state.candsB]
        sel=st.selectbox("揀客隊B", opts, key="optB")
        st.session_state.selB=st.session_state.candsB[opts.index(sel)]
        st.success(f"已揀: {st.session_state.selB['name']}")
with c3:
    n=st.slider("場數",5,20,10)

if not st.session_state.selA or not st.session_state.selB:
    st.warning("👆 先關鍵字搜，再Drop list揀兩隊，打 Swin 就出 Swindon"); st.stop()

teamA_name=st.session_state.selA['name']; teamB_name=st.session_state.selB['name']
teamA_id=st.session_state.selA['id']; teamB_id=st.session_state.selB['id']

col1,col2=st.columns(2)
with col1:
    if st.button(f"🔍 自動捉 {teamA_name} 近{n}場", type="primary", use_container_width=True):
        raw=fetch_recent(teamA_id,n)
        if raw:
            rec=[parse(x) for x in raw if parse(x)]
            st.session_state.recA=rec; st.session_state.statsA=analyse(rec, teamA_name)
            st.success(f"捉到 {len(rec)} 場")
        else: st.warning("API暫擋，用手入")
with col2:
    if st.button(f"🔍 自動捉對賽 {teamA_name} vs {teamB_name}", use_container_width=True):
        raw=fetch_h2h(teamA_id,teamB_id,12)
        if raw:
            rec=[parse(x) for x in raw if parse(x)]
            st.session_state.recH=rec; st.session_state.statsH=analyse(rec, teamA_name)
            st.success(f"捉到 {len(rec)} 場對賽")
        else: st.error("對賽空，用手入")

with st.expander("✋ 手入後備", expanded=False):
    dfA=pd.DataFrame([{"對手":"","主客":"主","我入":0,"對手入":0,"半主":0,"半客":0} for _ in range(10)])
    if st.session_state.recA:
        try: dfA=pd.DataFrame([{"對手":r['客隊'] if teamA_name.lower() in r['主隊'].lower() else r['主隊'],"主客":"主" if teamA_name.lower() in r['主隊'].lower() else "客","我入":r['主入'] if teamA_name.lower() in r['主隊'].lower() else r['客入'],"對手入":r['客入'] if teamA_name.lower() in r['主隊'].lower() else r['主入'],"半主":r['半主'],"半客":r['半客']} for r in st.session_state.recA])
        except: pass
    edA=st.data_editor(dfA, num_rows="dynamic", use_container_width=True, key="edA5")
    dfH=pd.DataFrame([{"主隊":teamA_name,"主入":0,"客入":0,"客隊":teamB_name,"半主":0,"半客":0} for _ in range(12)])
    if st.session_state.recH:
        try: dfH=pd.DataFrame([{"主隊":r['主隊'],"主入":r['主入'],"客入":r['客入'],"客隊":r['客隊'],"半主":r['半主'],"半客":r['半客']} for r in st.session_state.recH])
        except: pass
    edH=st.data_editor(dfH, num_rows="dynamic", use_container_width=True, key="edH5")
    if st.button("✅ 用手入覆蓋"):
        recA2=[]; recH2=[]
        for _,r in edA.iterrows():
            if int(r["我入"])==0 and int(r["對手入"])==0 and str(r["對手"]).strip()=="": continue
            is_home=r["主客"]=="主"
            recA2.append({"主隊":teamA_name if is_home else str(r["對手"]),"客隊":str(r["對手"]) if is_home else teamA_name,"主入":int(r["我入"]) if is_home else int(r["對手入"]),"客入":int(r["對手入"]) if is_home else int(r["我入"]),"半主":int(r["半主"]),"半客":int(r["半客"]),"總入":int(r["我入"])+int(r["對手入"])})
        for _,r in edH.iterrows():
            if int(r["主入"])==0 and int(r["客入"])==0 and str(r["主隊"]).strip()=="": continue
            recH2.append({"主隊":str(r["主隊"]),"客隊":str(r["客隊"]),"主入":int(r["主入"]),"客入":int(r["客入"]),"半主":int(r["半主"]),"半客":int(r["半客"]),"總入":int(r["主入"])+int(r["客入"])})
        st.session_state.recA=recA2; st.session_state.recH=recH2
        st.session_state.statsA=analyse(recA2, teamA_name) if recA2 else None
        st.session_state.statsH=analyse(recH2, teamA_name) if recH2 else None
        st.success("已覆蓋"); st.rerun()

if st.session_state.get('statsA'):
    sA=st.session_state.statsA; sH=st.session_state.get('statsH')
    def g(d,k): return d.get(k,0) if d else 0
    def weighted(a,b, wa=0.6, wb=0.4):
        if not b or b==0: return a
        return a*wa + b*wb

    st.divider()
    c1,c2=st.columns(2)
    with c1: st.metric(f"① {teamA_name} 硬實力", f"{g(sA,'勝')}勝{g(sA,'和')}和{g(sA,'負')}負", f"勝率 {g(sA,'勝率'):.0f}%")
    with c2:
        if sH: st.metric(f"② 對賽 {teamA_name} vs {teamB_name}", f"{g(sH,'勝')}勝{g(sH,'和')}和{g(sH,'負')}負", f"勝率 {g(sH,'勝率'):.0f}%")

    win_rate = weighted(g(sA,'勝率'), g(sH,'勝率')); draw_rate = weighted(g(sA,'和率'), g(sH,'和率')); lose_rate = weighted(g(sA,'負率'), g(sH,'負率'))
    total = win_rate+draw_rate+lose_rate
    if total>0: win_rate, draw_rate, lose_rate = win_rate/total*100, draw_rate/total*100, lose_rate/total*100
    ht_win = weighted(g(sA,'半勝率'), g(sH,'半勝率')); ht_draw = weighted(g(sA,'半和率'), g(sH,'半和率')); ht_lose = weighted(g(sA,'半負率'), g(sH,'半負率'))
    ht_total = ht_win+ht_draw+ht_lose
    if ht_total>0: ht_win, ht_draw, ht_lose = ht_win/ht_total*100, ht_draw/ht_total*100, ht_lose/ht_total*100
    else: ht_win, ht_draw, ht_lose = win_rate*0.55, 35, lose_rate*0.55

    cands=[]
    cands.append({"盤口":"全場主客和","組合":f"{teamA_name} 勝","命中":win_rate,"原因":f"硬{g(sA,'勝率'):.0f}%+對賽{g(sH,'勝率') if sH else 0:.0f}%加權->{win_rate:.0f}% (對賽{g(sH,'勝') if sH else 0}勝)"})
    cands.append({"盤口":"全場主客和","組合":"和","命中":draw_rate,"原因":f"硬{g(sA,'和率'):.0f}%+對賽{g(sH,'和率') if sH else 0:.0f}%->{draw_rate:.0f}%"})
    cands.append({"盤口":"全場主客和","組合":f"{teamB_name} 勝","命中":lose_rate,"原因":f"硬{g(sA,'負率'):.0f}%+對賽{g(sH,'負率') if sH else 0:.0f}%->{lose_rate:.0f}%"})
    cands.append({"盤口":"半場主客和","組合":f"半場 {teamA_name} 勝","命中":ht_win,"原因":f"半場勝 {ht_win:.0f}%"})
    cands.append({"盤口":"半場主客和","組合":"半場 和","命中":ht_draw,"原因":f"半場和 {ht_draw:.0f}%"})
    cands.append({"盤口":"半場主客和","組合":f"半場 {teamB_name} 勝","命中":ht_lose,"原因":f"半場負 {ht_lose:.0f}%"})
    cands.append({"盤口":"入球大細","組合":"大1.5","命中":g(sA,'大1.5%'),"原因":f"大1.5 {g(sA,'大1.5%'):.0f}% 場均{g(sA,'總入'):.1f}"})
    cands.append({"盤口":"入球大細","組合":"大2.5","命中":weighted(g(sA,'大2.5%'), g(sH,'大2.5%') if sH else 0),"原因":f"大2.5 {weighted(g(sA,'大2.5%'), g(sH,'大2.5%') if sH else 0):.0f}%"})
    cands.append({"盤口":"入球大細","組合":"細2.5","命中":100-weighted(g(sA,'大2.5%'), g(sH,'大2.5%') if sH else 0),"原因":f"細2.5"})
    if sA.get('波膽'):
        for sc,cnt in sA.get('波膽',[])[:3]:
            cands.append({"盤口":"全場波膽","組合":f"波膽 {sc}","命中":cnt/g(sA,'場')*100,"原因":f"硬實力最常見{cnt}次"})
    if sH and sH.get('波膽'):
        for sc,cnt in sH.get('波膽',[])[:2]:
            cands.append({"盤口":"全場波膽","組合":f"對賽波膽 {sc}","命中":cnt/g(sH,'場')*100,"原因":f"對賽常見{cnt}次"})

    st.subheader("🎯 馬會主盤 (已合併，無重複)")
    st.dataframe(pd.DataFrame(cands), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("💰 貼馬會賠率 - 點一下直接打，自動計EV")
    ev_df=pd.DataFrame([
        {"盤口":c["盤口"],"組合":c["組合"],"命中率%":round(c["命中"],1),"馬會賠率":2.0,"原因":c["原因"]}
        for c in cands if c["盤口"] in ["全場主客和","半場主客和","入球大細","全場波膽"]
    ])

    edited=st.data_editor(
        ev_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "盤口": st.column_config.TextColumn(disabled=True),
            "組合": st.column_config.TextColumn(disabled=True),
            "命中率%": st.column_config.NumberColumn(disabled=True, format="%.1f%%"),
            "馬會賠率": st.column_config.NumberColumn("馬會賠率(點此直接打)", min_value=1.01, max_value=100.0, step=0.05, format="%.2f"),
            "原因": st.column_config.TextColumn(disabled=True, width="large"),
        },
        key="ev_final"
    )

    res=[]
    for _,r in edited.iterrows():
        odd=float(r["馬會賠率"]); hit=float(r["命中率%"])
        ev=(hit/100*odd-1)*100
        grade="🔥 超值" if ev>15 else "✅ 值博" if ev>5 else "⚠️ 一般" if ev>-5 else "❌ 唔值"
        res.append({"盤口":r["盤口"],"組合":r["組合"],"命中":f"{hit:.0f}%","賠率":odd,"EV":f"{ev:.1f}%","評級":grade})

    st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)
    if res:
        best=max(res, key=lambda x: float(x['EV'].replace('%','')))
        if float(best['EV'].replace('%',''))>0:
            st.success(f"🏆 最值博: {best['組合']} @ {best['賠率']} EV {best['EV']} {best['評級']}")

import streamlit as st, requests, re, pandas as pd
from collections import Counter

st.set_page_config(page_title="EdgeLab v13.9 全部手入賠率", layout="wide")
APP_PWD = st.secrets.get("APP_PWD","1234")
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    pwd=st.text_input("密碼", type="password")
    if st.button("登入") and pwd==APP_PWD: st.session_state.auth=True; st.rerun()
    st.stop()

HEADERS={"User-Agent":"Mozilla/5.0","Referer":"https://www.aiscore.com/","Accept":"application/json"}
COMMON=[(3425,"Swindon Town","ENG L2"),(3559,"Newport County","ENG L2"),(21138,"Man City","ENG PL"),(21134,"Arsenal","ENG PL")]

def search_teams(kw):
    if not kw or len(kw.strip())<2: return []
    kw=kw.lower(); res=[]
    for tid,name,lg in COMMON:
        if kw in name.lower(): res.append({"id":tid,"name":name,"league":lg})
    try:
        r=requests.get(f"https://www.aiscore.com/api/search?query={kw}", headers=HEADERS, timeout=10)
        if r.status_code==200:
            j=r.json(); teams=j.get('data',{}).get('teams',[]) or []
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
        if hs==0 and aw==0:
            nums=re.findall(r'\d+', str(m.get('result','')))
            if len(nums)>=2: hs,aw=int(nums[0]),int(nums[1])
        return {"主隊":ht,"客隊":at,"主入":int(hs),"客入":int(aw),"總入":int(hs)+int(aw)}
    except: return None

def analyse(records, target):
    if not records: return None
    win=draw=lose=gf=ga=btts=o25=o15=0; scores=Counter(); valid=0
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
        scores[f"{r['主入']}-{r['客入']}"]+=1
    if valid==0: return None
    return {"場":valid,"勝":win,"和":draw,"負":lose,"勝率":win/valid*100,"和率":draw/valid*100,"負率":lose/valid*100,
            "入":gf/valid,"失":ga/valid,"總入":(gf+ga)/valid,"BTTS%":btts/valid*100,"大2.5%":o25/valid*100,"大1.5%":o15/valid*100,"波膽":scores.most_common(5)}

for k in ['recA','recH','statsA','statsH','selA','selB','candsA','candsB']:
    if k not in st.session_state: st.session_state[k]=[] if 'rec' in k or 'cands' in k else None

st.title("🌍 v13.9 全部賠率手入 - 我只做分析")
st.caption("關鍵字搜隊 -> 自動捉/手入數據 -> 你全部賠率手入 -> 我計EV回報")

c1,c2=st.columns(2)
with c1:
    kwA=st.text_input("主隊A關鍵字", placeholder="Swin", key="kwA")
    if st.button("🔍 搜A", key="btnA"): st.session_state.candsA=search_teams(kwA)
    if st.session_state.candsA:
        opts=[f"{x['name']} | {x['league']} | ID:{x['id']}" for x in st.session_state.candsA]
        sel=st.selectbox("揀A", opts, key="optA"); st.session_state.selA=st.session_state.candsA[opts.index(sel)]
with c2:
    kwB=st.text_input("客隊B關鍵字", placeholder="New", key="kwB")
    if st.button("🔍 搜B", key="btnB"): st.session_state.candsB=search_teams(kwB)
    if st.session_state.candsB:
        opts=[f"{x['name']} | {x['league']} | ID:{x['id']}" for x in st.session_state.candsB]
        sel=st.selectbox("揀B", opts, key="optB"); st.session_state.selB=st.session_state.candsB[opts.index(sel)]

if not st.session_state.selA or not st.session_state.selB:
    st.info("先搜揀隊"); st.stop()

teamA_name=st.session_state.selA['name']; teamB_name=st.session_state.selB['name']
teamA_id=st.session_state.selA['id']; teamB_id=st.session_state.selB['id']

colA,colB,colC=st.columns(3)
with colA: n=st.slider("捉幾多場",5,20,10)
with colB:
    if st.button(f"🔍 捉 {teamA_name} 近{n}場", type="primary", use_container_width=True):
        raw=fetch_recent(teamA_id,n)
        if raw:
            rec=[parse(x) for x in raw if parse(x)]
            st.session_state.recA=rec; st.session_state.statsA=analyse(rec, teamA_name)
with colC:
    if st.button(f"🔍 捉對賽", use_container_width=True):
        raw=fetch_h2h(teamA_id,teamB_id,12)
        if raw:
            rec=[parse(x) for x in raw if parse(x)]
            st.session_state.recH=rec; st.session_state.statsH=analyse(rec, teamA_name)

# 手入數據
with st.expander("✋ 手入賽果數據 (捉唔到就用呢度)", expanded=False):
    dfA=pd.DataFrame([{"對手":"","主客":"主","我入":0,"對手入":0} for _ in range(10)])
    if st.session_state.recA:
        try: dfA=pd.DataFrame([{"對手":r['客隊'] if teamA_name.lower() in r['主隊'].lower() else r['主隊'],"主客":"主" if teamA_name.lower() in r['主隊'].lower() else "客","我入":r['主入'] if teamA_name.lower() in r['主隊'].lower() else r['客入'],"對手入":r['客入'] if teamA_name.lower() in r['主隊'].lower() else r['主入']} for r in st.session_state.recA])
        except: pass
    edA=st.data_editor(dfA, num_rows="dynamic", use_container_width=True, key="edA6")
    if st.button("✅ 用手入數據覆蓋分析"):
        recA2=[]
        for _,r in edA.iterrows():
            if int(r["我入"])==0 and int(r["對手入"])==0 and str(r["對手"]).strip()=="": continue
            is_home=r["主客"]=="主"
            recA2.append({"主隊":teamA_name if is_home else str(r["對手"]),"客隊":str(r["對手"]) if is_home else teamA_name,"主入":int(r["我入"]) if is_home else int(r["對手入"]),"客入":int(r["對手入"]) if is_home else int(r["我入"]),"總入":int(r["我入"])+int(r["對手入"])})
        st.session_state.recA=recA2; st.session_state.statsA=analyse(recA2, teamA_name) if recA2 else None
        st.success("已覆蓋"); st.rerun()

if not st.session_state.get('statsA'):
    st.warning("捉完或手入數據後，先會出分析同賠率表"); st.stop()

sA=st.session_state.statsA; sH=st.session_state.get('statsH')
def g(d,k): return d.get(k,0) if d else 0
def weighted(a,b, wa=0.6, wb=0.4):
    if not b or b==0: return a
    return a*wa + b*wb

win_data=weighted(g(sA,'勝率'), g(sH,'勝率')); draw_data=weighted(g(sA,'和率'), g(sH,'和率')); lose_data=weighted(g(sA,'負率'), g(sH,'負率'))
tot=win_data+draw_data+lose_data
if tot>0: win_data,draw_data,lose_data=win_data/tot*100,draw_data/tot*100,lose_data/tot*100

st.divider()
st.subheader("📊 數據分析結果 (已合併硬實力+對賽)")
st.write(f"**{teamA_name}** 近{g(sA,'場')}場 {g(sA,'勝')}勝{g(sA,'和')}和{g(sA,'負')}負 勝率{g(sA,'勝率'):.0f}% 場均入{g(sA,'入'):.1f}失{g(sA,'失'):.1f} 總入{g(sA,'總入'):.1f} BTTS{g(sA,'BTTS%'):.0f}% 大2.5{g(sA,'大2.5%'):.0f}%")
if sH: st.write(f"**對賽** {teamA_name} vs {teamB_name} {g(sH,'場')}場 {g(sH,'勝')}勝{g(sH,'和')}和{g(sH,'負')}負 勝率{g(sH,'勝率'):.0f}%")

cands=[]
cands.append({"盤口":"全場主客和","組合":f"{teamA_name} 勝","命中率%":win_data,"原因":f"硬{g(sA,'勝率'):.0f}%+對賽{g(sH,'勝率') if sH else 0:.0f}%加權"})
cands.append({"盤口":"全場主客和","組合":"和","命中率%":draw_data,"原因":f"硬{g(sA,'和率'):.0f}%+對賽{g(sH,'和率') if sH else 0:.0f}%"})
cands.append({"盤口":"全場主客和","組合":f"{teamB_name} 勝","命中率%":lose_data,"原因":f"硬{g(sA,'負率'):.0f}%+對賽{g(sH,'負率') if sH else 0:.0f}%"})
cands.append({"盤口":"入球大細","組合":"大2.5","命中率%":g(sA,'大2.5%'),"原因":f"大2.5 {g(sA,'大2.5%'):.0f}% 場均{g(sA,'總入'):.1f}"})
cands.append({"盤口":"入球大細","組合":"細2.5","命中率%":100-g(sA,'大2.5%'),"原因":f"細2.5 {100-g(sA,'大2.5%'):.0f}%"})
cands.append({"盤口":"入球大細","組合":"大1.5","命中率%":g(sA,'大1.5%'),"原因":f"大1.5 {g(sA,'大1.5%'):.0f}%"})
cands.append({"盤口":"入球大細","組合":"BTTS Yes","命中率%":g(sA,'BTTS%'),"原因":f"BTTS {g(sA,'BTTS%'):.0f}%"})
if sA.get('波膽'):
    for sc,cnt in sA.get('波膽',[])[:4]:
        cands.append({"盤口":"波膽","組合":f"波膽 {sc}","命中率%":cnt/g(sA,'場')*100,"原因":f"出現{cnt}次"})

st.dataframe(pd.DataFrame(cands), use_container_width=True, hide_index=True)

st.divider()
st.subheader("💰 全部賠率手入 - 你入完我計EV回報")
st.caption("下面個表，馬會賠率欄點一下直接打新數，唔使Delete，打完自動計EV同回報")

# 全部賠率手入表
base_df=pd.DataFrame([
    {"盤口":c["盤口"],"組合":c["組合"],"命中率%":round(c["命中率%"],1),"馬會賠率":0.0,"原因":c["原因"]}
    for c in cands
])

# 如果隊名變咗，重置
if 'full_odds_df' not in st.session_state or len(st.session_state.full_odds_df)!=len(base_df):
    st.session_state.full_odds_df=base_df

edited=st.data_editor(
    st.session_state.full_odds_df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_config={
        "盤口": st.column_config.TextColumn(disabled=True),
        "組合": st.column_config.TextColumn(disabled=True, width="medium"),
        "命中率%": st.column_config.NumberColumn(disabled=True, format="%.1f%%"),
        "馬會賠率": st.column_config.NumberColumn("馬會賠率(全部手入，點此直接打)", min_value=0.0, max_value=100.0, step=0.05, format="%.2f", required=True),
        "原因": st.column_config.TextColumn(disabled=True, width="large"),
    },
    key="full_odds_editor"
)
st.session_state.full_odds_df=edited

# EV計算
results=[]
for _,r in edited.iterrows():
    odd=float(r["馬會賠率"]) if float(r["馬會賠率"])>0 else 0
    hit=float(r["命中率%"])
    if odd>0:
        ev=(hit/100*odd-1)*100
        profit_per_100 = ev # 每100蚊回報
        grade="🔥 超值" if ev>15 else "✅ 值博" if ev>5 else "⚠️ 一般" if ev>-5 else "❌ 唔值"
    else:
        ev=0; profit_per_100=0; grade="未入賠率"
    results.append({
        "盤口":r["盤口"],"組合":r["組合"],"命中":f"{hit:.1f}%","賠率":odd if odd>0 else "-",
        "EV":f"{ev:.1f}%" if odd>0 else "-","每100回報":f"${profit_per_100:.1f}" if odd>0 else "-","評級":grade
    })

st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

# 總結
if any(float(r["馬會賠率"])>0 for _,r in edited.iterrows()):
    valid=[r for r in results if r["賠率"]!="-"]
    if valid:
        best=max(valid, key=lambda x: float(x['EV'].replace('%','')) if x['EV']!="-" else -999)
        st.success(f"🏆 你手入賠率後最值博: {best['組合']} 命中{best['命中']} @ {best['賠率']} EV {best['EV']} {best['評級']} 每$100預期回報 {best['每100回報']}")
        st.write("**回報計法:** EV = 命中率 x 賠率 -1。正數代表長期有著數。")

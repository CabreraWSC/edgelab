import streamlit as st, requests, re, pandas as pd
from collections import Counter

st.set_page_config(page_title="EdgeLab v13.8 修復", layout="wide")
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
        hhs=m.get('homeHalfScore',0); haws=m.get('awayHalfScore',0)
        if isinstance(m.get('halfScore'),dict):
            hhs=m.get('halfScore',{}).get('home',0); haws=m.get('halfScore',{}).get('away',0)
        if hs==0 and aw==0:
            nums=re.findall(r'\d+', str(m.get('result','')))
            if len(nums)>=2: hs,aw=int(nums[0]),int(nums[1])
        return {"主隊":ht,"客隊":at,"主入":int(hs),"客入":int(aw),"半主":int(hhs or 0),"半客":int(haws or 0),"總入":int(hs)+int(aw)}
    except: return None

def analyse(records, target):
    if not records: return None
    win=draw=lose=gf=ga=btts=o25=o15=0; ht_w=ht_d=ht_l=0; scores=Counter(); valid=0
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
        if r['半主']!=0 or r['半客']!=0:
            my_ht=r['半主'] if is_home else r['半客']; opp_ht=r['半客'] if is_home else r['半主']
            if my_ht>opp_ht: ht_w+=1
            elif my_ht==opp_ht: ht_d+=1
            else: ht_l+=1
    if valid==0: return None
    return {"場":valid,"勝":win,"和":draw,"負":lose,"勝率":win/valid*100,"和率":draw/valid*100,"負率":lose/valid*100,
            "半勝":ht_w,"半和":ht_d,"半負":ht_l,"半勝率":ht_w/valid*100,"半和率":ht_d/valid*100,"半負率":ht_l/valid*100,
            "入":gf/valid,"失":ga/valid,"總入":(gf+ga)/valid,"BTTS%":btts/valid*100,"大2.5%":o25/valid*100,"大1.5%":o15/valid*100,"波膽":scores.most_common(5)}

for k in ['recA','recH','statsA','statsH','selA','selB','candsA','candsB']:
    if k not in st.session_state: st.session_state[k]=[] if 'rec' in k or 'cands' in k else None

st.title("🌍 v13.8 先入賠率再校正 - 修復版")
st.caption("先入馬會主客和賠率 -> 再捉 -> 賠率校正分析")

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

st.divider()
st.subheader("① 先入馬會全場主客和賠率 (直接打，唔使Delete)")
if 'market_df' not in st.session_state:
    st.session_state.market_df=pd.DataFrame([
        {"組合":f"{teamA_name} 勝","馬會賠率":1.95},
        {"組合":"和","馬會賠率":3.30},
        {"組合":f"{teamB_name} 勝","馬會賠率":3.80},
    ])
if st.session_state.market_df.iloc[0]['組合']!=f"{teamA_name} 勝":
    st.session_state.market_df=pd.DataFrame([
        {"組合":f"{teamA_name} 勝","馬會賠率":1.95},
        {"組合":"和","馬會賠率":3.30},
        {"組合":f"{teamB_name} 勝","馬會賠率":3.80},
    ])

market_edited=st.data_editor(
    st.session_state.market_df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_config={
        "組合": st.column_config.TextColumn(disabled=True),
        "馬會賠率": st.column_config.NumberColumn("賠率(點此直接打)", min_value=1.01, max_value=100.0, step=0.05, format="%.2f"),
    },
    key="market_editor"
)
st.session_state.market_df=market_edited

try:
    o1=float(market_edited.iloc[0]['馬會賠率']); oX=float(market_edited.iloc[1]['馬會賠率']); o2=float(market_edited.iloc[2]['馬會賠率'])
    p1=1/o1; pX=1/oX; p2=1/o2; over=p1+pX+p2
    imp1=p1/over*100; impX=pX/over*100; imp2=p2/over*100
    st.info(f"馬會隱含(去水): {teamA_name}勝 {imp1:.1f}% | 和 {impX:.1f}% | {teamB_name}勝 {imp2:.1f}% | 水位 {over*100-100:.1f}%")
except:
    o1,oX,o2=1.95,3.3,3.8; imp1,impX,imp2=33.3,33.3,33.3

st.divider()
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

if not st.session_state.get('statsA'):
    st.warning("入完賠率後按捉波"); st.stop()

sA=st.session_state.statsA; sH=st.session_state.get('statsH')
def g(d,k): return d.get(k,0) if d else 0
def weighted(a,b, wa=0.6, wb=0.4):
    if not b or b==0: return a
    return a*wa + b*wb

win_data=weighted(g(sA,'勝率'), g(sH,'勝率')); draw_data=weighted(g(sA,'和率'), g(sH,'和率')); lose_data=weighted(g(sA,'負率'), g(sH,'負率'))
final_win = win_data*0.5 + imp1*0.5; final_draw = draw_data*0.5 + impX*0.5; final_lose = lose_data*0.5 + imp2*0.5
tot=final_win+final_draw+final_lose
final_win, final_draw, final_lose = final_win/tot*100, final_draw/tot*100, final_lose/tot*100

st.subheader("🎯 校正後分析 (數據+對賽+馬會)")
cands=[]
cands.append({"盤口":"全場主客和","組合":f"{teamA_name} 勝","數據":f"{win_data:.0f}%","市場":f"{imp1:.0f}%","校正後":f"{final_win:.1f}%","值":final_win,"原因":f"硬{g(sA,'勝率'):.0f}%+對賽{g(sH,'勝率') if sH else 0:.0f}% vs 馬會{imp1:.0f}%"})
cands.append({"盤口":"全場主客和","組合":"和","數據":f"{draw_data:.0f}%","市場":f"{impX:.0f}%","校正後":f"{final_draw:.1f}%","值":final_draw,"原因":f"硬{g(sA,'和率'):.0f}% vs 馬會{impX:.0f}%"})
cands.append({"盤口":"全場主客和","組合":f"{teamB_name} 勝","數據":f"{lose_data:.0f}%","市場":f"{imp2:.0f}%","校正後":f"{final_lose:.1f}%","值":final_lose,"原因":f"硬{g(sA,'負率'):.0f}% vs 馬會{imp2:.0f}%"})
st.dataframe(pd.DataFrame(cands), use_container_width=True, hide_index=True)

st.subheader("💰 EV (用你入嘅賠率計)")
ev_rows=[]
odds_map={f"{teamA_name} 勝":o1,"和":oX,f"{teamB_name} 勝":o2}
for c in cands:
    odd=odds_map.get(c['組合'],2.0)
    ev=(c['值']/100*odd-1)*100
    grade="🔥 超值" if ev>15 else "✅ 值博" if ev>5 else "⚠️ 一般" if ev>-5 else "❌ 唔值"
    ev_rows.append({"組合":c['組合'],"校正命中":c['校正後'],"你入賠率":odd,"EV":f"{ev:.1f}%","評級":grade,"解讀":c['原因']})
st.dataframe(pd.DataFrame(ev_rows), use_container_width=True, hide_index=True)
if ev_rows:
    best=max(ev_rows, key=lambda x: float(x['EV'].replace('%','')))
    st.success(f"🏆 最值博: {best['組合']} {best['校正命中']} @ {best['你入賠率']} EV {best['EV']} {best['評級']}")

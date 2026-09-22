import streamlit as st, requests, re, pandas as pd
from collections import Counter

st.set_page_config(page_title="EdgeLab v14.3.1 修復", layout="wide")
APP_PWD = st.secrets.get("APP_PWD","1234")
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    pwd=st.text_input("密碼", type="password")
    if st.button("登入") and pwd==APP_PWD: st.session_state.auth=True; st.rerun()
    st.stop()

HEADERS={"User-Agent":"Mozilla/5.0"}
COMMON=[(3425,"Swindon Town"),(3559,"Newport County"),(21138,"Man City"),(21134,"Arsenal")]

def search_teams(kw):
    if not kw or len(kw.strip())<2: return []
    kw=kw.lower(); res=[]
    for tid,name in COMMON:
        if kw in name.lower(): res.append({"id":tid,"name":name})
    try:
        r=requests.get(f"https://www.aiscore.com/api/search?query={kw}", headers=HEADERS, timeout=8)
        if r.status_code==200:
            j=r.json(); teams=j.get('data',{}).get('teams',[]) or []
            if isinstance(teams,dict): teams=teams.get('teams',[])
            for t in teams[:12]:
                tid=t.get('id'); tname=t.get('name') or t.get('teamName','')
                if tid and tname and tid not in [x['id'] for x in res]:
                    res.append({"id":tid,"name":tname})
    except: pass
    return res[:12]

def fetch_recent(tid,n):
    try:
        r=requests.get(f"https://www.aiscore.com/api/football/team/matches?teamId={tid}&count={n}", headers=HEADERS, timeout=8)
        j=r.json(); d=j.get('data',j)
        if isinstance(d,dict) and 'matches' in d: d=d['matches']
        return d if isinstance(d,list) else []
    except: return []
def fetch_h2h(id1,id2,n):
    try:
        r=requests.get(f"https://www.aiscore.com/api/football/match/h2h?teamId1={id1}&teamId2={id2}&count={n}", headers=HEADERS, timeout=8)
        j=r.json(); d=j.get('data',j)
        if isinstance(d,dict) and 'matches' in d: d=d['matches']
        return d if isinstance(d,list) else []
    except: return []
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
        return {"主隊":ht,"客隊":at,"主入":int(hs),"客入":int(aw),"半主":int(hhs),"半客":int(haws),"總入":int(hs)+int(aw)}
    except: return None

def analyse(records, target):
    if not records: return None
    win=draw=lose=gf=ga=btts=o25=o15=0; ht_w=ht_d=ht_l=0; scores=Counter(); ht_scores=Counter(); valid=0
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
        ht_scores[f"{r['半主']}-{r['半客']}"]+=1
        my_ht=r['半主'] if is_home else r['半客']; opp_ht=r['半客'] if is_home else r['半主']
        if my_ht>opp_ht: ht_w+=1
        elif my_ht==opp_ht: ht_d+=1
        else: ht_l+=1
    if valid==0: return None
    return {"場":valid,"勝":win,"和":draw,"負":lose,"勝率":win/valid*100,"和率":draw/valid*100,"負率":lose/valid*100,
            "半勝":ht_w,"半和":ht_d,"半負":ht_l,"半勝率":ht_w/valid*100,"半和率":ht_d/valid*100,"半負率":ht_l/valid*100,
            "入":gf/valid,"失":ga/valid,"總入":(gf+ga)/valid,"BTTS%":btts/valid*100,"大2.5%":o25/valid*100,"大1.5%":o15/valid*100,
            "波膽":scores,"半波膽":ht_scores}

for k in ['recA','recH','statsA','statsH','selA','selB','candsA','candsB']:
    if k not in st.session_state: st.session_state[k]=[] if 'rec' in k or 'cands' in k else None
if 'odds' not in st.session_state: st.session_state.odds={}

st.title("v14.3.1 完整版 - 修復ValueError")

c1,c2=st.columns(2)
with c1:
    kwA=st.text_input("主隊A關鍵字", placeholder="Swin", key="kwA")
    if st.button("🔍 搜A", key="btnA"): st.session_state.candsA=search_teams(kwA)
    if st.session_state.candsA:
        opts=[f"{x['name']} | ID:{x['id']}" for x in st.session_state.candsA]
        sel=st.selectbox("揀主隊A", opts, key="optA"); st.session_state.selA=st.session_state.candsA[opts.index(sel)]
with c2:
    kwB=st.text_input("客隊B關鍵字", placeholder="New", key="kwB")
    if st.button("🔍 搜B", key="btnB"): st.session_state.candsB=search_teams(kwB)
    if st.session_state.candsB:
        opts=[f"{x['name']} | ID:{x['id']}" for x in st.session_state.candsB]
        sel=st.selectbox("揀客隊B", opts, key="optB"); st.session_state.selB=st.session_state.candsB[opts.index(sel)]

if not st.session_state.selA or not st.session_state.selB:
    st.info("先搜揀隊"); st.stop()

teamA_name=st.session_state.selA['name']; teamB_name=st.session_state.selB['name']
teamA_id=st.session_state.selA['id']; teamB_id=st.session_state.selB['id']

colA,colB=st.columns(2)
with colA:
    n=st.slider("捉幾多場",5,20,10, key="n_slider")
    if st.button(f"捉 {teamA_name} 對其他隊近{n}場", type="primary", use_container_width=True, key="btnA2"):
        raw=fetch_recent(teamA_id,n)
        if raw:
            rec=[parse(x) for x in raw if parse(x)]
            st.session_state.recA=rec; st.session_state.statsA=analyse(rec, teamA_name)
with colB:
    if st.button(f"捉 {teamA_name} vs {teamB_name} 對賽", use_container_width=True, key="btnH2"):
        raw=fetch_h2h(teamA_id,teamB_id,12)
        if raw:
            rec=[parse(x) for x in raw if parse(x)]
            st.session_state.recH=rec; st.session_state.statsH=analyse(rec, teamA_name)

sA=st.session_state.get('statsA'); sH=st.session_state.get('statsH')
if not sA and not sH:
    st.warning("要捉主隊對其他隊 同 對賽"); st.stop()

def g(d,k): return d.get(k,0) if d else 0
def weighted(a,b, wa=0.6, wb=0.4): return a*wa + b*wb if b and b>0 else a

win_A=g(sA,'勝率') if sA else 0; draw_A=g(sA,'和率') if sA else 0; lose_A=g(sA,'負率') if sA else 0
win_H=g(sH,'勝率') if sH else 0; draw_H=g(sH,'和率') if sH else 0; lose_H=g(sH,'負率') if sH else 0
win_data=weighted(win_A, win_H); draw_data=weighted(draw_A, draw_H); lose_data=weighted(lose_A, lose_H)
tot=win_data+draw_data+lose_data
if tot>0: win_data,draw_data,lose_data=win_data/tot*100,draw_data/tot*100,lose_data/tot*100
else: win_data,draw_data,lose_data=33.3,33.3,33.3

ht_win=weighted(g(sA,'半勝率'), g(sH,'半勝率')); ht_draw=weighted(g(sA,'半和率'), g(sH,'半和率')); ht_lose=weighted(g(sA,'半負率'), g(sH,'半負率'))
ht_tot=ht_win+ht_draw+ht_lose
if ht_tot>0: ht_win,ht_draw,ht_lose=ht_win/ht_tot*100,ht_draw/ht_tot*100,ht_lose/ht_tot*100
else: ht_win,ht_draw,ht_lose=30,40,30

# 往績主客和
st.divider()
st.subheader("📊 往績主客和數據")
c1,c2=st.columns(2)
with c1:
    if sA:
        st.markdown(f"**① {teamA_name} 對其他隊 近{g(sA,'場')}場**")
        st.table(pd.DataFrame([
            {"": "全場", "主勝": f"{g(sA,'勝')}場 {g(sA,'勝率'):.1f}%", "和": f"{g(sA,'和')}場 {g(sA,'和率'):.1f}%", "客勝": f"{g(sA,'負')}場 {g(sA,'負率'):.1f}%"},
            {"": "半場", "主勝": f"{g(sA,'半勝')}場 {g(sA,'半勝率'):.1f}%", "和": f"{g(sA,'半和')}場 {g(sA,'半和率'):.1f}%", "客勝": f"{g(sA,'半負')}場 {g(sA,'半負率'):.1f}%"},
        ]))
    else: st.info("①未有")
with c2:
    if sH:
        st.markdown(f"**② 對賽 {teamA_name} vs {teamB_name} 近{g(sH,'場')}場**")
        st.table(pd.DataFrame([
            {"": "全場", "主勝": f"{g(sH,'勝')}場 {g(sH,'勝率'):.1f}%", "和": f"{g(sH,'和')}場 {g(sH,'和率'):.1f}%", "客勝": f"{g(sH,'負')}場 {g(sH,'負率'):.1f}%"},
            {"": "半場", "主勝": f"{g(sH,'半勝')}場 {g(sH,'半勝率'):.1f}%", "和": f"{g(sH,'半和')}場 {g(sH,'半和率'):.1f}%", "客勝": f"{g(sH,'半負')}場 {g(sH,'半負率'):.1f}%"},
        ]))
    else: st.info("②未有對賽")

# 修復呢行 - 唔可以喺f-string入面做if else format
avg_goals = g(sA,'總入') if sA else 0
avg_o25 = g(sA,'大2.5%') if sA else 0
st.info(f"→ 加權後 主勝{win_data:.1f}% 和{draw_data:.1f}% 客勝{lose_data:.1f}% | 半場 主{ht_win:.1f}% 和{ht_draw:.1f}% 客{ht_lose:.1f}% | 場均總入{avg_goals:.1f} 大2.5 {avg_o25:.0f}%")

st.divider()
st.subheader("💰 賠率手入")

def num_input(key):
    return st.number_input("賠率", min_value=0.0, max_value=100.0, value=float(st.session_state.odds.get(key,0.0)), step=0.05, format="%.2f", key=key, label_visibility="collapsed")

st.write("**全場主客和**")
c1,c2,c3=st.columns(3)
with c1:
    st.write(f"主 {teamA_name}")
    o_h=num_input(f"hhad_h_{teamA_name}")
    st.session_state.odds[f"hhad_h_{teamA_name}"]=o_h
    if o_h>0: st.caption(f"命中{win_data:.1f}% EV {(win_data/100*o_h-1)*100:.1f}%")
with c2:
    st.write("和")
    o_d=num_input("hhad_d")
    st.session_state.odds["hhad_d"]=o_d
    if o_d>0: st.caption(f"命中{draw_data:.1f}% EV {(draw_data/100*o_d-1)*100:.1f}%")
with c3:
    st.write(f"客 {teamB_name}")
    o_a=num_input(f"hhad_a_{teamB_name}")
    st.session_state.odds[f"hhad_a_{teamB_name}"]=o_a
    if o_a>0: st.caption(f"命中{lose_data:.1f}% EV {(lose_data/100*o_a-1)*100:.1f}%")

st.write("**半場主客和**")
c1,c2,c3=st.columns(3)
with c1:
    st.write(f"半場主 {teamA_name}")
    o_hh=num_input(f"hh_h_{teamA_name}")
    st.session_state.odds[f"hh_h_{teamA_name}"]=o_hh
    if o_hh>0: st.caption(f"命中{ht_win:.1f}% EV {(ht_win/100*o_hh-1)*100:.1f}%")
with c2:
    st.write("半場和")
    o_hd=num_input("hh_d")
    st.session_state.odds["hh_d"]=o_hd
    if o_hd>0: st.caption(f"命中{ht_draw:.1f}% EV {(ht_draw/100*o_hd-1)*100:.1f}%")
with c3:
    st.write(f"半場客 {teamB_name}")
    o_ha=num_input(f"hh_a_{teamB_name}")
    st.session_state.odds[f"hh_a_{teamB_name}"]=o_ha
    if o_ha>0: st.caption(f"命中{ht_lose:.1f}% EV {(ht_lose/100*o_ha-1)*100:.1f}%")

st.write("**入球大細 - 盤口可手入**")
df_ou=pd.DataFrame([
    {"盤口":"大2.5","過往":f"{g(sA,'大2.5%'):.1f}%" if sA else "0%","命中值":g(sA,'大2.5%') if sA else 0,"賠率":st.session_state.odds.get("ou_大2.5",0.0)},
    {"盤口":"細2.5","過往":f"{100-g(sA,'大2.5%'):.1f}%" if sA else "0%","命中值":100-g(sA,'大2.5%') if sA else 0,"賠率":st.session_state.odds.get("ou_細2.5",0.0)},
    {"盤口":"大1.5","過往":f"{g(sA,'大1.5%'):.1f}%" if sA else "0%","命中值":g(sA,'大1.5%') if sA else 0,"賠率":st.session_state.odds.get("ou_大1.5",0.0)},
])
edited_ou=st.data_editor(df_ou, use_container_width=True, hide_index=True, num_rows="dynamic",
    column_config={
        "盤口": st.column_config.TextColumn("盤口(可改名)"),
        "過往": st.column_config.TextColumn(disabled=True),
        "命中值": st.column_config.NumberColumn(disabled=True),
        "賠率": st.column_config.NumberColumn("馬會賠率(留空或直接打)", min_value=0.0, max_value=100.0, step=0.05, format="%.2f"),
    }, key="ou_ed")
for _,r in edited_ou.iterrows():
    st.session_state.odds[f"ou_{r['盤口']}"]=float(r["賠率"])

st.divider()
st.subheader("⚽ 波膽 - 馬會格仔 (賠率留空)")

scores_grid=[
    ["1-0","2-0","2-1","3-0","3-1","3-2","4-0","4-1","其他主勝"],
    ["0-0","1-1","2-2","0-1","0-2","1-2","0-3","1-3","其他客勝/和"],
]

combined_scores=Counter()
if sA and sA.get('波膽'): combined_scores+=sA.get('波膽')
if sH and sH.get('波膽'): combined_scores+=sH.get('波膽')
total_games=(g(sA,'場') if sA else 0)+(g(sH,'場') if sH else 0)

def get_hit(sc):
    if "其他" in sc: return 5.0
    return combined_scores.get(sc,0)/total_games*100 if total_games>0 else 0

for row in scores_grid:
    cols=st.columns(len(row))
    for i,sc in enumerate(row):
        with cols[i]:
            st.write(f"**{sc}**")
            hit=get_hit(sc)
            st.caption(f"過往{hit:.1f}%")
            o=num_input(f"cs_{sc}")
            st.session_state.odds[f"cs_{sc}"]=o
            if o>0:
                ev=(hit/100*o-1)*100
                st.caption(f"EV {ev:.1f}% {'🔥' if ev>15 else '✅' if ev>5 else ''}")

st.write("**半場波膽**")
ht_grid=[["1-0","2-0","0-0","1-1","0-1","0-2","其他"]]
for row in ht_grid:
    cols=st.columns(len(row))
    for i,sc in enumerate(row):
        with cols[i]:
            st.write(f"**半 {sc}**")
            ht_combined=Counter()
            if sA and sA.get('半波膽'): ht_combined+=sA.get('半波膽')
            hit=ht_combined.get(sc,0)/total_games*100 if total_games>0 else 0
            st.caption(f"過往{hit:.1f}%")
            o=num_input(f"hcs_{sc}")
            st.session_state.odds[f"hcs_{sc}"]=o
            if o>0:
                ev=(hit/100*o-1)*100
                st.caption(f"EV {ev:.1f}%")

st.divider()
rows=[]
for key,label,hit in [
    (f"hhad_h_{teamA_name}", f"全場 {teamA_name}勝", win_data),
    ("hhad_d", "全場 和", draw_data),
    (f"hhad_a_{teamB_name}", f"全場 {teamB_name}勝", lose_data),
    (f"hh_h_{teamA_name}", f"半場 {teamA_name}勝", ht_win),
    ("hh_d", "半場 和", ht_draw),
    (f"hh_a_{teamB_name}", f"半場 {teamB_name}勝", ht_lose),
]:
    o=st.session_state.odds.get(key,0)
    if o>0:
        ev=(hit/100*o-1)*100
        rows.append({"組合":label,"命中":f"{hit:.1f}%","賠率":o,"EV":f"{ev:.1f}%","回報/100":f"${ev:.1f}"})

for _,r in edited_ou.iterrows():
    o=float(r["賠率"])
    if o>0:
        ev=(float(r["命中值"])/100*o-1)*100
        rows.append({"組合":r["盤口"],"命中":r["過往"],"賠率":o,"EV":f"{ev:.1f}%","回報/100":f"${ev:.1f}"})

if rows:
    st.subheader("📈 總回報")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    best=max(rows, key=lambda x: float(x['EV'].replace('%','')))
    st.success(f"🏆 最值博: {best['組合']} {best['命中']} @ {best['賠率']} EV {best['EV']}")

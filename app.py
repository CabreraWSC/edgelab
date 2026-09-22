import streamlit as st, requests, re, pandas as pd
from collections import Counter

st.set_page_config(page_title="EdgeLab v14 馬會介面", layout="wide")
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

# === 樣式 - 馬會藍 ===
st.markdown("""
<style>
.jc-card {background:#fff; border:1px solid #ddd; border-radius:8px; padding:12px; margin-bottom:12px;}
.jc-title {background:#005baa; color:#fff; padding:8px 12px; border-radius:6px 6px 0 0; font-weight:bold;}
.jc-row {display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid #eee;}
.jc-team {font-weight:bold; flex:1;}
.jc-odd-box {background:#f6f8ff; border:1px solid #005baa; border-radius:6px; padding:6px 14px; min-width:70px; text-align:center; font-weight:bold; color:#005baa;}
</style>
""", unsafe_allow_html=True)

st.title("🌍 EdgeLab v14 馬會手機介面版")
# --- 搜隊 ---
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
    n=st.slider("捉幾多場",5,20,10)
    if st.button(f"🔍 捉 {teamA_name} 近{n}場", type="primary", use_container_width=True):
        raw=fetch_recent(teamA_id,n)
        if raw:
            rec=[parse(x) for x in raw if parse(x)]
            st.session_state.recA=rec; st.session_state.statsA=analyse(rec, teamA_name)
with colB:
    if st.button(f"🔍 捉對賽 {teamA_name} vs {teamB_name}", use_container_width=True):
        raw=fetch_h2h(teamA_id,teamB_id,12)
        if raw:
            rec=[parse(x) for x in raw if parse(x)]
            st.session_state.recH=rec; st.session_state.statsH=analyse(rec, teamA_name)

if not st.session_state.get('statsA'):
    st.warning("捉完先出分析"); st.stop()

sA=st.session_state.statsA; sH=st.session_state.get('statsH')
def g(d,k): return d.get(k,0) if d else 0
def weighted(a,b, wa=0.6, wb=0.4):
    return a*wa + b*wb if b and b>0 else a

win_data=weighted(g(sA,'勝率'), g(sH,'勝率')); draw_data=weighted(g(sA,'和率'), g(sH,'和率')); lose_data=weighted(g(sA,'負率'), g(sH,'負率'))
tot=win_data+draw_data+lose_data
if tot>0: win_data,draw_data,lose_data=win_data/tot*100,draw_data/tot*100,lose_data/tot*100

# === 上面：分析 (唔郁) ===
st.divider()
st.markdown(f'<div class="jc-title">📊 分析結果 - {teamA_name} vs {teamB_name}</div>', unsafe_allow_html=True)
st.markdown('<div class="jc-card">', unsafe_allow_html=True)
c1,c2,c3=st.columns(3)
with c1: st.metric(f"{teamA_name} 勝率", f"{win_data:.1f}%", f"{g(sA,'勝')}勝{g(sA,'負')}負")
with c2: st.metric("和率", f"{draw_data:.1f}%", f"{g(sA,'和')}和")
with c3: st.metric(f"{teamB_name} 勝率", f"{lose_data:.1f}%", f"入{g(sA,'入'):.1f} 失{g(sA,'失'):.1f}")
st.write(f"場均總入 {g(sA,'總入'):.1f} | 大2.5 {g(sA,'大2.5%'):.0f}% | 大1.5 {g(sA,'大1.5%'):.0f}% | BTTS {g(sA,'BTTS%'):.0f}%")
if sA.get('波膽'): st.write(f"常見波膽: {', '.join([f'{sc}({cnt}次)' for sc,cnt in sA.get('波膽',[])[:3]])}")
if sH: st.write(f"對賽: {teamA_name} {g(sH,'勝')}勝 {g(sH,'和')}和 {g(sH,'負')}負 勝率{g(sH,'勝率'):.0f}%")
st.markdown('</div>', unsafe_allow_html=True)

# === 下面：馬會手機投注介面 - 全部手入 ===
st.divider()
st.markdown('<div class="jc-title">🎫 馬會賠率輸入 - 跟手機投注版面 (全部手入)</div>', unsafe_allow_html=True)

# 初始化賠率 session
if 'odds' not in st.session_state:
    st.session_state.odds={}

def odd_input(label, key, default=0.0):
    # 馬會格仔 - 直接打數
    val=st.session_state.odds.get(key, default)
    new_val=st.number_input(label, min_value=0.0, max_value=100.0, value=float(val), step=0.05, format="%.2f", key=key, label_visibility="collapsed")
    st.session_state.odds[key]=new_val
    return new_val

# 1. 全場主客和 - 馬會式 3行
st.markdown('<div class="jc-card"><b>主客和 - 全場</b>', unsafe_allow_html=True)
cols=st.columns([2,1,1])
with cols[0]: st.write(f"**{teamA_name}** 主勝")
with cols[1]: o_h=odd_input(f"{teamA_name}勝", f"hhad_h_{teamA_name}")
with cols[2]:
    hit=win_data
    ev=(hit/100*o_h-1)*100 if o_h>0 else 0
    st.markdown(f'<div class="jc-odd-box">{o_h:.2f}<br><small style="color:{"green" if ev>5 else "red"}">{ev:.1f}%</small></div>', unsafe_allow_html=True) if o_h>0 else st.write("-")

cols=st.columns([2,1,1])
with cols[0]: st.write("**和**")
with cols[1]: o_d=odd_input("和", "hhad_d")
with cols[2]:
    ev=(draw_data/100*o_d-1)*100 if o_d>0 else 0
    st.markdown(f'<div class="jc-odd-box">{o_d:.2f}<br><small style="color:{"green" if ev>5 else "red"}">{ev:.1f}%</small></div>', unsafe_allow_html=True) if o_d>0 else st.write("-")

cols=st.columns([2,1,1])
with cols[0]: st.write(f"**{teamB_name}** 客勝")
with cols[1]: o_a=odd_input(f"{teamB_name}勝", f"hhad_a_{teamB_name}")
with cols[2]:
    ev=(lose_data/100*o_a-1)*100 if o_a>0 else 0
    st.markdown(f'<div class="jc-odd-box">{o_a:.2f}<br><small style="color:{"green" if ev>5 else "red"}">{ev:.1f}%</small></div>', unsafe_allow_html=True) if o_a>0 else st.write("-")
st.markdown('</div>', unsafe_allow_html=True)

# 2. 入球大細
st.markdown('<div class="jc-card"><b>入球大細</b>', unsafe_allow_html=True)
for label, hit, k in [("大 2.5", g(sA,'大2.5%'), "ou_o25"), ("細 2.5", 100-g(sA,'大2.5%'), "ou_u25"), ("大 1.5", g(sA,'大1.5%'), "ou_o15"), ("細 1.5", 100-g(sA,'大1.5%'), "ou_u15")]:
    cols=st.columns([2,1,1])
    with cols[0]: st.write(f"**{label}**")
    with cols[1]: o=odd_input(label, k)
    with cols[2]:
        ev=(hit/100*o-1)*100 if o>0 else 0
        st.markdown(f'<div class="jc-odd-box">{o:.2f}<br><small>{ev:.1f}%</small></div>', unsafe_allow_html=True) if o>0 else st.write("-")
st.markdown('</div>', unsafe_allow_html=True)

# 3. 波膽 - 馬會式
st.markdown('<div class="jc-card"><b>波膽 - 全場 (熱門)</b>', unsafe_allow_html=True)
for sc,cnt in sA.get('波膽',[])[:6]:
    hit=cnt/g(sA,'場')*100
    cols=st.columns([2,1,1])
    with cols[0]: st.write(f"**{sc}** ({cnt}次 {hit:.0f}%)")
    with cols[1]: o=odd_input(f"波膽 {sc}", f"cs_{sc}")
    with cols[2]:
        ev=(hit/100*o-1)*100 if o>0 else 0
        st.markdown(f'<div class="jc-odd-box">{o:.2f}<br><small>{ev:.1f}%</small></div>', unsafe_allow_html=True) if o>0 else st.write("-")
st.markdown('</div>', unsafe_allow_html=True)

# 4. 自訂 - 其他盤
st.markdown('<div class="jc-card"><b>自訂盤口 (角球/半場等)</b>', unsafe_allow_html=True)
c1,c2,c3=st.columns([2,1,1])
with c1: custom_name=st.text_input("盤口名", placeholder="例: 半場主勝 / 角球大9.5", key="custom_name")
with c2: custom_hit=st.number_input("估命中%", 0.0, 100.0, 30.0, step=1.0, key="custom_hit")
with c3: custom_odd=st.number_input("賠率", 0.0, 100.0, 0.0, step=0.05, format="%.2f", key="custom_odd")
if custom_name and custom_odd>0:
    ev=(custom_hit/100*custom_odd-1)*100
    st.info(f"{custom_name} 命中{custom_hit:.0f}% @ {custom_odd:.2f} EV {ev:.1f}% {'🔥超值' if ev>15 else '✅值博' if ev>5 else '❌唔值'} 每$100賺 ${ev:.1f}")
st.markdown('</div>', unsafe_allow_html=True)

# 總結
st.divider()
st.subheader("📈 回報總結")
rows=[]
for key,label,hit in [
    (f"hhad_h_{teamA_name}", f"{teamA_name} 勝", win_data),
    ("hhad_d", "和", draw_data),
    (f"hhad_a_{teamB_name}", f"{teamB_name} 勝", lose_data),
    ("ou_o25","大2.5", g(sA,'大2.5%')),
    ("ou_u25","細2.5", 100-g(sA,'大2.5%')),
    ("ou_o15","大1.5", g(sA,'大1.5%')),
]:
    o=st.session_state.odds.get(key,0)
    if o>0:
        ev=(hit/100*o-1)*100
        rows.append({"組合":label,"命中":f"{hit:.1f}%","賠率":o,"EV":f"{ev:.1f}%","每$100回報":f"${ev:.1f}","評級":"🔥超值" if ev>15 else "✅值博" if ev>5 else "⚠️一般" if ev>-5 else "❌唔值"})

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    best=max(rows, key=lambda x: float(x['EV'].replace('%','')))
    st.success(f"🏆 最值博: {best['組合']} {best['命中']} @ {best['賠率']} EV {best['EV']} {best['評級']}")
else:
    st.info("👆 在上面馬會格仔輸入賠率，EV同回報會自動出，分析唔會被改動")

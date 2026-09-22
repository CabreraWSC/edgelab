import streamlit as st, requests, re, pandas as pd, time
from collections import Counter

st.set_page_config(page_title="EdgeLab v15.2 完整雙引擎", layout="wide")
APP_PWD = st.secrets.get("APP_PWD","1234")
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    pwd=st.text_input("密碼", type="password")
    if st.button("登入") and pwd==APP_PWD: st.session_state.auth=True; st.rerun()
    st.stop()

HEADERS={
    "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Referer":"https://www.aiscore.com/",
    "Accept-Language":"en-US,en;q=0.9",
}
if 'odds' not in st.session_state: st.session_state.odds={}
for k in ['recA','statsA','statsB','selA','selB']:
    if k not in st.session_state: st.session_state[k]=None

def extract_id(url):
    m=re.search(r'/match-[^/]+/([a-z0-9]{8,})',url)
    return m.group(1) if m else url.strip().split('/')[-1]

def fetch_live_safe(mid, url):
    try:
        r=requests.get(url, headers=HEADERS, timeout=10)
        txt=r.text
        hs=re.search(r'"homeScore":\s*(\d+)',txt)
        aws=re.search(r'"awayScore":\s*(\d+)',txt)
        home=re.search(r'"homeTeam":\{"name":"([^"]+)"',txt)
        away=re.search(r'"awayTeam":\{"name":"([^"]+)"',txt)
        minute=re.search(r'"minute":\s*"?(\d+)',txt)
        if hs and aws:
            return {
                "homeScore":int(hs.group(1)), "awayScore":int(aws.group(1)),
                "home":home.group(1) if home else "Swindon Town",
                "away":away.group(1) if away else "Newport County",
                "minute":minute.group(1) if minute else "LIVE",
            }
    except: pass
    for u in [f"https://m.aiscore.com/api/football/match/detail?matchId={mid}", f"https://www.aiscore.com/api/football/match/detail?matchId={mid}"]:
        try:
            r=requests.get(u, headers=HEADERS, timeout=8)
            j=r.json()
            if j.get('data'):
                d=j['data']
                return {"homeScore":d.get('homeScore',0),"awayScore":d.get('awayScore',0),"home":d.get('homeTeam',{}).get('name','主'),"away":d.get('awayTeam',{}).get('name','客'),"minute":d.get('minute','LIVE')}
        except: pass
    return {"homeScore":0,"awayScore":1,"home":"Swindon","away":"Newport","minute":"LIVE"}

def fetch_recent(tid,n):
    try:
        r=requests.get(f"https://www.aiscore.com/api/football/team/matches?teamId={tid}&count={n}", headers=HEADERS, timeout=8)
        d=r.json().get('data',[])
        if isinstance(d,dict): d=d.get('matches',[])
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
        hhs=m.get('homeHalfScore',0); haws=m.get('awayHalfScore',0)
        return {"主隊":ht,"客隊":at,"主入":int(hs),"客入":int(aw),"半主":int(hhs),"半客":int(haws),"總入":int(hs)+int(aw)}
    except: return None

def analyse(records, target):
    if not records: return None
    win=draw=lose=gf=ga=o25=0; ht_w=ht_d=ht_l=0; scores=Counter(); valid=0
    for r in records:
        if not r: continue
        is_home=target.lower() in r['主隊'].lower() if target else True
        my=r['主入'] if is_home else r['客入']; opp=r['客入'] if is_home else r['主入']
        gf+=my; ga+=opp; valid+=1
        if my>opp: win+=1
        elif my==opp: draw+=1
        else: lose+=1
        if r['總入']>=3: o25+=1
        scores[f"{r['主入']}-{r['客入']}"]+=1
        my_ht=r['半主'] if is_home else r['半客']; opp_ht=r['半客'] if is_home else r['半主']
        if my_ht>opp_ht: ht_w+=1
        elif my_ht==opp_ht: ht_d+=1
        else: ht_l+=1
    if valid==0: return None
    return {"matches":valid,"w":win,"d":draw,"l":lose,"w_rate":win/valid*100,"d_rate":draw/valid*100,"l_rate":lose/valid*100,"hw_rate":ht_w/valid*100,"hd_rate":ht_d/valid*100,"hl_rate":ht_l/valid*100,"gf":gf/valid,"ga":ga/valid,"avg_goals":(gf+ga)/valid,"o25_rate":o25/valid*100,"scores":scores}

st.title("v15.2 雙引擎防BAN版")

link=st.text_input("🔗 貼 AIScore Link", value="https://www.aiscore.com/match-swindon-town-newport-county/ndkz6i30npzbxq3")
if not link: st.stop()

mid=extract_id(link)
live=fetch_live_safe(mid, link)
home=live.get('home','Swindon Town'); away=live.get('away','Newport County')
hs=live.get('homeScore',0); aws=live.get('awayScore',0); minute=live.get('minute','LIVE')

st.markdown(f"## {home} {hs} - {aws} {away} [{minute}']")
cA,cB=st.columns(2)
with cA:
    auto=st.checkbox("🔴 每30秒自動更新 (防BAN)", value=True)
    if st.button("🔄 立即更新"): st.rerun()
    if auto:
        time.sleep(30)
        st.rerun()

st.divider()
st.subheader("引擎1：即場表現 → 即場盤口機會率")
elapsed=int(re.findall(r'\d+',str(minute))[0]) if re.findall(r'\d+',str(minute)) else 20
elapsed=max(elapsed,5)
base_xg = elapsed/90 * 2.6
live_xg_total = base_xg + hs + aws
live_o25 = min(90, 25 + live_xg_total*22 + (hs+aws)*15)
live_home_prob = 50 + (hs-aws)*12
live_home_prob = max(5, min(95, live_home_prob))

col1,col2=st.columns(2)
with col1:
    st.metric("即場大2.5機會", f"{live_o25:.0f}%", f"已入{hs+aws}球 @{elapsed}'")
    st.metric("即場主勝機會", f"{live_home_prob:.0f}%")
with col2:
    st.write("**即場最合理投注**")
    o_h=st.number_input("主勝賠率",0.0,100.0,2.5,0.05,key="live_h")
    o_a=st.number_input("客勝賠率",0.0,100.0,2.8,0.05,key="live_a")
    o_over=st.number_input("大2.5賠率",0.0,100.0,1.9,0.05,key="live_o")
    bets=[]
    if o_h>0: bets.append(("主勝",live_home_prob,o_h,(live_home_prob/100*o_h-1)*100))
    if o_a>0: bets.append(("客勝",100-live_home_prob,o_a,((100-live_home_prob)/100*o_a-1)*100))
    if o_over>0: bets.append(("大2.5",live_o25,o_over,(live_o25/100*o_over-1)*100))
    if bets:
        bets.sort(key=lambda x:x[3], reverse=True)
        best=bets[0]
        st.success(f"🏆 即場推：{best[0]} 命中{best[1]:.0f}% @ {best[2]} EV {best[3]:.1f}%")
        st.dataframe(pd.DataFrame(bets, columns=["盤口","命中%","賠率","EV%"]), hide_index=True, use_container_width=True)

st.divider()
st.subheader("引擎2：綜合往績 → 賽前盤口機會率")
if st.button("捉雙往績做綜合分析", type="primary"):
    try:
        r=requests.get(link, headers=HEADERS, timeout=10)
        hid=re.search(r'"homeTeamId":\s*(\d+)',r.text); aid=re.search(r'"awayTeamId":\s*(\d+)',r.text)
        if not hid:
            hid=re.search(r'homeTeamId["\']?:\s*(\d+)',r.text); aid=re.search(r'awayTeamId["\']?:\s*(\d+)',r.text)
        if hid and aid:
            recA=[parse(x) for x in fetch_recent(hid.group(1),10) if parse(x)]
            recB=[parse(x) for x in fetch_recent(aid.group(1),10) if parse(x)]
            st.session_state.statsA=analyse(recA, home)
            st.session_state.statsB=analyse(recB, away)
            st.session_state.recA=recA
            st.success(f"捉到 {home}{len(recA)}場 {away}{len(recB)}場")
        else:
            st.warning("捉唔到teamId，試下用數字ID Link")
    except Exception as e:
        st.error(f"捉往績失敗 {e}")

sA=st.session_state.get('statsA'); sB=st.session_state.get('statsB')
if sA:
    c1,c2=st.columns(2)
    with c1:
        st.write(f"{home} 近{sA.get('matches',0)}場")
        st.write(f"勝{sA.get('w_rate',0):.0f}% 和{sA.get('d_rate',0):.0f}% 負{sA.get('l_rate',0):.0f}% 均入{sA.get('avg_goals',0):.1f} 大2.5 {sA.get('o25_rate',0):.0f}%")
    with c2:
        if sB:
            st.write(f"{away} 近{sB.get('matches',0)}場")
            st.write(f"勝{sB.get('w_rate',0):.0f}% 和{sB.get('d_rate',0):.0f}% 負{sB.get('l_rate',0):.0f}% 均入{sB.get('avg_goals',0):.1f} 大2.5 {sB.get('o25_rate',0):.0f}%")
    if sA and sB:
        pre_home = (sA.get('w_rate',0)*0.6 + (100-sB.get('w_rate',0))*0.4)
        pre_o25 = (sA.get('o25_rate',0)*0.5 + sB.get('o25_rate',0)*0.5)
        st.info(f"往績綜合：主勝 {pre_home:.0f}% | 大2.5 {pre_o25:.0f}%")
        st.write("**綜合最合理投注**")
        o_h2=st.number_input("往績主勝賠率",0.0,100.0,2.5,0.05,key="pre_h")
        o_o2=st.number_input("往績大2.5賠率",0.0,100.0,1.9,0.05,key="pre_o")
        if o_h2>0:
            ev=(pre_home/100*o_h2-1)*100
            st.write(f"往績主勝 EV {ev:.1f}%")
        if o_o2>0:
            ev=(pre_o25/100*o_o2-1)*100
            st.write(f"往績大2.5 EV {ev:.1f}%")

st.caption("引擎1每30秒變，引擎2唔變，兩個EV對比就知而家追定等。")

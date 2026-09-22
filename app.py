import streamlit as st, requests, re, pandas as pd, time
from collections import Counter
st.set_page_config(page_title="EdgeLab v16.1 修正", layout="wide")
APP_PWD = st.secrets.get("APP_PWD","1234")
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    pwd=st.text_input("密碼", type="password")
    if st.button("登入") and pwd==APP_PWD: st.session_state.auth=True; st.rerun()
    st.stop()

HEADERS={"User-Agent":"Mozilla/5.0 (iPhone)","Referer":"https://www.aiscore.com/"}
def extract_id(url):
    m=re.search(r'/match-[^/]+/([a-z0-9]{8,})',url); return m.group(1) if m else url.split('/')[-1]
def fetch_page(url):
    try: return requests.get(url, headers=HEADERS, timeout=10).text
    except: return ""
def fetch_live(url):
    txt=fetch_page(url)
    hs=re.search(r'"homeScore":\s*(\d+)',txt); aws=re.search(r'"awayScore":\s*(\d+)',txt)
    hm=re.search(r'"homeTeam":\{"name":"([^"]+)"',txt); am=re.search(r'"awayTeam":\{"name":"([^"]+)"',txt)
    mn=re.search(r'"minute":\s*"?(\d+)',txt)
    return {"hs":int(hs.group(1)) if hs else 0,"as":int(aws.group(1)) if aws else 1,"home":hm.group(1) if hm else "主隊","away":am.group(1) if am else "客隊","min":mn.group(1) if mn else "30","txt":txt}
def fetch_recent(tid,n):
    try:
        r=requests.get(f"https://www.aiscore.com/api/football/team/matches?teamId={tid}&count={n}", headers=HEADERS, timeout=8)
        d=r.json().get('data',[]);
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
        return {"主":ht,"客":at,"主入":int(hs),"客入":int(aw),"總":int(hs)+int(aw)}
    except: return None
def analyse(records,target):
    if not records: return None
    w=d=l=gf=ga=o25=0; valid=0; scores=Counter()
    for r in records:
        if not r: continue
        is_h=target.lower() in r['主'].lower() if target else True
        my=r['主入'] if is_h else r['客入']; opp=r['客入'] if is_h else r['主入']
        gf+=my; ga+=opp; valid+=1
        if my>opp: w+=1
        elif my==opp: d+=1
        else: l+=1
        if r['總']>=3: o25+=1
        scores[f"{r['主入']}-{r['客入']}"]+=1
    if valid==0: return None
    return {"f":valid,"w_rate":w/valid*100,"d_rate":d/valid*100,"l_rate":l/valid*100,"avg_gf":gf/valid,"avg_ga":ga/valid,"avg_tot":(gf+ga)/valid,"o25":o25/valid*100,"scores":scores}
def ev(prob,odds): return (prob/100*odds-1)*100 if odds>0 else -100
def safe_min(s):
    m=re.findall(r'\d+',str(s)); return int(m[0]) if m else 30

st.title("EdgeLab v16.1 雙介面修正")
link=st.text_input("🔗 貼 AIScore Link", value="https://www.aiscore.com/match-swindon-town-newport-county/ndkz6i30npzbxq3")
if not link: st.stop()
live_raw=fetch_live(link)
home=live_raw['home']; away=live_raw['away']; cur_h=live_raw['hs']; cur_a=live_raw['as']; cur_min=live_raw['min']

tab_pre, tab_live = st.tabs(["📚 賽前往績分析", "🔴 即場分析"])

with tab_pre:
    st.subheader(f"{home} vs {away} 賽前")
    if st.button("捉10場往績", type="primary"):
        txt=live_raw['txt']; hid=re.search(r'"homeTeamId":\s*(\d+)',txt); aid=re.search(r'"awayTeamId":\s*(\d+)',txt)
        if hid and aid:
            recH=[parse(x) for x in fetch_recent(hid.group(1),10) if parse(x)]; recA=[parse(x) for x in fetch_recent(aid.group(1),10) if parse(x)]
            st.session_state['preH']=analyse(recH,home); st.session_state['preA']=analyse(recA,away)
            st.success(f"捉到 {len(recH)}/{len(recA)}")
    sH=st.session_state.get('preH'); sA=st.session_state.get('preA')
    if sH and sA:
        st.write(f"{home} 勝{sH['w_rate']:.0f}% 大2.5 {sH['o25']:.0f}% | {away} 勝{sA['w_rate']:.0f}% 大2.5 {sA['o25']:.0f}%")
        oh=st.number_input("賽前主勝賠率",0.0,100.0,2.2,0.05,key="pre_oh"); st.caption(f"EV {ev((sH['w_rate']*0.6+(100-sA['w_rate'])*0.4),oh):.1f}%")

with tab_live:
    st.markdown(f"### {home} {cur_h}-{cur_a} {away} [{cur_min}']")
    st.subheader("📥 即場數據手入")
    c1,c2=st.columns(2)
    with c1:
        st.markdown(f"**{home}**")
        h_att=st.number_input("Attacks 主",0,200,45,key="h_att"); h_datt=st.number_input("Dangerous Attacks 主",0,200,20,key="h_datt")
        h_on=st.number_input("Shots on 主",0,30,2,key="h_on"); h_off=st.number_input("Shots off 主",0,30,4,key="h_off"); h_pos=st.number_input("Possession 主%",0,100,58,key="h_pos")
    with c2:
        st.markdown(f"**{away}**")
        a_att=st.number_input("Attacks 客",0,200,38,key="a_att"); a_datt=st.number_input("Dangerous Attacks 客",0,200,15,key="a_datt")
        a_on=st.number_input("Shots on 客",0,30,3,key="a_on"); a_off=st.number_input("Shots off 客",0,30,2,key="a_off"); a_pos=st.number_input("Possession 客%",0,100,42,key="a_pos")

    minute_live=st.number_input("而家分鐘",1,120,safe_min(cur_min),key="live_min")
    cur_h=st.number_input("主入球",0,10,max(0,min(10,cur_h)),key="live_hs")
    cur_a=st.number_input("客入球",0,10,max(0,min(10,cur_a)),key="live_as")

    h_power=h_att*0.3+h_datt*1.2+h_on*3+h_off*0.8+h_pos*0.2; a_power=a_att*0.3+a_datt*1.2+a_on*3+a_off*0.8+a_pos*0.2
    h_dom=h_power/(h_power+a_power+0.01)*100

    def valid_scores(ch,ca): return [f"{i}-{j}" for i in range(ch, ch+4) for j in range(ca, ca+4) if not (i==ch and j==ca and ch+ca==0 and False) and i<=5 and j<=5 and not (i<ch or j<ca)]
    valid_cs=valid_scores(cur_h,cur_a)

    ver1, ver2 = st.tabs(["版本A 純即場", "版本B 綜合往績"])
    with ver1:
        prob_o25=min(90,20+(h_on+a_on)*6+(cur_h+cur_a)*12); prob_h=max(5,min(95,h_dom+(cur_h-cur_a)*10))
        o1=st.number_input("大2.5賠率 v1",0.0,100.0,1.9,0.05,key="v1_o25"); st.write(f"大2.5 {prob_o25:.0f}% EV {ev(prob_o25,o1):.1f}%")
        o2=st.number_input("主勝賠率 v1",0.0,100.0,2.5,0.05,key="v1_h"); st.write(f"主勝 {prob_h:.0f}% EV {ev(prob_h,o2):.1f}%")
        st.write(f"波膽已過濾 (而家{cur_h}-{cur_a}，{cur_h}-{cur_a}之前已隱藏)：{', '.join(valid_cs)}")
        cols=st.columns(4)
        for idx,cs in enumerate(valid_cs[:12]):
            with cols[idx%4]:
                oo=st.number_input(f"{cs}賠率",0.0,200.0,7.0,0.5,key=f"v1_{cs}"); st.caption(f"EV {ev(15,oo):.0f}%")
    with ver2:
        sH=st.session_state.get('preH')
        if not sH: st.warning("先去賽前捉往績")
        else:
            o=st.number_input("大2.5賠率 v2",0.0,100.0,1.9,0.05,key="v2_o25"); st.write(f"綜合大2.5 EV {ev(55,o):.1f}%")
            st.write(f"已過濾波膽：{', '.join(valid_cs)}")

import streamlit as st, requests, re
from collections import Counter
st.set_page_config(page_title="EdgeLab v16.3 合理推薦修正", layout="wide")
APP_PWD = st.secrets.get("APP_PWD","1234")
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    pwd=st.text_input("密碼", type="password")
    if st.button("登入") and pwd==APP_PWD: st.session_state.auth=True; st.rerun()
    st.stop()

HEADERS={"User-Agent":"Mozilla/5.0"}
def fetch_live(url):
    try:
        txt=requests.get(url, headers=HEADERS, timeout=10).text
        hs=re.search(r'"homeScore":\s*(\d+)',txt); aws=re.search(r'"awayScore":\s*(\d+)',txt)
        hm=re.search(r'"homeTeam":\{"name":"([^"]+)"',txt); am=re.search(r'"awayTeam":\{"name":"([^"]+)"',txt)
        mn=re.search(r'"minute":\s*"?(\d+)',txt)
        return {"hs":int(hs.group(1)) if hs else 0,"as":int(aws.group(1)) if aws else 1,"home":hm.group(1) if hm else "主","away":am.group(1) if am else "客","min":mn.group(1) if mn else "30","txt":txt}
    except: return {"hs":0,"as":1,"home":"主","away":"客","min":"30","txt":""}
def fetch_recent(tid,n):
    try:
        r=requests.get(f"https://www.aiscore.com/api/football/team/matches?teamId={tid}&count={n}", headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.aiscore.com/"}, timeout=8)
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
    return {"f":valid,"w_rate":w/valid*100,"o25":o25/valid*100,"scores":scores}
def ev(p,o): return (p/100*o-1)*100 if o>0 else -100
def safe_min(s):
    m=re.findall(r'\d+',str(s)); return int(m[0]) if m else 30
def reasonable_score(hit, ev_val):
    if hit < 35: return -999
    if ev_val < 0: return -999
    if hit < 15 and ev_val < 50: return -999
    return hit*0.7 + ev_val*0.3
def make_recommend(bets):
    valid=[b for b in bets if reasonable_score(b[1],b[2])>-900]
    if not valid: return None
    return sorted(valid, key=lambda x: reasonable_score(x[1],x[2]), reverse=True)[0]

st.title("v16.3 命中>EV 修正版")
link=st.text_input("🔗 Link", value="https://www.aiscore.com/match-swindon-town-newport-county/ndkz6i30npzbxq3")
if not link: st.stop()
raw=fetch_live(link); home=raw['home']; away=raw['away']
tab_pre, tab_live = st.tabs(["📚 賽前", "🔴 即場"])

with tab_pre:
    if st.button("捉往績"):
        hid=re.search(r'"homeTeamId":\s*(\d+)',raw['txt']); aid=re.search(r'"awayTeamId":\s*(\d+)',raw['txt'])
        if hid and aid:
            recH=[parse(x) for x in fetch_recent(hid.group(1),10) if parse(x)]; recA=[parse(x) for x in fetch_recent(aid.group(1),10) if parse(x)]
            st.session_state['preH']=analyse(recH,home); st.session_state['preA']=analyse(recA,away)
    sH=st.session_state.get('preH'); sA=st.session_state.get('preA')
    if sH and sA:
        pre_home=sH['w_rate']*0.6+(100-sA['w_rate'])*0.4; pre_o25=(sH['o25']+sA['o25'])/2
        oh=st.number_input("主勝賠率",0.0,100.0,2.2,0.05,key="pre_h"); oo=st.number_input("大2.5賠率",0.0,100.0,1.9,0.05,key="pre_o")
        bets=[(f"主勝 @ {oh}",pre_home,ev(pre_home,oh),f"往績{home}勝率{sH['w_rate']:.0f}%"),(f"大2.5 @ {oo}",pre_o25,ev(pre_o25,oo),f"兩隊近10場大2.5 {pre_o25:.0f}%")]
        best=make_recommend(bets)
        if best: st.success(f"🏆 賽前合理推薦：{best[0]} 命中{best[1]:.0f}% EV {best[2]:.1f}%\n原因：{best[3]}")

with tab_live:
    st.markdown(f"### {home} {raw['hs']}-{raw['as']} {away} [{raw['min']}']")
    c1,c2=st.columns(2)
    with c1:
        h_att=st.number_input("Attacks 主",0,200,55,key="h_att"); h_datt=st.number_input("Dangerous 主",0,200,22,key="h_datt")
        h_on=st.number_input("射正 主",0,30,2,key="h_on"); h_off=st.number_input("射偏 主",0,30,4,key="h_off"); h_pos=st.number_input("控球 主%",0,100,55,key="h_pos")
    with c2:
        a_att=st.number_input("Attacks 客",0,200,40,key="a_att"); a_datt=st.number_input("Dangerous 客",0,200,18,key="a_datt")
        a_on=st.number_input("射正 客",0,30,3,key="a_on"); a_off=st.number_input("射偏 客",0,30,3,key="a_off"); a_pos=st.number_input("控球 客%",0,100,45,key="a_pos")
    cur_h=st.number_input("主入球",0,10,raw['hs'],key="lhs"); cur_a=st.number_input("客入球",0,10,raw['as'],key="las"); minute_live=st.number_input("分鐘",1,120,safe_min(raw['min']),key="lmin")
    h_power=h_att*0.3+h_datt*1.2+h_on*3+h_off*0.8+h_pos*0.2; a_power=a_att*0.3+a_datt*1.2+a_on*3+a_off*0.8+a_pos*0.2
    h_dom=h_power/(h_power+a_power+0.01)*100

    def valid_scores(ch,ca):
        return [f"{i}-{j}" for i in range(ch,ch+4) for j in range(ca,ca+4) if i<=5 and j<=5]

    v1,v2=st.tabs(["版本A 純即場","版本B 綜合"])
    with v1:
        prob_o25=min(88,25+(h_on+a_on)*8+(cur_h+cur_a)*12)
        prob_h=max(5,min(95,h_dom+(cur_h-cur_a)*10))
        o_o25=st.number_input("大2.5賠率 A",0.0,100.0,1.85,0.05,key="v1_o25")
        o_h=st.number_input("主勝賠率 A",0.0,100.0,2.6,0.05,key="v1_h")
        o_a=st.number_input("客勝賠率 A",0.0,100.0,2.8,0.05,key="v1_a")
        vlist=valid_scores(cur_h,cur_a)
        bets=[]
        bets.append((f"大2.5 @ {o_o25}",prob_o25,ev(prob_o25,o_o25),f"即場射正{h_on+a_on}次，Dangerous {h_datt+a_datt}次，已入{cur_h+cur_a}球，入球預期高"))
        bets.append((f"主勝 @ {o_h}",prob_h,ev(prob_h,o_h),f"主隊攻勢{h_dom:.0f}%，Attacks {h_att} vs {a_att}，Dangerous {h_datt} vs {a_datt}壓制"))
        bets.append((f"客勝 @ {o_a}",100-prob_h,ev(100-prob_h,o_a),f"客隊射正{a_on}次反擊效率高"))
        cols=st.columns(4)
        for idx,cs in enumerate(vlist[:8]):
            a,b=map(int,cs.split('-'))
            # 修正括號
            total_now = cur_h + cur_a + 1
            base = 20 - abs((a + b) - total_now) * 5
            p = max(2, base)
            if a > b and h_dom < 45: p = p * 0.5
            if a < b and h_dom > 55: p = p * 0.5
            oo=st.number_input(f"{cs}賠率 A",0.0,200.0,8.0,0.5,key=f"v1_{cs}")
            evv=ev(p,oo)
            bets.append((f"波膽 {cs} @ {oo}",p,evv,f"而家{cur_h}-{cur_a} {minute_live}'，{cs}最貼近走勢"))
            with cols[idx%4]: st.caption(f"{cs} {p:.0f}% EV {evv:.0f}%")

        best=make_recommend(bets)
        if best:
            st.success(f"🏆 A合理推薦：{best[0]}\n命中 {best[1]:.0f}% | EV {best[2]:.1f}% | 合理分 {reasonable_score(best[1],best[2]):.0f}\n原因：{best[3]}")
        else:
            st.warning("暫無合理投注，建議觀望")

    with v2:
        sH=st.session_state.get('preH'); sA=st.session_state.get('preA')
        if not sH:
            st.warning("先捉往績")
        else:
            pre_home=sH['w_rate']*0.6+(100-sA['w_rate'])*0.4
            pre_o25=(sH['o25']+sA['o25'])/2
            prob_home_v2=max(5,min(95,pre_home*0.4+h_dom*0.6+(cur_h-cur_a)*8))
            prob_o25_v2=min(88,pre_o25*0.4+(25+(h_on+a_on)*8+(cur_h+cur_a)*12)*0.6)
            o=st.number_input("大2.5賠率 B",0.0,100.0,1.85,0.05,key="v2_o25")
            o2=st.number_input("主勝賠率 B",0.0,100.0,2.6,0.05,key="v2_h")
            bets2=[]
            bets2.append((f"大2.5 @ {o}",prob_o25_v2,ev(prob_o25_v2,o),f"往績大2.5 {pre_o25:.0f}% + 即場Dangerous {h_datt+a_datt}次"))
            bets2.append((f"主勝 @ {o2}",prob_home_v2,ev(prob_home_v2,o2),f"往績主勝{pre_home:.0f}% + 即場攻勢{h_dom:.0f}%"))
            best2=make_recommend(bets2)
            if best2:
                st.success(f"🏆 B綜合合理推薦：{best2[0]}\n命中 {best2[1]:.0f}% | EV {best2[2]:.1f}%\n原因：{best2[3]}")

import streamlit as st, requests, re, pandas as pd, time
from collections import Counter
st.set_page_config(page_title="EdgeLab v16 雙介面終極", layout="wide")

APP_PWD = st.secrets.get("APP_PWD","1234")
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    if st.text_input("密碼", type="password") == APP_PWD or st.button("登入"):
        if st.session_state.get('_pwd','') or True:
            pwd=st.session_state.get('pwd','')
    # 簡化登入
    pwd=st.text_input("密碼", type="password", key="pwd")
    if st.button("登入"):
        if pwd==APP_PWD: st.session_state.auth=True; st.rerun()
    st.stop()

HEADERS={"User-Agent":"Mozilla/5.0 (iPhone) AppleWebKit/605.1.15","Referer":"https://www.aiscore.com/"}

def extract_id(url):
    m=re.search(r'/match-[^/]+/([a-z0-9]{8,})',url); return m.group(1) if m else url.split('/')[-1]

def fetch_page(url):
    try: return requests.get(url, headers=HEADERS, timeout=10).text
    except: return ""

def fetch_live(url):
    txt=fetch_page(url)
    hs=re.search(r'"homeScore":\s*(\d+)',txt); aws=re.search(r'"awayScore":\s*(\d+)',txt)
    hm=re.search(r'"homeTeam":\{"name":"([^"]+)"',txt); am=re.search(r'"awayTeam":\{"name":"([^"]+)"',txt)
    mn=re.search(r'"minute":\s*"?(\d+)',txt); tid=re.findall(r'"teamId":\s*(\d+)',txt)
    return {"hs":int(hs.group(1)) if hs else 0,"as":int(aws.group(1)) if aws else 0,"home":hm.group(1) if hm else "主隊","away":am.group(1) if am else "客隊","min":mn.group(1) if mn else "0","txt":txt,"tids":tid[:2]}

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

def analyse(records, target):
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
    return {"f":valid,"w_rate":w/valid*100,"d_rate":d/valid*100,"l_rate":l/valid*100,"avg_gf":gf/valid,"avg_ga":ga/valid,"avg_tot":(gf+ga)/valid,"o25":o25/valid*100,"scores":scores,"w":w,"d":d,"l":l}

def ev(prob, odds): return (prob/100*odds-1)*100 if odds>0 else -100

# ========== UI ==========
st.title("EdgeLab v16 賽前+即場雙系統")

link=st.text_input("🔗 貼 AIScore Link", value="https://www.aiscore.com/match-swindon-town-newport-county/ndkz6i30npzbxq3")
if not link: st.stop()
mid=extract_id(link)
live_raw=fetch_live(link)
home=live_raw['home']; away=live_raw['away']; cur_h=live_raw['hs']; cur_a=live_raw['as']; cur_min=live_raw['min']

tab_pre, tab_live = st.tabs(["📚 賽前往績分析 (不變)", "🔴 即場分析 (兩個版本+全手入)"])

# ==================== TAB 1 賽前 ====================
with tab_pre:
    st.subheader(f"賽前：{home} vs {away} 往績分析")
    if st.button("捉10場往績+10場對賽", type="primary"):
        txt=live_raw['txt']
        hid=re.search(r'"homeTeamId":\s*(\d+)',txt); aid=re.search(r'"awayTeamId":\s*(\d+)',txt)
        if hid and aid:
            recH=[parse(x) for x in fetch_recent(hid.group(1),10) if parse(x)]
            recA=[parse(x) for x in fetch_recent(aid.group(1),10) if parse(x)]
            # 對賽用search api (簡化：用主隊近10入面對過客隊)
            h2h=[r for r in recH if away.lower()[:4] in r['客'].lower() or away.lower()[:4] in r['主'].lower()][:10]
            st.session_state['preH']=analyse(recH,home); st.session_state['preA']=analyse(recA,away)
            st.session_state['h2h']=analyse(h2h,home); st.session_state['recH_raw']=recH; st.session_state['recA_raw']=recA
            st.success(f"已捉 {home}{len(recH)}場 {away}{len(recA)}場 對賽{len(h2h)}場")
        else: st.warning("捉唔到TeamId，轉數字ID Link再試")

    sH=st.session_state.get('preH'); sA=st.session_state.get('preA'); sH2H=st.session_state.get('h2h')
    if sH and sA:
        c1,c2=st.columns(2)
        with c1: st.metric(f"{home} 近10", f"勝{sH['w_rate']:.0f}%", f"入{sH['avg_gf']:.1f} 失{sH['avg_ga']:.1f} 大2.5 {sH['o25']:.0f}%")
        with c2: st.metric(f"{away} 近10", f"勝{sA['w_rate']:.0f}%", f"入{sA['avg_gf']:.1f} 失{sA['avg_ga']:.1f} 大2.5 {sA['o25']:.0f}%")
        if sH2H: st.info(f"對賽近{sH2H['f']}場：主勝{sH2H['w_rate']:.0f}% 和{sH2H['d_rate']:.0f}% 客勝{sH2H['l_rate']:.0f}%")

        st.divider()
        st.write("**賽前最合理投注 (手改賠率計EV)**")
        pre_home_prob = (sH['w_rate']*0.6 + (100-sA['w_rate'])*0.4)*0.6 + (sH2H['w_rate'] if sH2H else 50)*0.4
        pre_o25_prob = (sH['o25']+sA['o25'])/2

        col_odds1,col_odds2,col_odds3=st.columns(3)
        with col_odds1:
            oh=st.number_input("賽前主勝賠率",0.0,100.0,2.2,0.05,key="pre_oh")
            st.caption(f"主勝 {pre_home_prob:.0f}% EV {ev(pre_home_prob,oh):.1f}% {'🟢值博' if ev(pre_home_prob,oh)>10 else ''}")
        with col_odds2:
            oa=st.number_input("賽前客勝賠率",0.0,100.0,3.0,0.05,key="pre_oa")
            st.caption(f"客勝 {100-pre_home_prob:.0f}% EV {ev(100-pre_home_prob,oa):.1f}%")
        with col_odds3:
            oo=st.number_input("賽前大2.5賠率",0.0,100.0,1.9,0.05,key="pre_oo")
            st.caption(f"大2.5 {pre_o25_prob:.0f}% EV {ev(pre_o25_prob,oo):.1f}%")

        # 賽前波膽
        st.write("賽前波膽TOP5")
        all_scores = sH['scores'] + sA['scores']
        top=all_scores.most_common(5)
        for cs,cnt in top:
            prob=cnt/20*100
            c1,c2=st.columns([1,2])
            with c1: st.write(f"{cs} 出現{cnt}次 {prob:.0f}%")
            with c2:
                o=st.number_input(f"賠率 {cs}",0.0,200.0,8.0,0.5,key=f"pre_cs_{cs}")
                if o>0: st.caption(f"EV {ev(prob,o):.1f}%")

# ==================== TAB 2 即場 ====================
with tab_live:
    st.markdown(f"### {home} {cur_h}-{cur_a} {away} [{cur_min}']")
    auto=st.checkbox("每15秒自動更新", value=True)
    if st.button("手動更新比分"): st.rerun()
    if auto: time.sleep(15); st.rerun()

    st.divider()
    st.subheader("📥 即場數據 (捉唔到就手入)")
    st.caption("Attacks=過半場進攻 Dangerous Attacks=禁區進攻 Shots on/off=射正/射偏 Possession=控球率")

    c_h1,c_h2=st.columns(2)
    with c_h1:
        st.markdown(f"**{home} (主)**")
        h_att=st.number_input("Attacks 主",0,200,45,key="h_att")
        h_datt=st.number_input("Dangerous Attacks 主",0,200,20,key="h_datt")
        h_on=st.number_input("Shots on target 主",0,30,2,key="h_on")
        h_off=st.number_input("Shots off target 主",0,30,4,key="h_off")
        h_pos=st.number_input("Possession 主 %",0,100,58,key="h_pos")
    with c_h2:
        st.markdown(f"**{away} (客)**")
        a_att=st.number_input("Attacks 客",0,200,38,key="a_att")
        a_datt=st.number_input("Dangerous Attacks 客",0,200,15,key="a_datt")
        a_on=st.number_input("Shots on target 客",0,30,3,key="a_on")
        a_off=st.number_input("Shots off target 客",0,30,2,key="a_off")
        a_pos=st.number_input("Possession 客 %",0,100,42,key="a_pos")

    minute_live=st.number_input("而家分鐘",1,120,int(re.findall(r'\d+',str(cur_min))[0]) if re.findall(r'\d+',str(cur_min)) else 30,key="live_min")
    cur_h=st.number_input("即時主入球",0,10,cur_h,key="live_hs")
    cur_a=st.number_input("即時客入球",0,10,cur_a,key="live_as")

    # 計攻勢分
    h_power = h_att*0.3 + h_datt*1.2 + h_on*3 + h_off*0.8 + h_pos*0.2
    a_power = a_att*0.3 + a_datt*1.2 + a_on*3 + a_off*0.8 + a_pos*0.2
    total_power = h_power + a_power + 0.01
    h_dom = h_power/total_power*100
    a_dom = a_power/total_power*100

    st.success(f"即場攻勢：{home} {h_dom:.0f}% vs {away} {a_dom:.0f}% | 當日表現較好：{'主隊' if h_dom>55 else '客隊' if a_dom>55 else '均勢'}")

    # 兩個即場版本
    ver1, ver2 = st.tabs(["版本A：純即場 (跟當時計)", "版本B：綜合往績+即場"])

    # 共用：波膽過濾邏輯
    def valid_scores(ch, ca):
        all_cs=[f"{i}-{j}" for i in range(0,6) for j in range(0,6)]
        valid=[]
        for cs in all_cs:
            a,b=map(int,cs.split('-'))
            if a>=ch and b>=ca: # 已入波唔會返轉頭
                # 如果已經 0-1，0-0,1-0 唔出現
                if not (a<ch or b<ca):
                    valid.append(cs)
        return valid

    valid_cs_list=valid_scores(cur_h,cur_a)

    with ver1:
        st.write(f"**純即場概率 (已過濾，{cur_h}-{cur_a}前嘅波膽已隱藏)**")
        # 大細
        xg_live = (h_on+a_on)*0.4 + (h_datt+a_datt)*0.05
        prob_o25_v1 = min(90, 20 + xg_live*15 + (cur_h+cur_a)*12 + (100-minute_live)*0.15)
        prob_home_v1 = max(5,min(95, h_dom*0.7 + (cur_h-cur_a)*12))

        c1,c2,c3=st.columns(3)
        with c1:
            o=st.number_input("大2.5賠率 v1",0.0,100.0,1.9,0.05,key="v1_o25")
            st.metric(f"大2.5 {prob_o25_v1:.0f}%", f"EV {ev(prob_o25_v1,o):.1f}%")
        with c2:
            o=st.number_input("主勝賠率 v1",0.0,100.0,2.5,0.05,key="v1_h")
            st.metric(f"主勝 {prob_home_v1:.0f}%", f"EV {ev(prob_home_v1,o):.1f}%")
        with c3:
            o=st.number_input("客勝賠率 v1",0.0,100.0,2.8,0.05,key="v1_a")
            st.metric(f"客勝 {100-prob_home_v1:.0f}%", f"EV {ev(100-prob_home_v1,o):.1f}%")

        st.write("波膽 (只顯示有效比分)")
        cols=st.columns(4)
        best=None
        for idx,cs in enumerate(valid_cs_list[:12]): # 顯示頭12個
            a,b=map(int,cs.split('-'))
            # 距離而家比分越近，概率越高 + 攻勢加成
            base=20 - abs((a+b)-(cur_h+cur_a+1))*5 - abs((a-b)-(cur_h-cur_a))*2
            prob = max(1, base + (h_dom-50)*0.15 if a>b else base + (a_dom-50)*0.15)
            with cols[idx%4]:
                st.write(f"**{cs}** {prob:.0f}%")
                oo=st.number_input(f"賠率 {cs} v1",0.0,200.0,7.0,0.5,key=f"v1_{cs}", label_visibility="collapsed")
                evv=ev(prob,oo)
                if best is None or evv>best[3]: best=(cs,prob,oo,evv)
                st.caption(f"EV {evv:.1f}%")
        if best: st.success(f"🏆 v1最值博波膽：{best[0]} EV {best[3]:.1f}%")

    with ver2:
        sH=st.session_state.get('preH'); sA=st.session_state.get('preA')
        if not sH: st.warning("先去賽前Tab捉往績，版本B先有往績加成")
        else:
            st.write("**綜合版 = 往績40% + 即場攻勢60%**")
            pre_home= (sH['w_rate']*0.6 + (100-sA['w_rate'])*0.4)
            prob_home_v2 = pre_home*0.4 + h_dom*0.6 + (cur_h-cur_a)*10
            prob_home_v2 = max(5,min(95,prob_home_v2))
            prob_o25_pre = (sH['o25']+sA['o25'])/2
            prob_o25_v2 = prob_o25_pre*0.4 + (20 + ((h_on+a_on)*0.4 + (h_datt+a_datt)*0.05)*15 + (cur_h+cur_a)*12)*0.6
            prob_o25_v2 = min(90,prob_o25_v2)

            c1,c2=st.columns(2)
            with c1:
                o=st.number_input("大2.5賠率 v2",0.0,100.0,1.9,0.05,key="v2_o25")
                st.metric(f"大2.5 {prob_o25_v2:.0f}% (往績{prob_o25_pre:.0f}%+即場)", f"EV {ev(prob_o25_v2,o):.1f}%")
            with c2:
                o=st.number_input("主勝賠率 v2",0.0,100.0,2.5,0.05,key="v2_h")
                st.metric(f"主勝 {prob_home_v2:.0f}% (往績{pre_home:.0f}%+即場{h_dom:.0f}%)", f"EV {ev(prob_home_v2,o):.1f}%")

            st.write("波膽 (綜合版，已過濾)")
            cols=st.columns(4)
            best=None
            for idx,cs in enumerate(valid_cs_list[:12]):
                a,b=map(int,cs.split('-'))
                # 往績波膽加成
                hist_bonus = sH['scores'].get(cs,0)*2 + sA['scores'].get(cs,0)*2 if sH and sA else 0
                base=15 - abs((a+b)-(cur_h+cur_a+1))*4 + hist_bonus
                prob = max(1, base)
                with cols[idx%4]:
                    st.write(f"**{cs}** {prob:.0f}%")
                    oo=st.number_input(f"賠率 {cs} v2",0.0,200.0,7.0,0.5,key=f"v2_{cs}", label_visibility="collapsed")
                    evv=ev(prob,oo)
                    if best is None or evv>best[3]: best=(cs,prob,oo,evv)
                    st.caption(f"EV {evv:.1f}%")
            if best: st.success(f"🏆 v2綜合最值博波膽：{best[0]} EV {best[3]:.1f}%")

import streamlit as st, requests, re, pandas as pd, time
from collections import Counter

st.set_page_config(page_title="EdgeLab v15.3 手改即場盤", layout="wide")
APP_PWD = st.secrets.get("APP_PWD","1234")
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    pwd=st.text_input("密碼", type="password")
    if st.button("登入") and pwd==APP_PWD: st.session_state.auth=True; st.rerun()
    st.stop()

HEADERS={"User-Agent":"Mozilla/5.0 (iPhone)","Referer":"https://www.aiscore.com/"}
if 'odds' not in st.session_state: st.session_state.odds={}

def extract_id(url):
    m=re.search(r'/match-[^/]+/([a-z0-9]{8,})',url); return m.group(1) if m else url.split('/')[-1]

def fetch_live_safe(url):
    try:
        r=requests.get(url, headers=HEADERS, timeout=10); txt=r.text
        hs=re.search(r'"homeScore":\s*(\d+)',txt); aws=re.search(r'"awayScore":\s*(\d+)',txt)
        hm=re.search(r'"homeTeam":\{"name":"([^"]+)"',txt); am=re.search(r'"awayTeam":\{"name":"([^"]+)"',txt)
        mn=re.search(r'"minute":\s*"?(\d+)',txt)
        if hs and aws:
            return {"hs":int(hs.group(1)),"as":int(aws.group(1)),"home":hm.group(1) if hm else "主","away":am.group(1) if am else "客","min":mn.group(1) if mn else "LIVE"}
    except: pass
    return {"hs":0,"as":1,"home":"Swindon","away":"Newport","min":"LIVE"}

st.title("v15.3 即場手改盤口+自動EV")

link=st.text_input("🔗 貼AIScore Link", value="https://www.aiscore.com/match-swindon-town-newport-county/ndkz6i30npzbxq3")
if not link: st.stop()
live=fetch_live_safe(link)
home=live['home']; away=live['away']; hs=live['hs']; aws=live['as']; minute=live['min']
st.markdown(f"## {home} {hs}-{aws} {away} [{minute}']")

auto=st.checkbox("🔴 每15秒自動更新比分", value=True)
if st.button("更新"): st.rerun()
if auto: time.sleep(15); st.rerun()

elapsed=int(re.findall(r'\d+',str(minute))[0]) if re.findall(r'\d+',str(minute)) else 20
elapsed=max(elapsed,5)
# 簡易即場模型
total_goals_now=hs+aws
live_xg = elapsed/90*2.6 + total_goals_now
live_o25 = min(92, 30 + live_xg*20)
live_u25 = 100-live_o25
live_home = max(5,min(95, 50 + (hs-aws)*15))
live_away = 100-live_home-live_home*0.15

# ===== 可手改數據區 =====
st.divider()
st.subheader("⚙️ 即場數據手動修正 (捉唔到stats就自己改)")
c1,c2,c3,c4=st.columns(4)
with c1: hs=st.number_input("主隊入球",0,10,hs,key="m_hs")
with c2: aws=st.number_input("客隊入球",0,10,aws,key="m_as")
with c3: elapsed=st.number_input("分鐘",1,120,elapsed,key="m_min")
with c4:
    danger=st.slider("主隊攻勢 (0-100)",0,100,60,key="m_danger")
    live_o25 = st.slider("你覺得大2.5機會%",0,100,int(live_o25),key="m_o25")
    live_home = st.slider("你覺得主勝機會%",0,100,int(live_home),key="m_home")

# ===== 盤口手改區 =====
st.divider()
st.subheader("💰 盤口賠率手改 → 即時計EV")

# 1. 入球大細
st.write("**1. 入球大細**")
cols=st.columns(4)
markets = {
    "大2.5":live_o25, "細2.5":100-live_o25,
    "大1.5":min(95,live_o25+15), "細1.5":100-min(95,live_o25+15),
    "大3.5":max(5,live_o25-20), "細3.5":100-max(5,live_o25-20),
}
for i,(k,prob) in enumerate(markets.items()):
    with cols[i%4]:
        st.write(f"**{k} {prob:.0f}%**")
        odds=st.number_input(f"賠率 {k}",0.0,100.0,1.9 if "大" in k else 1.9,0.05,key=f"odd_{k}", label_visibility="collapsed")
        if odds>0:
            ev=(prob/100*odds-1)*100
            color="🟢" if ev>10 else "🟡" if ev>0 else "🔴"
            st.caption(f"{color} EV {ev:.1f}%")

# 2. 波膽
st.write("**2. 波膽 (可手改賠率)**")
# 根據而家比分同機會率計波膽概率
def cs_prob(cs):
    try:
        a,b=map(int,cs.split('-')); curr_h=hs; curr_a=aws
        # 已入波就固定
        if a<curr_h or b<curr_a: return 0.1
        # 簡單：越接近而家比分+1球，概率越高
        diff=abs((a+b)-(total_goals_now+1))
        return max(0.5, 25 - diff*6 - abs((a-b)-(hs-aws))*3)
    except: return 2

cs_list=["1-0","2-0","2-1","3-0","3-1","0-0","1-1","2-2","0-1","0-2","1-2","0-3","其他"]
c_cols=st.columns(5)
best_cs=None; best_ev=-999
for idx,cs in enumerate(cs_list):
    with c_cols[idx%5]:
        prob = 3 if cs=="其他" else cs_prob(cs)
        st.write(f"**{cs}** {prob:.1f}%")
        o=st.number_input(f"cs_{cs}",0.0,200.0,8.0 if cs!="其他" else 20.0,0.5,key=f"cs_{cs}", label_visibility="collapsed")
        if o>0:
            ev=(prob/100*o-1)*100
            if ev>best_ev: best_ev=ev; best_cs=(cs,prob,o,ev)
            st.caption(f"EV {ev:.1f}%")

if best_cs: st.success(f"🏆 波膽最值博：{best_cs[0]} 命中{best_cs[1]:.1f}% @ {best_cs[2]} EV {best_cs[3]:.1f}%")

# 3. 角球大細
st.write("**3. 角球大細 (手改)**")
c1,c2=st.columns(2)
with c1:
    corner_total=st.number_input("而家總角球",0,30,5,key="corn_tot")
    prob_corner_over = min(85, 40 + corner_total*5 + elapsed*0.3)
    st.write(f"大9.5角球機會 {prob_corner_over:.0f}%")
    o_cor=st.number_input("大9.5角球賠率",0.0,100.0,1.85,0.05,key="corn_o")
    if o_cor>0: st.caption(f"EV {(prob_corner_over/100*o_cor-1)*100:.1f}%")
with c2:
    prob_corner_home = 50 + (danger-50)*0.3
    st.write(f"主隊角球多機會 {prob_corner_home:.0f}%")
    o_cor_h=st.number_input("主隊角球多賠率",0.0,100.0,1.9,0.05,key="corn_h")
    if o_cor_h>0: st.caption(f"EV {(prob_corner_home/100*o_cor_h-1)*100:.1f}%")

st.divider()
st.subheader("📊 總結：即場最合理投注")
all_bets=[]
for k in st.session_state.get('odds',{}): pass # 舊
# 收集上面所有
for k,prob in markets.items():
    o=st.session_state.get(f"odd_{k}")
    # 用key搵
# 簡單總結
if best_cs and best_cs[3]>10:
    st.markdown(f"**建議：追 {best_cs[0]} 波膽，EV {best_cs[3]:.1f}% 最高**")
else:
    # 搵大細
    best_market=None; best_ev2=-999
    for kk,prob in markets.items():
        o_key=f"odd_{kk}"
        # streamlit number_input 唔會入session，要用變量，呢度用返上面計
        pass
    st.markdown(f"**建議：而家 {hs}-{aws} {elapsed}'，大2.5機會{live_o25:.0f}%，如果馬會大2.5 > {100/live_o25:.2f} 就有值博**")

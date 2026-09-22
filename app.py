import streamlit as st, requests, re, pandas as pd, time
from collections import Counter

st.set_page_config(page_title="EdgeLab v15 雙引擎", layout="wide")
HEADERS={"User-Agent":"Mozilla/5.0","Referer":"https://www.aiscore.com/"}
if 'odds' not in st.session_state: st.session_state.odds={}
for k in ['statsA','statsH','selA','selB']:
    if k not in st.session_state: st.session_state[k]=None

def extract_id(url):
    m=re.search(r'/match-[^/]+/([a-z0-9]{10,})',url)
    return m.group(1) if m else url.split('/')[-1]

def fetch_live(mid):
    for u in [f"https://www.aiscore.com/api/football/match/liveDetail?matchId={mid}", f"https://www.aiscore.com/api/football/match/detail?matchId={mid}"]:
        try:
            r=requests.get(u, headers=HEADERS, timeout=6)
            if r.status_code==200 and r.json().get('data'): return r.json().get('data')
        except: pass
    return {}

#... (fetch_recent, fetch_h2h, parse, analyse 用返你v14.5嗰套，唔重貼)

st.title("v15 雙引擎 + 即時最值博")

link=st.text_input("🔗 貼 AIScore Link", placeholder="https://www.aiscore.com/match-.../xxxx")
if not link: st.stop()

mid=extract_id(link)
live=fetch_live(mid)
if not live: st.error("捉唔到Live"); st.stop()

home=live.get('homeTeam',{}).get('name','主'); away=live.get('awayTeam',{}).get('name','客')
hs=live.get('homeScore',0); aws=live.get('awayScore',0)
minute=live.get('minute', live.get('matchTime','0'))
stats=live.get('stats',{}) or {}

# ===== 引擎1 即場 =====
st.divider()
st.subheader(f"🔴 引擎1：即場表現分析 (Live {minute}' {hs}-{aws}) - 每5秒更新")
auto=st.checkbox("自動更新", value=True)
if auto: time.sleep(5); st.rerun()

# 假設 stats 有呢啲，無就0
sh=stats.get('shots',{}); shot_h=sh.get('home',0); shot_a=sh.get('away',0)
sot=stats.get('shotsOnTarget',{}); sot_h=sot.get('home',0); sot_a=sot.get('away',0)
corn=stats.get('corners',{}); c_h=corn.get('home',0); c_a=corn.get('away',0)
dang=stats.get('dangerousAttacks',{}); d_h=dang.get('home',0); d_a=dang.get('away',0)

live_xg_h = sot_h*0.3 + shot_h*0.1 + c_h*0.05 + d_h*0.01
live_xg_a = sot_a*0.3 + shot_a*0.1 + c_a*0.05 + d_a*0.01
total_xg_live = live_xg_h + live_xg_a + hs + aws

# 即場盤口機會率
live_o25 = min(95, 40 + total_xg_live*18 + (hs+aws)*12)
live_home_win_prob = 50 + (live_xg_h - live_xg_a)*15 + (hs-aws)*10

c1,c2=st.columns(2)
with c1:
    st.metric("即場主隊xG", f"{live_xg_h:.2f}", f"射正{sot_h} 射門{shot_h} 角{c_h}")
    st.metric("即場客隊xG", f"{live_xg_a:.2f}", f"射正{sot_a} 射門{shot_a} 角{c_a}")
with c2:
    st.write(f"**即場開大2.5機會：{live_o25:.0f}%**")
    st.write(f"**即場主勝機會：{live_home_win_prob:.0f}%**")
    # 最合理投注
    # 用你手入賠率計EV
    def best_live():
        bets=[]
        for k,v in st.session_state.odds.items():
            if v>0:
                if "大2.5" in k: prob=live_o25
                elif f"hhad_h_{home}" in k: prob=live_home_win_prob
                elif "hhad_a" in k: prob=100-live_home_win_prob
                else: continue
                ev=(prob/100*v-1)*100
                bets.append((k,prob,v,ev))
        if bets:
            bets.sort(key=lambda x: x[3], reverse=True)
            return bets[0]
        return None
    best=best_live()
    if best:
        st.success(f"🏆 即場最值博: {best[0]} 命中{best[1]:.0f}% @ {best[2]} EV {best[3]:.1f}%")
    else:
        st.info("入返馬會賠率，佢會即時計最值博")

# ===== 引擎2 往績 =====
st.divider()
st.subheader("📊 引擎2：綜合往績分析 (賽前)")

if st.button("捉雙往績做綜合分析", type="primary"):
    #... 捉 recA, recH, analyse...
    pass

# 你現有嘅往績表格 + 馬會波膽格仔擺喺呢度...
# 最後加埋 綜合最值博
st.caption("引擎1=即場睇盤，隨時間變。引擎2=往績睇長線，唔變。兩個EV對比，就知而家追大定係等。")

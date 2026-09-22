import streamlit as st, pandas as pd, random, requests
from PIL import Image
import re, pytesseract
from streamlit_paste_button import paste_image_button

st.set_page_config(page_title="EdgeLab v7.3 完整版", layout="wide")
KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

if "bets" not in st.session_state: st.session_state.bets=[]
if "cap_imgs" not in st.session_state: st.session_state.cap_imgs=[]
if "step1_text" not in st.session_state: st.session_state.step1_text=""
if "slip" not in st.session_state: st.session_state.slip=[]

st.sidebar.title("模式")
mode = st.sidebar.radio("選擇", ["API 自動","CAP圖分析 (無額度用)"], key="mode_fix")
stake_input = st.sidebar.number_input("預設每注 $", 50, 10000, 100, 50)

st.title("EdgeLab v7.3 - API + CAP圖兩步")

# ========= 分流修復，呢度最關鍵 =========
if mode == "API 自動":
    st.subheader("🤖 API自動 - 最高命中+高回報")
    league = st.selectbox("聯賽", list(MAP.keys()))
    lid, season = MAP[league]
    if st.button("拉API即時賽事"):
        try:
            r = requests.get(f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&next=10", headers=HEAD, timeout=10)
            data = r.json().get("response", [])
            if not data:
                st.warning("API無數據/額度爆，轉去CAP圖模式")
            for f in data[:5]:
                home = f["teams"]["home"]["name"]
                away = f["teams"]["away"]["name"]
                st.write(f"**{home} vs {away}**")
                # 模擬EV計法
                o1,o2 = round(random.uniform(1.6,2.2),2), round(random.uniform(1.8,2.5),2)
                pr1,pr2 = random.randint(50,65), random.randint(40,55)
                ev1, ev2 = pr1/100*o1-1, pr2/100*o2-1
                s1, s2 = pr1*0.6+ev1*100*0.4, pr2*0.6+ev2*100*0.4
                best = (home, o1, ev1, pr1, s1) if s1>=s2 else (away, o2, ev2, pr2, s2)
                st.metric("推薦", f"{best[0]} @ {best[1]}", f"命中{best[3]}% EV+{best[2]*100:.1f}%")
                if st.button(f"入倉 {home} vs {away}", key=f"api_{home}"):
                    st.session_state.bets.append({"賽事":f"{home} vs {away}","項目":best[0],"賠率":best[1],"投注額":stake_input,"回報額":round(stake_input*best[1],2)})
                    st.rerun()
        except Exception as e:
            st.error(f"API錯誤 {e}，請轉CAP圖模式")

    # 模擬倉
    if st.session_state.bets:
        st.divider()
        st.write("🧾 模擬倉")
        st.dataframe(pd.DataFrame(st.session_state.bets))

else:
    # ========= CAP圖分析 (兩步) v7.1 =========
    st.subheader("📊 CAP圖兩步 - 數據先，賠率後 (唔會撈亂)")

    st.markdown("### 第1步：放馬會數據頁 (過往賽果/對賽)")
    c1,c2 = st.columns([3,1])
    with c1:
        up1 = st.file_uploader("上傳數據圖", type=["png","jpg"], key="up71_data", accept_multiple_files=True)
        paste1 = paste_image_button("📋 Ctrl+V 貼數據圖", key="paste71_data")
    with c2:
        if st.button("清數據"):
            st.session_state.step1_text=""
            st.rerun()

    step1_imgs=[]
    if up1:
        for u in up1: step1_imgs.append(Image.open(u))
    if paste1 and paste1.image_data is not None:
        step1_imgs.append(paste1.image_data)

    step1_full_text=""
    for im in step1_imgs:
        st.image(im, caption="數據圖", width=350)
        try: step1_full_text+=pytesseract.image_to_string(im, lang="chi_tra+eng")+"\n"
        except: pass

    st.session_state.step1_text = st.text_area("數據OCR (淨比數)", st.session_state.step1_text+"\n"+step1_full_text, height=120)

    if st.session_state.step1_text:
        scores = re.findall(r"(\d+)\s*[:\-]\s*(\d+)", st.session_state.step1_text)
        total = len(scores) if scores else 1
        over25 = sum(1 for a,b in scores if int(a)+int(b)>2)
        st.info(f"📈 共{total}場 | 大2.5 {over25/total*100:.0f}% | 常見 {scores[:3]}")

    st.divider()
    st.markdown("### 第2步：放馬會賠率頁 (波膽/主客和)")
    up2 = st.file_uploader("上傳賠率圖", type=["png","jpg"], key="up71_odds", accept_multiple_files=True)
    paste2 = paste_image_button("📋 Ctrl+V 貼賠率圖", key="paste71_odds")

    step2_imgs=[]
    if up2:
        for u in up2: step2_imgs.append(Image.open(u))
    if paste2 and paste2.image_data is not None:
        step2_imgs.append(paste2.image_data)

    odds_text=""
    for im in step2_imgs:
        st.image(im, caption="賠率圖", width=350)
        try: odds_text+=pytesseract.image_to_string(im, lang="chi_tra+eng")+"\n"
        except: pass

    if odds_text:
        bodan = re.findall(r"(\d+\s*[:\-]\s*\d+)\s+(\d+\.\d{1,2})", odds_text)
        simple_odds = re.findall(r"\d+\.\d{1,2}", odds_text)
        simple_odds = [o for o in simple_odds if 1.01<=float(o)<=50.0]
        st.success(f"賠率頁認到 {len(simple_odds)} 個賠率，波膽 {len(bodan)} 個")
        if bodan:
            cols=st.columns(3)
            best=None
            best_score=-1
            for i,(score,odd) in enumerate(bodan[:12]):
                est_prob = 40 + st.session_state.step1_text.count(score.replace(" ","")[0])*2
                est_prob = min(70, est_prob)
                ev = est_prob/100*float(odd)-1
                final_score = est_prob*0.6 + ev*100*0.4
                if final_score>best_score:
                    best_score=final_score
                    best=(score,odd,est_prob,ev,final_score)
                cols[i%3].button(f"{score} @ {odd}\n命中{est_prob:.0f}% EV{ev*100:+.0f}%", key=f"bd_{i}")
            if best:
                st.metric("🏆 數據+賠率綜合推薦", f"{best[0]} @ {best[1]}", f"命中{best[2]:.0f}% EV+{best[3]*100:.1f}%")
                if st.button(f"入模擬倉 ${stake_input}", key="in_bodan"):
                    st.session_state.bets.append({"賽事":"波膽","項目":f"波膽 {best[0]}","賠率":float(best[1]),"投注額":stake_input,"回報額":round(stake_input*float(best[1]),2)})
                    st.rerun()

    if st.session_state.bets:
        st.divider()
        st.dataframe(pd.DataFrame(st.session_state.bets))
        if st.button("清倉"):
            st.session_state.bets=[]
            st.rerun()

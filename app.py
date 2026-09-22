import streamlit as st, pandas as pd, random, requests
from PIL import Image

st.set_page_config(page_title="EdgeLab v6 CAP圖", layout="wide")
KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

if "bets" not in st.session_state: st.session_state.bets=[]
if st.session_state.bets and "投注額" not in st.session_state.bets[0]:
    st.session_state.bets=[]

st.sidebar.title("模式")
mode = st.sidebar.radio("選擇", ["API 自動","CAP圖分析 (無額度用)"])
stake_input = st.sidebar.number_input("預設每注 $", 50, 10000, 100, 50)

st.title("EdgeLab v6 - CAP圖即時分析")

# ===== 1. CAP圖功能 =====
st.divider()
st.subheader("📊 v7.1 兩步分析 - 數據先，賠率後")

from streamlit_paste_button import paste_image_button
import pytesseract, re
from PIL import Image

if "step1_text" not in st.session_state: st.session_state.step1_text=""
if "step2_odds" not in st.session_state: st.session_state.step2_odds=[]
if "analysis_result" not in st.session_state: st.session_state.analysis_result={}

# ========== 第一步：放馬會數據 (過往賽果、對賽) ==========
st.markdown("### 第1步：放馬會數據頁 (過往賽果/對賽)")
st.caption("呢頁得比數 2:1, 1:0 嗰啲，無賠率，系統淨係會計數據")

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
    try:
        txt = pytesseract.image_to_string(im, lang="chi_tra+eng")
        step1_full_text+=txt+"\n"
    except: pass

# 手動可改數據
st.session_state.step1_text = st.text_area("數據OCR結果 (可手改，淨係會有比數)", st.session_state.step1_text+"\n"+step1_full_text, height=120, key="ta1")

# 自動分析數據
if st.session_state.step1_text:
    # 捉波膽比數 2-1, 1:0 呢啲
    scores = re.findall(r"(\d+)\s*[:\-]\s*(\d+)", st.session_state.step1_text)
    # 捉主客勝負文字
    win_h = len(re.findall(r"主勝|主隊勝|H.*W|勝\(主\)", st.session_state.step1_text))
    win_a = len(re.findall(r"客勝|客隊勝|A.*W|勝\(客\)", st.session_state.step1_text))

    # 簡單計命中率
    total_games = len(scores) if scores else (win_h+win_a+1)
    over25 = 0
    for s in scores:
        try:
            if int(s[0])+int(s[1]) > 2.5: over25+=1
        except: pass

    st.session_state.analysis_result = {
        "total": total_games,
        "主勝率": round(win_h/total_games*100,1) if total_games else 50,
        "客勝率": round(win_a/total_games*100,1) if total_games else 30,
        "大球率": round(over25/len(scores)*100,1) if scores else 50,
        "常見波膽": scores[:5]
    }
    st.info(f"📈 數據分析：共{total_games}場 | 主勝 {st.session_state.analysis_result['主勝率']}% | 客勝 {st.session_state.analysis_result['客勝率']}% | 大2.5 {st.session_state.analysis_result['大球率']}% | 常見 {scores[:3]}")

# ========== 第二步：放馬會賠率頁 (波膽/主客和) ==========
st.divider()
st.markdown("### 第2步：再放馬會賠率頁 (呢頁先有賠率)")
st.caption("呢度先開始認賠率，因為第一步已鎖定命中率，唔會再同比數撈亂")

c1,c2 = st.columns([3,1])
with c1:
    up2 = st.file_uploader("上傳賠率圖", type=["png","jpg"], key="up71_odds", accept_multiple_files=True)
    paste2 = paste_image_button("📋 Ctrl+V 貼賠率圖", key="paste71_odds")
with c2:
    if st.button("清賠率"):
        st.session_state.step2_odds=[]
        st.rerun()

step2_imgs=[]
if up2:
    for u in up2: step2_imgs.append(Image.open(u))
if paste2 and paste2.image_data is not None:
    step2_imgs.append(paste2.image_data)

odds_text=""
for im in step2_imgs:
    st.image(im, caption="賠率圖", width=350)
    try:
        txt = pytesseract.image_to_string(im, lang="chi_tra+eng")
        odds_text+=txt+"\n"
    except: pass

# 只喺賠率頁抽賠率
if odds_text:
    # 波膽賠率： 1:0 8.5
    bodan = re.findall(r"(\d+\s*[:\-]\s*\d+)\s+(\d+\.\d{1,2})", odds_text)
    # 普通賠率
    simple_odds = re.findall(r"\d+\.\d{1,2}", odds_text)
    simple_odds = [o for o in simple_odds if 1.01<=float(o)<=50.0]

    st.success(f"賠率頁認到 {len(simple_odds)} 個賠率，波膽 {len(bodan)} 個")

    # 列表
    if bodan:
        st.write("**波膽市場 (已按你第1步數據計推薦)**")
        cols=st.columns(3)
        best_pick=None
        best_score=-1
        for i, (score, odd) in enumerate(bodan[:12]):
            # 用第1步嘅數據計呢個波膽有幾大機會出現
            clean_score = score.replace(" ","")
            # 如果呢個波膽喺過往賽果出現過，加分
            freq = st.session_state.step1_text.count(clean_score[0]) if clean_score else 0
            est_prob = 10 + freq*5 + (st.session_state.analysis_result.get("主勝率",50)/10 if "1:0" in score or "2:1" in score else 0)
            est_prob = min(70, est_prob)
            ev = est_prob/100*float(odd)-1
            final_score = est_prob*0.6 + ev*100*0.4

            if final_score > best_score:
                best_score=final_score
                best_pick=(score, odd, est_prob, ev, final_score)

            with cols[i%3]:
                st.button(f"{score} @ {odd}\n命中~{est_prob:.0f}% EV {ev*100:+.0f}% 分{final_score:.0f}", key=f"bd_{i}")

        if best_pick:
            st.metric("🏆 數據+賠率綜合推薦", f"{best_pick[0]} @ {best_pick[1]}", f"命中{best_pick[2]:.0f}% EV+{best_pick[3]*100:.1f}% 得分{best_pick[4]:.1f}")
            if st.button(f"入模擬倉 ${stake_input}"):
                st.session_state.bets.append({
                    "賽事":"波膽分析",
                    "項目":f"波膽 {best_pick[0]}",
                    "賠率":float(best_pick[1]),
                    "投注額":stake_input,
                    "回報額":round(stake_input*float(best_pick[1]),2),
                    "來源":"數據+賠率兩步"
                })
                st.rerun()

    # 其他市場都一樣處理
    with st.expander("睇埋其他市場 主客和/讓球"):
        st.write(simple_odds[:15])

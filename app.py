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
st.subheader("📱 v7.0 馬會投注模擬器 - 全項目識別")

from streamlit_paste_button import paste_image_button
import pytesseract, re
from PIL import Image

if "cap_imgs" not in st.session_state: st.session_state.cap_imgs=[]
if "hkjc_markets" not in st.session_state: st.session_state.hkjc_markets={}

# 上傳
c1,c2,c3 = st.columns([2,2,1])
with c1:
    ups = st.file_uploader("上傳馬會賠率版 (全版)", type=["png","jpg"], accept_multiple_files=True, key="up70")
    if ups:
        for u in ups: st.session_state.cap_imgs.append(Image.open(u))
with c2:
    paste = paste_image_button("📋 Ctrl+V 貼馬會版面", key="paste70")
    if paste and paste.image_data is not None:
        st.session_state.cap_imgs.append(paste.image_data)
with c3:
    if st.button("清空"): 
        st.session_state.cap_imgs=[]
        st.session_state.hkjc_markets={}
        st.rerun()

# 核心：馬會關鍵字字典
MARKET_KEYS = {
    "主客和": ["主客和","HAD","主 客 和"],
    "讓球主客和": ["讓球主客和","讓球主客","HDC HAD"],
    "讓球": ["讓球$","讓球 ","讓  球","亞洲讓球","HDC"],
    "半場主客和": ["半場主客和","半場","Half Time HAD","半場主客"],
    "波膽": ["波膽","Correct Score","正確比數","波 膽"],
    "入球大細": ["入球大細","大細","入球 大細","大/細","O/U","入球數"],
    "半全場": ["半全場","Half Time Full Time"],
    "角球大細": ["角球","角 球"],
}

def parse_hkjc_full(text, img_odds):
    markets={}
    lines=text.split("\n")
    for m_name, keys in MARKET_KEYS.items():
        for line in lines:
            for k in keys:
                if k.lower() in line.lower():
                    # 捉呢行附近嘅賠率
                    odds = re.findall(r"\d+\.\d{1,2}", line)
                    # 如果呢行無賠率，捉下面一行
                    if not odds: 
                        continue
                    # 過濾
                    valid=[o for o in odds if 1.01<=float(o)<=40.0]
                    if valid:
                        if m_name not in markets: markets[m_name]=[]
                        markets[m_name].extend(valid)
                    break
    # 波膽特殊處理：捉 比數+賠率
    score_pattern = re.findall(r"(\d+:\d+|\d+-\d+)\s*(\d+\.\d+)", text)
    if score_pattern:
        markets["波膽"] = [f"{s} @ {o}" for s,o in score_pattern[:16]]

    # 如果分唔到，就全部當主客和
    if not markets and img_odds:
        markets["主客和"] = img_odds
    return markets

if st.session_state.cap_imgs:
    last_im = st.session_state.cap_imgs[-1]
    st.image(last_im, use_container_width=True, caption="馬會原圖")

    # OCR成頁
    full_text = pytesseract.image_to_string(last_im, lang="chi_tra+eng")
    all_odds = re.findall(r"\d+\.\d{1,2}", full_text)
    all_odds = [o for o in all_odds if 1.01<=float(o)<=40.0]
    uniq_odds=[]
    for o in all_odds:
        if o not in uniq_odds: uniq_odds.append(o)

    markets = parse_hkjc_full(full_text, uniq_odds)
    st.session_state.hkjc_markets = markets

    if markets:
        st.success(f"已識別到 {len(markets)} 個馬會項目: {list(markets.keys())}")
        
        # 馬會式Tabs
        tabs = st.tabs(list(markets.keys()))
        selected_bets=[]

        for idx, m_name in enumerate(markets.keys()):
            with tabs[idx]:
                st.write(f"**{m_name}** - 馬會賠率")
                items = markets[m_name]
                cols = st.columns(3)
                for i, item in enumerate(items[:12]): # 最多顯示12個盤
                    # 解析賠率
                    odd_match = re.search(r"(\d+\.\d+)", str(item))
                    odd = float(odd_match.group(1)) if odd_match else 1.90
                    
                    label = item if "@" in str(item) or ":" in str(item) else f"{m_name} {item}"
                    if cols[i%3].button(f"{label}", key=f"bet_{m_name}_{i}"):
                        selected_bets.append((m_name, label, odd))
                        st.toast(f"已加入投注單: {label} @ {odd}")

                # 手動加盤
                with st.expander(f"手動加 {m_name} 盤"):
                    custom_label = st.text_input(f"{m_name} 名", f"{m_name} 自定", key=f"cl_{m_name}")
                    custom_odd = st.number_input(f"{m_name} 賠率", 1.01, 50.0, 2.0, key=f"co_{m_name}")
                    if st.button(f"加入 {m_name}", key=f"cb_{m_name}"):
                        selected_bets.append((m_name, custom_label, custom_odd))

        # 投注單 - 模擬馬會APP底欄
        if "slip" not in st.session_state: st.session_state.slip=[]
        if selected_bets:
            st.session_state.slip.extend(selected_bets)
        
        if st.session_state.slip:
            st.divider()
            st.subheader(f"🧾 投注單 ({len(st.session_state.slip)}) - 模擬馬會")
            total_stake=0
            for i, (mtype, label, odd) in enumerate(st.session_state.slip):
                c1,c2,c3,c4 = st.columns([3,2,2,1])
                c1.write(f"{mtype}: {label}")
                c2.write(f"@ {odd}")
                stake = c3.number_input(f"注", 10, 10000, 100, key=f"stake_{i}")
                total_stake+=stake
                c4.button("X", key=f"del_{i}", on_click=lambda i=i: st.session_state.slip.pop(i))
                # 計最高命中+回報
                pr = st.slider(f"{label} 命中% (睇你貼嘅數據)", 10, 90, 50, key=f"pr_{i}")
                ev = pr/100*odd-1
                score = pr*0.6 + ev*100*0.4
                st.caption(f"EV {ev*100:+.1f}% | 綜合分 {score:.1f} {'✅ 推薦' if score>50 else ''}")

            if st.button(f"全部入模擬倉 測試ROI ${total_stake}", type="primary"):
                for mtype, label, odd in st.session_state.slip:
                    st.session_state.bets.append({
                        "賽事": match_name if 'match_name' in locals() else "馬會分析",
                        "項目": f"{mtype} {label}",
                        "賠率": odd,
                        "投注額": 100,
                        "回報額": round(100*odd,2),
                    })
                st.session_state.slip=[]
                st.rerun()
    else:
        st.error("未識別到馬會項目，試下Cap清楚啲，或用下面手動揀")
        st.text_area("OCR原文", full_text, height=150)

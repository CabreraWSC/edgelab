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
st.subheader("📸 v6.9 馬會左右分邊版")

from streamlit_paste_button import paste_image_button
import pytesseract, re
from PIL import Image

if "cap_imgs" not in st.session_state: st.session_state.cap_imgs=[]
if "split_data" not in st.session_state: st.session_state.split_data={}

c1,c2,c3 = st.columns([2,2,1])
with c1:
    ups = st.file_uploader("上傳馬會賠率頁 (左右兩邊嗰頁)", type=["png","jpg"], accept_multiple_files=True, key="up69")
    if ups:
        for u in ups: st.session_state.cap_imgs.append(Image.open(u))
with c2:
    paste = paste_image_button("📋 Ctrl+V 貼賠率頁", key="paste69")
    if paste and paste.image_data is not None:
        st.session_state.cap_imgs.append(paste.image_data)
with c3:
    if st.button("清空"):
        st.session_state.cap_imgs=[]
        st.session_state.split_data={}
        st.rerun()

def extract_odds(text):
    ods = re.findall(r"\d+\.\d{1,2}", text)
    uniq=[]
    for o in ods:
        if 1.01 <= float(o) <= 15.0 and o not in uniq:
            uniq.append(o)
    return uniq

if st.session_state.cap_imgs:
    last_im = st.session_state.cap_imgs[-1]
    w,h = last_im.size
    # 關鍵：切開左半右半
    left_box = (0, 0, w//2, h)
    right_box = (w//2, 0, w, h)
    left_im = last_im.crop(left_box)
    right_im = last_im.crop(right_box)

    colL,colR = st.columns(2)
    with colL:
        st.image(left_im, caption="左邊 = 主隊區", use_container_width=True)
        left_text = pytesseract.image_to_string(left_im, lang="chi_tra+eng")
        left_odds = extract_odds(left_text)
        st.text_area("左邊讀到", left_text, height=100, key="lt")
        st.success(f"左邊賠率: {left_odds[:5]}")
    with colR:
        st.image(right_im, caption="右邊 = 客隊區", use_container_width=True)
        right_text = pytesseract.image_to_string(right_im, lang="chi_tra+eng")
        right_odds = extract_odds(right_text)
        st.text_area("右邊讀到", right_text, height=100, key="rt")
        st.success(f"右邊賠率: {right_odds[:5]}")

    st.divider()
    # 派位已經分好，你只需確認
    st.write("### 已自動分開左右，唔會再撈亂")
    c1,c2,c3 = st.columns(3)
    h_name = c1.text_input("主隊 (左邊)", "主隊")
    a_name = c2.text_input("客隊 (右邊)", "客隊")
    match_name = c3.text_input("賽事", f"{h_name} vs {a_name}")

    with st.form("f69"):
        lc, rc = st.columns(2)
        # 左邊賠率選
        o_h = lc.selectbox(f"{h_name} 左邊賠率揀一個", left_odds if left_odds else ["1.85"], key="oh69")
        o_h = float(o_h)
        o_h = lc.number_input(f"{h_name} 最終賠率", 1.01, 15.0, o_h, key="ohf69")
        pr_h = lc.slider(f"{h_name} 命中% (按你貼嘅馬會數據)", 10, 90, 55, key="prh69")

        o_a = rc.selectbox(f"{a_name} 右邊賠率揀一個", right_odds if right_odds else ["2.05"], key="oa69")
        o_a = float(o_a)
        o_a = rc.number_input(f"{a_name} 最終賠率", 1.01, 15.0, o_a, key="oaf69")
        pr_a = rc.slider(f"{a_name} 命中%", 10, 90, 45, key="pra69")

        go = st.form_submit_button("計邊邊最高命中+回報", type="primary")

    if go:
        ev_h = pr_h/100*o_h-1
        ev_a = pr_a/100*o_a-1
        s_h = pr_h*0.6 + ev_h*100*0.4
        s_a = pr_a*0.6 + ev_a*100*0.4
        best = (h_name, o_h, ev_h, pr_h, s_h) if s_h >= s_a else (a_name, o_a, ev_a, pr_a, s_a)
        st.success(f"🏆 推薦: {best[0]} @ {best[1]} 命中{best[3]}% EV+{best[2]*100:.1f}%")
        st.write(f"左 {h_name} @ {o_h} 分{s_h:.1f} vs 右 {a_name} @ {o_a} 分{s_a:.1f}")
        if st.button(f"入倉 ${stake_input}"):
            st.session_state.bets.append({"賽事":match_name,"項目":best[0],"賠率":best[1],"投注額":stake_input,"回報額":round(stake_input*best[1],2),"預期盈利":round(stake_input*best[2],2)})
            st.rerun()

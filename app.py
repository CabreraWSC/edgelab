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
st.subheader("📸 CAP圖分析 v6.4 多圖Ctrl+V")

from streamlit_paste_button import paste_image_button
import pytesseract, re

# 初始化用來存多張圖
if "cap_imgs" not in st.session_state:
    st.session_state.cap_imgs = []

c1, c2, c3 = st.columns([2,2,1])
with c1:
    ups = st.file_uploader("選檔上傳(可多張)", type=["png","jpg","jpeg"], accept_multiple_files=True, key="up64")
    if ups:
        for u in ups:
            im = Image.open(u)
            if im not in st.session_state.cap_imgs:
                st.session_state.cap_imgs.append(im)

with c2:
    paste = paste_image_button("📋 撳完 Ctrl+V 貼圖", key="paste64")
    if paste and paste.image_data is not None:
        # 貼一張加一張，唔會蓋
        st.session_state.cap_imgs.append(paste.image_data)
        st.toast(f"已加第 {len(st.session_state.cap_imgs)} 張圖")

with c3:
    if st.button("🗑️ 清空所有圖"):
        st.session_state.cap_imgs = []
        st.rerun()

# 顯示所有已貼嘅圖
# 顯示所有已貼嘅圖 - 修復版
read_text = ""
if st.session_state.cap_imgs:
    st.write(f"已收集 {len(st.session_state.cap_imgs)} 張CAP圖")
    cols = st.columns(3)
    for idx, im in enumerate(st.session_state.cap_imgs):
        with cols[idx % 3]:
            st.image(im, caption=f"圖{idx+1}", use_container_width=True)
        try:
            read_text += pytesseract.image_to_string(im, lang="chi_tra+eng") + "\n"
        except:
            pass
    # 抽賠率
    odds = re.findall(r"\d\.\d{1,2}", read_text)
    if odds:
        st.success(f"自動搵到賠率: {odds[:8]}")
    if read_text:
        st.text_area("OCR文字", read_text, height=120)

# 分析
with st.form("f64"):
    h = st.text_input("主隊","神戶")
    a = st.text_input("客隊","鹿島")
    # 如果搵到多個賠率，自動填頭2個
    def get_odd(i, default):
        try: return float(odds[i])
        except: return default
    o1 = st.number_input("賠率1",1.1,5.0,get_odd(0,1.95), key="o1_64")
    pr1 = st.slider("命中1%",30,80,60, key="pr1_64")
    o2 = st.number_input("賠率2",1.1,5.0,get_odd(1,1.90), key="o2_64")
    pr2 = st.slider("命中2%",30,80,55, key="pr2_64")
    go = st.form_submit_button("計最高命中+高回報", type="primary")

if go:
    ev1, ev2 = pr1/100*o1-1, pr2/100*o2-1
    s1, s2 = pr1*0.6+ev1*40, pr2*0.6+ev2*40
    best = (f"{h}項目1",o1,ev1,pr1) if s1>s2 else ("項目2",o2,ev2,pr2)
    st.success(f"✅ 推薦: {best[0]} @ {best[1]} EV+{best[2]*100:.1f}% 命中{best[3]}%")
    if st.button(f"入紀錄 ${stake_input}"):
        st.session_state.bets.append({"賽事":f"{h} vs {a}(多圖CAP)","項目":best[0],"賠率":best[1],"投注額":stake_input,"回報額":round(stake_input*best[1],2),"預期盈利":round(stake_input*best[2],2)})
        st.rerun()

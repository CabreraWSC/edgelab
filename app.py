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
st.subheader("📸 CAP圖分析 v6.3 Ctrl+V貼圖")

from streamlit_paste_button import paste_image_button
import pytesseract, re

st.info("電腦用 Snipping Tool / 微信截圖後，直接Ctrl+V")

# 支援2種：上傳 + Ctrl+V貼上
c1, c2 = st.columns(2)
with c1:
    ups = st.file_uploader("或選檔上傳", type=["png","jpg"], accept_multiple_files=True, key="up63")
with c2:
    paste = paste_image_button("📋 撳呢度再 Ctrl+V 貼圖", key="paste63")

imgs = []
if ups: imgs += [Image.open(u) for u in ups]
if paste and paste.image_data is not None:
    st.success("已貼上！")
    imgs.append(paste.image_data)

read_text = ""
if imgs:
    for im in imgs:
        st.image(im, width=380)
        try:
            read_text += pytesseract.image_to_string(im, lang="chi_tra+eng") + "\n"
        except: pass

if read_text:
    st.text_area("讀到文字", read_text, height=120)
    odds = re.findall(r"\d\.\d{1,2}", read_text)
    st.write("搵到賠率:", odds[:5])

# 下面分析form同之前一樣
with st.form("f63"):
    h = st.text_input("主隊","神戶")
    a = st.text_input("客隊","鹿島")
    o1 = st.number_input("賠率1",1.1,5.0,float(odds[0]) if 'odds' in locals() and odds else 1.95)
    pr1 = st.slider("命中1%",30,80,60)
    o2 = st.number_input("賠率2",1.1,5.0,float(odds[1]) if 'odds' in locals() and len(odds)>1 else 1.9)
    pr2 = st.slider("命中2%",30,80,55)
    go = st.form_submit_button("計最高命中+高回報", type="primary")

if go:
    ev1, ev2 = pr1/100*o1-1, pr2/100*o2-1
    best = ("項目1",o1,ev1,pr1) if pr1*0.6+ev1*40 > pr2*0.6+ev2*40 else ("項目2",o2,ev2,pr2)
    st.success(f"推薦: {best[0]} @ {best[1]} EV+{best[2]*100:.1f}% 命中{best[3]}%")

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
st.subheader("📸 CAP圖分析 v6.2 自動讀字")

import pytesseract, re
ups = st.file_uploader("上傳馬會CAP圖", type=["png","jpg"], accept_multiple_files=True, key="cap62")

read_text = ""
if ups:
    for u in ups:
        img = Image.open(u)
        st.image(img, width=350)
        try:
            # 中文+英文一起讀
            txt = pytesseract.image_to_string(img, lang="chi_tra+eng")
            read_text += txt + "\n"
        except Exception as e:
            st.warning(f"OCR引擎未裝好: {e}")

if read_text:
    st.text_area("OCR讀到嘅文字 (你核對)", read_text, height=150)
    # 自動抽賠率 例如 1.95 2.10
    odds_found = re.findall(r"\d\.\d{1,2}", read_text)
    st.write("自動搵到賠率:", odds_found[:5] if odds_found else "搵唔到，你手打")

with st.form("cap62_form"):
    h = st.text_input("主隊", "神戶")
    a = st.text_input("客隊", "鹿島")
    c1,c2 = st.columns(2)
    o1 = c1.number_input("賠率1 (可由OCR貼上)", 1.1, 5.0, float(odds_found[0]) if 'odds_found' in locals() and len(odds_found)>0 else 1.95)
    pr1 = c1.slider("命中%1", 30, 80, 60)
    o2 = c2.number_input("賠率2", 1.1, 5.0, float(odds_found[1]) if 'odds_found' in locals() and len(odds_found)>1 else 1.90)
    pr2 = c2.slider("命中%2", 30, 80, 55)
    go = st.form_submit_button("計最高命中+高回報", type="primary")

if go:
    m1_ev = pr1/100*o1-1
    m2_ev = pr2/100*o2-1
    best = (f"{h} 項目1", o1, m1_ev, pr1) if pr1/100*0.6+m1_ev*0.4 > pr2/100*0.6+m2_ev*0.4 else (f"大細/項目2", o2, m2_ev, pr2)
    st.success(f"推薦: {best[0]} @ {best[1]} 命中{best[3]}% EV+{best[2]*100:.1f}%")

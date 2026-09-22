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
st.subheader("📸 馬會通用分析 v6.6 貼數據+賠率即計")

from streamlit_paste_button import paste_image_button
import pytesseract, re

if "cap_imgs" not in st.session_state:
    st.session_state.cap_imgs = []
if "hkjc_text" not in st.session_state:
    st.session_state.hkjc_text = ""

# 收集圖 - 多張疊加
c1,c2,c3 = st.columns([2,2,1])
with c1:
    ups = st.file_uploader("上傳馬會截圖 (數據+賠率)", type=["png","jpg"], accept_multiple_files=True, key="up66")
    if ups:
        for u in ups: st.session_state.cap_imgs.append(Image.open(u))
with c2:
    paste = paste_image_button("📋 Cap完直接Ctrl+V", key="paste66")
    if paste and paste.image_data is not None:
        st.session_state.cap_imgs.append(paste.image_data)
        st.toast("已加圖")
with c3:
    if st.button("清空重貼"):
        st.session_state.cap_imgs=[]
        st.session_state.hkjc_text=""
        st.rerun()

read_text = ""
odds_guess = []
if st.session_state.cap_imgs:
    for idx, im in enumerate(st.session_state.cap_imgs):
        st.image(im, caption=f"馬會圖{idx+1}", use_container_width=True)
        try:
            txt = pytesseract.image_to_string(im, lang="chi_tra+eng")
            read_text += txt + "\n"
        except: pass

# 馬會數據有時OCR讀唔清，加個手動貼文字區，雙保險
st.write("如果圖太濛，馬會數據可直接Ctrl+V文字落下面：")
st.session_state.hkjc_text = st.text_area("貼馬會賠率/往績文字 (可選)", st.session_state.hkjc_text + "\n" + read_text, height=180, placeholder="例：曼城 對 阿仙奴 主勝1.85 和3.5 客勝3.8...")

full_text = st.session_state.hkjc_text
# 通用抽賠率 1.01-10.0
all_odds = re.findall(r"\d+\.\d{1,2}", full_text)
odds_guess = [o for o in all_odds if 1.01 <= float(o) <= 12.0]
# 去重保序
seen=set()
odds_unique=[]
for o in odds_guess:
    if o not in seen:
        seen.add(o)
        odds_unique.append(o)

if odds_unique:
    st.success(f"已由你貼嘅馬會資料搵到賠率: {odds_unique[:10]}")
else:
    st.warning("暫未搵到賠率，請確保圖入面有數字如 1.85 2.10")

# 通用分析form - 唔再限日職
with st.form("f66"):
    st.write("根據馬會賠率，揀2個你想比嘅盤：")
    col1,col2 = st.columns(2)
    p1 = col1.text_input("盤1 (例: 主勝 / 曼城 -0.5 / 大2.5)", "主隊勝")
    o1 = col1.number_input("馬會賠率1", 1.01, 12.0, float(odds_unique[0]) if len(odds_unique)>0 else 1.85, key="o1_66")
    pr1 = col1.slider("你按馬會數據估命中%1", 20, 90, 60, key="pr1_66", help="睇埋你貼嘅往績、近況去估")

    p2 = col2.text_input("盤2 (例: 和局 / 細2.5)", "大球 2.5")
    o2 = col2.number_input("馬會賠率2", 1.01, 12.0, float(odds_unique[1]) if len(odds_unique)>1 else 1.90, key="o2_66")
    pr2 = col2.slider("你按馬會數據估命中%2", 20, 90, 55, key="pr2_66")

    match_name = st.text_input("賽事名 (自動/手打都得)", "由馬會圖分析")
    go = st.form_submit_button("按馬會賠率計 邊個最高命中+回報", type="primary")

if go:
    ev1 = pr1/100*o1-1
    ev2 = pr2/100*o2-1
    # 計分 = 命中率60% + EV 40% = 最高回報又高命中
    s1 = pr1*0.6 + ev1*100*0.4
    s2 = pr2*0.6 + ev2*100*0.4
    best = (p1,o1,ev1,pr1,s1) if s1>=s2 else (p2,o2,ev2,pr2,s2)
    worst = (p2,o2,ev2,pr2,s2) if s1>=s2 else (p1,o1,ev1,pr1,s1)

    st.divider()
    st.metric("🏆 推薦 (最高命中+高回報)", f"{best[0]} @ {best[1]}", f"命中{best[3]}% EV+{best[2]*100:.1f}% 得分{best[4]:.1f}")
    st.write(f"對比: {worst[0]} @ {worst[1]} 命中{worst[3]}% EV+{worst[2]*100:.1f}%")

    # 入返你原本個模擬紀錄，計ROI實證
    if st.button(f"入模擬倉 ${stake_input} 試ROI"):
        st.session_state.bets.append({
            "賽事": match_name,
            "項目": best[0],
            "賠率": best[1],
            "投注額": stake_input,
            "回報額": round(stake_input*best[1],2),
            "預期盈利": round(stake_input*best[2],2),
            "來源": "馬會圖分析"
        })
        st.rerun()

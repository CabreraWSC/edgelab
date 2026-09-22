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
st.subheader("📸 馬會通用分析 v6.8 手動派位版 - 絕不撈亂")

from streamlit_paste_button import paste_image_button
import pytesseract, re

if "cap_imgs" not in st.session_state:
    st.session_state.cap_imgs = []
if "hkjc_text" not in st.session_state:
    st.session_state.hkjc_text = ""

c1,c2,c3 = st.columns([2,2,1])
with c1:
    ups = st.file_uploader("上傳馬會截圖", type=["png","jpg"], accept_multiple_files=True, key="up68")
    if ups:
        for u in ups: st.session_state.cap_imgs.append(Image.open(u))
with c2:
    paste = paste_image_button("📋 Ctrl+V貼圖", key="paste68")
    if paste and paste.image_data is not None:
        st.session_state.cap_imgs.append(paste.image_data)
with c3:
    if st.button("清空"):
        st.session_state.cap_imgs=[]
        st.session_state.hkjc_text=""
        st.rerun()

read_text=""
for im in st.session_state.cap_imgs:
    st.image(im, use_container_width=True)
    try: read_text+=pytesseract.image_to_string(im, lang="chi_tra+eng")+"\n"
    except: pass

st.session_state.hkjc_text = st.text_area("馬會文字 (OCR自動，你見錯可手改)", (st.session_state.hkjc_text+"\n"+read_text).strip(), height=150)

# 抽晒所有賠率
all_odds = re.findall(r"\d+\.\d{1,2}", st.session_state.hkjc_text)
odds_unique=[]
for o in all_odds:
    if 1.01 <= float(o) <= 15.0 and o not in odds_unique:
        odds_unique.append(o)

if not odds_unique:
    st.warning("未搵到賠率，手打入去例如 1.85 3.5 3.8 都得")
    odds_unique = ["1.85","3.50","3.80"]

st.write(f"搵到 {len(odds_unique)} 個賠率：", odds_unique)

# 核心：你手動派位
st.write("### 第一步：派位 (保證唔會錯)")
colA,colB,colC = st.columns(3)
# 預設選項
opts = ["(不選)"] + odds_unique
def_idx = lambda v: opts.index(v) if v in opts else 0

# 記住上次派位
if "assign" not in st.session_state: st.session_state.assign = {}

with colA:
    h_name = st.text_input("主隊名", "主隊")
    sel_h = st.selectbox(f"{h_name} 賠率揀邊個", opts, index=def_idx(odds_unique[0]) if odds_unique else 0, key="sel_h")
    o_h_manual = st.number_input(f"{h_name} 賠率微調", 1.01, 15.0, float(sel_h) if sel_h!="(不選)" else 1.85)
with colB:
    d_name = st.text_input("和局名", "和局")
    sel_d = st.selectbox(f"{d_name} 賠率揀邊個", opts, index=def_idx(odds_unique[1]) if len(odds_unique)>1 else 0, key="sel_d")
    o_d_manual = st.number_input(f"{d_name} 賠率微調", 1.01, 15.0, float(sel_d) if sel_d!="(不選)" else 3.50)
with colC:
    a_name = st.text_input("客隊名", "客隊")
    sel_a = st.selectbox(f"{a_name} 賠率揀邊個", opts, index=def_idx(odds_unique[2]) if len(odds_unique)>2 else 0, key="sel_a")
    o_a_manual = st.number_input(f"{a_name} 賠率微調", 1.01, 15.0, float(sel_a) if sel_a!="(不選)" else 3.80)

st.divider()
st.write("### 第二步：按馬會數據估命中率，再計最高回報")

with st.form("f68"):
    c1,c2,c3 = st.columns(3)
    pr_h = c1.slider(f"{h_name} 命中%", 10, 90, 50, key="pr_h")
    pr_d = c2.slider(f"{d_name} 命中%", 5, 60, 25, key="pr_d")
    pr_a = c3.slider(f"{a_name} 命中%", 10, 90, 30, key="pr_a")
    match_name = st.text_input("賽事名", f"{h_name} vs {a_name}")
    go = st.form_submit_button("計 最高命中+高回報", type="primary")

if go:
    ev_h = pr_h/100*o_h_manual-1
    ev_d = pr_d/100*o_d_manual-1
    ev_a = pr_a/100*o_a_manual-1
    s_h = pr_h*0.6 + ev_h*100*0.4
    s_d = pr_d*0.6 + ev_d*100*0.4
    s_a = pr_a*0.6 + ev_a*100*0.4
    res = [(h_name, o_h_manual, ev_h, pr_h, s_h), (d_name, o_d_manual, ev_d, pr_d, s_d), (a_name, o_a_manual, ev_a, pr_a, s_a)]
    res.sort(key=lambda x: x[4], reverse=True)
    best = res[0]
    st.success(f"🏆 推薦：{best[0]} @ {best[1]} 命中{best[3]}% EV+{best[2]*100:.1f}%")
    for r in res:
        st.write(f"- {r[0]} @ {r[1]} 命中{r[3]}% EV {r[2]*100:+.1f}% 分 {r[4]:.1f}")

    if st.button(f"入模擬倉 ${stake_input}"):
        st.session_state.bets.append({"賽事":match_name,"項目":best[0],"賠率":best[1],"投注額":stake_input,"回報額":round(stake_input*best[1],2),"預期盈利":round(stake_input*best[2],2)})
        st.rerun()

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
st.subheader("📸 CAP圖分析 (API無額度用)")

# 1. 上傳 - 放form外面，即刻有反應
ups = st.file_uploader("上傳馬會CAP圖", type=["png","jpg","jpeg"], accept_multiple_files=True, key="cap_up")
if ups:
    st.write(f"已收到 {len(ups)} 張圖")
    for u in ups:
        try:
            img = Image.open(u)
            st.image(img, caption=u.name, width=350)
        except:
            st.write(f"讀唔到 {u.name}")

    st.success("圖已讀到！落去下面入賠率就計到")

# 2. 分析 - 獨立form
with st.form("cap_form_v61"):
    c1,c2 = st.columns(2)
    h = c1.text_input("主隊", "神戶勝利船")
    a = c2.text_input("客隊", "鹿島鹿角")
    
    c1,c2 = st.columns(2)
    p1 = c1.text_input("項目1", f"{h} -0.25")
    o1 = c1.number_input("賠率1", 1.1, 5.0, 1.95, key="o1")
    pr1 = c1.slider("你估命中%1", 30, 80, 60, key="pr1")
    
    p2 = c2.text_input("項目2", "大2.5")
    o2 = c2.number_input("賠率2", 1.1, 5.0, 1.90, key="o2")
    pr2 = c2.slider("你估命中%2", 30, 80, 55, key="pr2")

    go = st.form_submit_button("即時分析", type="primary")

if go:
    m1_ev = pr1/100*o1-1
    m2_ev = pr2/100*o2-1
    s1 = pr1/100*0.6 + m1_ev*0.4
    s2 = pr2/100*0.6 + m2_ev*0.4
    
    if s1 > s2:
        best_pick, best_odds, best_ev = p1, o1, m1_ev
        best_hit = pr1
    else:
        best_pick, best_odds, best_ev = p2, o2, m2_ev
        best_hit = pr2

    st.success(f"✅ 推薦: {best_pick} @ {best_odds} 命中{best_hit}% EV+{best_ev*100:.1f}%")
    
    if st.button(f"入模擬紀錄 ${stake_input} -> 回報 ${round(stake_input*best_odds,2)}"):
        st.session_state.bets.append({
            "賽事": f"{h} vs {a}(CAP)",
            "項目": best_pick,
            "賠率": best_odds,
            "投注額": stake_input,
            "回報額": round(stake_input*best_odds,2),
            "預期盈利": round(stake_input*best_ev,2),
        })
        st.rerun()

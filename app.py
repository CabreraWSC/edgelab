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
st.subheader("📸 馬會通用分析 v6.7 分清主客版")

from streamlit_paste_button import paste_image_button
import pytesseract, re

if "cap_imgs" not in st.session_state:
    st.session_state.cap_imgs = []
if "hkjc_text" not in st.session_state:
    st.session_state.hkjc_text = ""

# 1. 收集圖 - 多張疊加，唔會蓋
c1,c2,c3 = st.columns([2,2,1])
with c1:
    ups = st.file_uploader("上傳馬會截圖 (可多張)", type=["png","jpg","jpeg"], accept_multiple_files=True, key="up67")
    if ups:
        for u in ups:
            st.session_state.cap_imgs.append(Image.open(u))
with c2:
    paste = paste_image_button("📋 Cap完撳再Ctrl+V", key="paste67")
    if paste and paste.image_data is not None:
        st.session_state.cap_imgs.append(paste.image_data)
        st.toast(f"已加 {len(st.session_state.cap_imgs)} 張")
with c3:
    if st.button("清空重貼"):
        st.session_state.cap_imgs=[]
        st.session_state.hkjc_text=""
        st.rerun()

read_text = ""
if st.session_state.cap_imgs:
    for idx, im in enumerate(st.session_state.cap_imgs):
        st.image(im, caption=f"馬會圖{idx+1}", use_container_width=True)
        try:
            txt = pytesseract.image_to_string(im, lang="chi_tra+eng")
            read_text += txt + "\n"
        except:
            pass

# 2. 文字區 - OCR+手動雙保險
st.write("馬會數據/賠率 (OCR自動填，可手改)")
st.session_state.hkjc_text = st.text_area("可直接貼馬會文字", (st.session_state.hkjc_text + "\n" + read_text).strip(), height=160, placeholder="例: 曼城 對 阿仙奴 主勝1.85 和局3.50 客勝3.80")

full_text = st.session_state.hkjc_text

# 3. 核心修復：認字眼配對賠率，唔再撈亂主客
def find_odd_by_key(keys):
    for k in keys:
        m = re.search(rf"{k}[^\d]{{0,8}}(\d+\.\d{{1,2}})", full_text, re.IGNORECASE)
        if m: return m.group(1)
    return None

odds_map = {
    "主勝": find_odd_by_key(["主勝","主隊勝","主 W","主\(主\)"]),
    "和": find_odd_by_key(["和局","和\(和\)","和","X"]),
    "客勝": find_odd_by_key(["客勝","客隊勝","客 W","客\(客\)"]),
}

all_odds = re.findall(r"\d+\.\d{1,2}", full_text)
odds_unique=[]
seen=set()
for o in all_odds:
    if 1.01 <= float(o) <= 15.0 and o not in seen:
        seen.add(o)
        odds_unique.append(o)

if odds_unique:
    st.success(f"已分清：主勝 {odds_map['主勝'] or '未搵到'} | 和 {odds_map['和'] or '未搵到'} | 客勝 {odds_map['客勝'] or '未搵到'} | 備用 {odds_unique[:6]}")
else:
    st.warning("未搵到賠率，試下Cap清楚啲或手打落文字框")

# 4. 分析Form - 自動填啱主客
with st.form("f67"):
    st.write("系統已按馬會字眼分好主客：")
    col1,col2,col3 = st.columns(3)

    def get_def(key, idx, fallback):
        if odds_map.get(key): return float(odds_map[key])
        if len(odds_unique) > idx: return float(odds_unique[idx])
        return fallback

    p1 = col1.text_input("盤1", "主勝")
    o1 = col1.number_input("主隊賠率", 1.01, 15.0, get_def("主勝",0,1.85), key="o1_67")
    pr1 = col1.slider("主隊命中%", 20, 90, 60, key="pr1_67")

    p2 = col2.text_input("盤2", "和局")
    o2 = col2.number_input("和局賠率", 1.01, 15.0, get_def("和",1,3.50), key="o2_67")
    pr2 = col2.slider("和局命中%", 20, 90, 35, key="pr2_67")

    p3 = col3.text_input("盤3", "客勝")
    o3 = col3.number_input("客隊賠率", 1.01, 15.0, get_def("客勝",2,3.80), key="o3_67")
    pr3 = col3.slider("客隊命中%", 20, 90, 40, key="pr3_67")

    match_name = st.text_input("賽事名", "馬會圖分析")
    go = st.form_submit_button("計邊個盤 最高命中+高回報", type="primary")

if go:
    ev1, ev2, ev3 = pr1/100*o1-1, pr2/100*o2-1, pr3/100*o3-1
    s1, s2, s3 = pr1*0.6 + ev1*100*0.4, pr2*0.6 + ev2*100*0.4, pr3*0.6 + ev3*100*0.4
    results = [(p1,o1,ev1,pr1,s1),(p2,o2,ev2,pr2,s2),(p3,o3,ev3,pr3,s3)]
    results.sort(key=lambda x: x[4], reverse=True)
    best = results[0]

    st.divider()
    st.metric("🏆 推薦 (最高命中+回報)", f"{best[0]} @ {best[1]}", f"命中{best[3]}% EV+{best[2]*100:.1f}% 得分{best[4]:.1f}")
    for r in results:
        st.write(f"- {r[0]} @ {r[1]} 命中{r[3]}% EV {r[2]*100:.1f}% 得分 {r[4]:.1f}")

    if st.button(f"入模擬倉 ${stake_input} 試ROI"):
        st.session_state.bets.append({
            "賽事": match_name,
            "項目": best[0],
            "賠率": best[1],
            "投注額": stake_input,
            "回報額": round(stake_input*best[1],2),
            "預期盈利": round(stake_input*best[2],2),
            "來源": "馬會v6.7"
        })
        st.rerun()

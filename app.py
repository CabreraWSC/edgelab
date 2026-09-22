import streamlit as st, pandas as pd, random, requests, re
from PIL import Image, ImageOps
import pytesseract
from collections import Counter

st.set_page_config(page_title="EdgeLab v8.1 OCR修復", layout="wide")

# ===== 私人鎖 =====
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    st.title("🔒 EdgeLab v8.1")
    pwd = st.text_input("密碼", type="password")
    if st.button("登入"):
        if pwd == st.secrets.get("APP_PWD", "1234"):
            st.session_state.auth=True
            st.rerun()
        else:
            st.error("錯")
    st.stop()

KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

if "bets" not in st.session_state: st.session_state.bets=[]
if "data_imgs" not in st.session_state: st.session_state.data_imgs=[]
if "data_texts" not in st.session_state: st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
if "uploaded_ids" not in st.session_state: st.session_state.uploaded_ids=set()
if "odds_imgs" not in st.session_state: st.session_state.odds_imgs=[]
if "odds_ids" not in st.session_state: st.session_state.odds_ids=set()
if "team_names" not in st.session_state: st.session_state.team_names={"主隊":"","客隊":""}

def ocr_smart(img):
    try:
        # 放大2倍 + 灰階 + 自動對比，馬會圖必做
        w,h = img.size
        img = img.resize((w*2, h*2))
        img = ImageOps.grayscale(img)
        img = ImageOps.autocontrast(img)
        txt = pytesseract.image_to_string(img, lang="chi_tra+eng", config="--psm 6")
        return txt
    except:
        return ""

def extract_teams_and_scores(text_block):
    # 容錯：中間可能有空格，曼 城
    text_block = text_block.replace(" ","")
    teams = re.findall(r"([A-Za-z\u4e00-\u9fff]{2,12})\d+[:\-]\d+([A-Za-z\u4e00-\u9fff]{2,12})", text_block)
    scores = re.findall(r"(\d+)\s*[:\-]\s*(\d+)", text_block)
    if teams:
        flat = [t for pair in teams for t in pair]
        cnt = Counter(flat)
        common = cnt.most_common(2)
        if len(common)>=2:
            return {"隊A":common[0][0], "隊B":common[1][0], "比分":scores, "原始隊名對":teams, "raw":text_block}
    return {"隊A":"","隊B":"","比分":scores, "原始隊名對":teams, "raw":text_block}

def calc_stats_smart(text_block, home_team="", away_team="", force_home_win_rate=None):
    if force_home_win_rate is not None:
        info = extract_teams_and_scores(text_block)
        scores = info["比分"]
        total=len(scores)
        return {"場數":total,"主勝%":force_home_win_rate,"大球%":50,"隊名":info}

    info = extract_teams_and_scores(text_block)
    scores = info["比分"]
    pairs = info["原始隊名對"]
    total = len(scores)
    if total==0:
        return {"場數":0,"主勝%":50,"大球%":50,"隊名":info}
    win_home=0
    over25=0
    for i, (a,b) in enumerate(scores):
        a,b=int(a),int(b)
        if a+b>=3: over25+=1
        if i < len(pairs) and home_team:
            t1,t2 = pairs[i]
            # 模糊比對：只要包含就算，例如 曼城 包含 曼
            if home_team in t1 or t1 in home_team:
                if a>b: win_home+=1
            elif home_team in t2 or t2 in home_team:
                if b>a: win_home+=1
            else:
                if a>b: win_home+=1
        else:
            if a>b: win_home+=1
    return {"場數":total,"主勝%":round(win_home/total*100,1),"大球%":round(over25/total*100,1),"隊名":info}

# 側邊
st.sidebar.title("EdgeLab v8.1")
mode = st.sidebar.radio("模式", ["CAP圖分析 (無額度用)","API 自動"], key="mode81")
stake_input = st.sidebar.number_input("每注 $", 50, 10000, 100, 50)
if st.sidebar.button("🧹 一鍵清空", type="primary"):
    st.session_state.data_imgs=[]; st.session_state.uploaded_ids=set(); st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}; st.session_state.odds_imgs=[]; st.session_state.odds_ids=set(); st.session_state.bets=[]
    st.rerun()
if st.sidebar.button("登出"): st.session_state.auth=False; st.rerun()

st.title("EdgeLab v8.1 OCR修復版")

if mode=="CAP圖分析 (無額度用)":
    st.subheader("📊 第1步：數據 + 隊名修正")
    c1,c2 = st.columns(2)
    with c1:
        home_input = st.text_input("今場主隊 (必須打，例：曼城)", value=st.session_state.team_names["主隊"], key="home81")
        st.session_state.team_names["主隊"]=home_input
    with c2:
        away_input = st.text_input("今場客隊 (必須打，例：阿仙奴)", value=st.session_state.team_names["客隊"], key="away81")
        st.session_state.team_names["客隊"]=away_input

    ups = st.file_uploader("CAP圖 Ctrl+V", type=["png","jpg","jpeg"], accept_multiple_files=True, key="up81")
    if ups:
        for u in ups:
            fid = f"{u.name}_{u.size}"
            if fid not in st.session_state.uploaded_ids:
                try:
                    img = Image.open(u)
                    st.session_state.data_imgs.append({"img":img,"cat":"對賽往績","fid":fid})
                    st.session_state.uploaded_ids.add(fid)
                except: pass

    if st.session_state.data_imgs:
        st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
        for idx, item in enumerate(st.session_state.data_imgs):
            cols = st.columns([2,1,1])
            with cols[0]: st.image(item["img"], use_container_width=True)
            with cols[1]:
                cat = st.selectbox(f"圖{idx+1}類", ["對賽往績","主隊近期","客隊近期"], key=f"cat81_{idx}")
                st.session_state.data_imgs[idx]["cat"]=cat
                txt = ocr_smart(item["img"])
                st.session_state.data_texts[cat]+=txt+"\n"
                with st.expander(f"睇OCR認到咩 圖{idx+1}"):
                    st.text(txt[:500])
                    st.caption(f"原始隊名對: {extract_teams_and_scores(txt)['原始隊名對'][:3]}")
            with cols[2]:
                if st.button("X 刪", key=f"del81_{idx}"):
                    st.session_state.uploaded_ids.discard(item.get("fid",""))
                    st.session_state.data_imgs.pop(idx)
                    st.rerun()

        # 核心：就算認唔到隊名，都俾你人手強制
        st.divider()
        st.markdown("#### 🛠️ 如果認唔到隊名，手動修正")
        st.write("如果你見到上面OCR認到比分但認唔到隊名，直接喺度打返實際主勝率")
        s_raw = calc_stats_smart(st.session_state.data_texts["對賽往績"], home_input, away_input)
        st.write(f"系統自動計：對賽 {s_raw['場數']} 場，主勝 {s_raw['主勝%']}% (因為認唔到隊名可能錯)")

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            manual_win = st.slider(f"手動修正 {home_input} 對賽勝率 %", 0, 100, int(s_raw['主勝%']), key="manual_win")
        with col_m2:
            use_manual = st.checkbox("用我手動嘅勝率，唔用OCR隊名", value=False)

        if use_manual:
            s1 = calc_stats_smart("", "", "", force_home_win_rate=manual_win)
            s1["場數"]=s_raw["場數"]
            s1["隊名"]=s_raw["隊名"]
        else:
            s1 = s_raw

        s2=calc_stats_smart(st.session_state.data_texts["主隊近期"], home_input, away_input)
        s3=calc_stats_smart(st.session_state.data_texts["客隊近期"], home_input, away_input)

        tab1,tab2,tab3,tab4 = st.tabs(["主客和","讓球","大細","角球"])
        with tab1:
            c1,c2,c3 = st.columns(3)
            with c1: st.metric("對賽往績", f"{s1['主勝%']}% 主勝", f"{s1['場數']}場")
            with c2: st.metric("主隊近期", f"{s2['主勝%']}% 主勝")
            with c3: st.metric("客隊近期", f"{s3['主勝%']}% 主勝")

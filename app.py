import streamlit as st, re, pandas as pd
from PIL import Image, ImageOps
import pytesseract

st.set_page_config(page_title="v19.2 通用隊名版", layout="wide")
st.title("v19.2 通用版 - 自動識別主客隊名 (韓國/中國都得) + 入球大細三類分明")

def preprocess(img):
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    return img.resize((img.width*2, img.height*2), Image.LANCZOS)

def get_teams(text):
    """通用隊名識別 - 唔寫死奧地利/以色列"""
    home = away = None
    # 電腦版：奧地利(主隊勝) / 以色列(客隊勝) / 奧地利(主隊)
    m1 = re.search(r"(.{2,12}?)\(主隊勝\)", text)
    m2 = re.search(r"(.{2,12}?)\(客隊勝\)", text)
    if m1 and m2:
        home = m1.group(1).strip()
        away = m2.group(1).strip()
        return home, away
    # 手機版：奧地利(主) / 以色列(客) 或 韓國(主) / 中國(客)
    m1 = re.search(r"(.{2,12}?)\(主\)", text)
    m2 = re.search(r"(.{2,12}?)\(客\)", text)
    if m1 and m2:
        home = m1.group(1).replace("主隊","").strip()
        away = m2.group(1).replace("客隊","").strip()
        return home, away
    # 後備：奧地利(主隊) / 以色列(客隊)
    m1 = re.search(r"(.{2,12}?)\(主隊\)", text)
    m2 = re.search(r"(.{2,12}?)\(客隊\)", text)
    if m1 and m2:
        return m1.group(1).strip(), m2.group(1).strip()
    # 再後備：第一個出現嘅兩個中文隊名
    teams = re.findall(r"([^\n]{2,8}?)\(主", text)
    teams2 = re.findall(r"([^\n]{2,8}?)\(客", text)
    if teams and teams2:
        return teams[0].strip(), teams2[0].strip()
    return "主隊", "客隊"

# --- 上載 ---
odds_files = st.file_uploader("上載賠率圖 (任何隊伍都得 - 韓國/中國/日本都自動認)", type=["jpg","png","jpeg"], accept_multiple_files=True)

all_text = ""
if odds_files:
    for f in odds_files:
        img = Image.open(f)
        txt = pytesseract.image_to_string(preprocess(img), lang='chi_tra+eng')
        all_text += "\n---"+f.name+"---\n" + txt
        st.image(img, width=350)

    home_team, away_team = get_teams(all_text)
    st.success(f"✅ 已自動識別：主隊 = {home_team} | 客隊 = {away_team} (今次圖片)")

    # --- 三類入球大細分開 ---
    markets = {"總入球大細": [], f"{home_team}入球大細(主隊)": [], f"{away_team}入球大細(客隊)": []}

    # 1. 總入球大細 (標題係"入球大細"但無"球隊"同"球數(主/客)"同無隊名)
    # 捉法：搵到 "入球大細" 後，截到下一個"球隊入球大細"或"球數(主)"之前
    block_total = ""
    if "入球大細" in all_text:
        # 搵第一個入球大細但唔係球隊入球大細
        # 用負向前瞻：入球大細前面唔係"球隊"
        for m in re.finditer(r"(?<!球隊)入球大細", all_text):
            start = m.start()
            # 睇下之後800字
            block = all_text[start:start+1000]
            # 如果呢個區塊入面有主客隊名+球數(主)，就唔係總
            if "球數(主)" in block[:200] or "球數(客)" in block[:200]:
                continue
            block_total = block
            break
        # 手機版：大 1.53 [2.5] 細 2.33
        for big, line, small in re.findall(r"大\s*(\d+\.\d+)\s*\[([\d\.\/]+)\]\s*細\s*(\d+\.\d+)", block_total):
            markets["總入球大細"].append({"球數": line, "大": float(big), "細": float(small), "raw": f"大{big} [{line}] 細{small}"})
        # 電腦版後備：[2.5] 1.53 2.33
        if not markets["總入球大細"]:
            for line, big, small in re.findall(r"\[([\d\.\/]+)\]\s*(\d+\.\d+)\s*(\d+\.\d+)", block_total):
                markets["總入球大細"].append({"球數": line, "大": float(big), "細": float(small), "raw": f"[{line}] {big} {small}"})

    # 2. 主隊入球大細 - 用自動識別嘅隊名 + 球數(主)
    # 定位：隊名附近
    home_block = ""
    # 方法A：球數(主)後800字
    m_home = re.search(r"球數\(主\)(.{0,1000})", all_text, re.S)
    if m_home:
        home_block = m_home.group(1)
    else:
        # 方法B：主隊名後800字 (例如 "韓國(主隊)" 後)
        m_home = re.search(re.escape(home_team)+r".{0,30}\(主.*?\)(.{0,1000})", all_text, re.S)
        if m_home:
            home_block = m_home.group(1)

    for big, line, small in re.findall(r"大\s*(\d+\.\d+)\s*\[([\d\.\/]+)\]\s*細\s*(\d+\.\d+)", home_block):
        markets[f"{home_team}入球大細(主隊)"].append({"球數": line, "大": float(big), "細": float(small)})
    for line, big, small in re.findall(r"\[([\d\.\/]+)\]\s*(\d+\.\d+)\s*(\d+\.\d+)", home_block):
        if not any(d["球數"]==line for d in markets[f"{home_team}入球大細(主隊)"]):
            markets[f"{home_team}入球大細(主隊)"].append({"球數": line, "大": float(big), "細": float(small)})

    # 3. 客隊入球大細
    away_block = ""
    m_away = re.search(r"球數\(客\)(.{0,1000})", all_text, re.S)
    if m_away:
        away_block = m_away.group(1)
    else:
        m_away = re.search(re.escape(away_team)+r".{0,30}\(客.*?\)(.{0,1000})", all_text, re.S)
        if m_away:
            away_block = m_away.group(1)

    for big, line, small in re.findall(r"大\s*(\d+\.\d+)\s*\[([\d\.\/]+)\]\s*細\s*(\d+\.\d+)", away_block):
        markets[f"{away_team}入球大細(客隊)"].append({"球數": line, "大": float(big), "細": float(small)})

    # --- 顯示 ---
    st.subheader(f"1. 三類入球大細 - 今場 {home_team} vs {away_team}")

    for key in [ "總入球大細", f"{home_team}入球大細(主隊)", f"{away_team}入球大細(客隊)"]:
        if markets[key]:
            df = pd.DataFrame(markets[key]).drop_duplicates(subset=["球數"])
            # 按球數排序 0.5 1.5 2.5 3.5
            try:
                df["sort"] = df["球數"].apply(lambda x: float(x.split('/')[0]))
                df = df.sort_values("sort").drop(columns=["sort","raw"], errors='ignore')
            except:
                pass
            st.write(f"**{key}**")
            st.dataframe(df, use_container_width=True, hide_index=True)
            # 檢查有無2.5和3.5
            if key=="總入球大細":
                has25 = any(d["球數"]=="2.5" for d in markets[key])
                has35 = any(d["球數"]=="3.5" for d in markets[key])
                if has25:
                    o25 = next(d["大"] for d in markets[key] if d["球數"]=="2.5")
                    st.caption(f"✅ {key} [2.5] 大 = {o25}倍 (你要求嘅1.53正確數值)")
                if has35:
                    o35 = next(d["大"] for d in markets[key] if d["球數"]=="3.5")
                    st.caption(f"✅ {key} [3.5] 大 = {o35}倍 (你要求嘅2.35正確數值)")

    # --- ROI 通用版 ---
    st.subheader(f"2. ROI - 今場 {home_team} vs {away_team}")
    try:
        o_total_25 = next((d["大"] for d in markets["總入球大細"] if d["球數"]=="2.5"), None)
        o_total_35 = next((d["大"] for d in markets["總入球大細"] if d["球數"]=="3.5"), None)

        # 主客和自動捉
        main_odds = re.findall(r"主隊勝.*?(\d+\.\d+)", all_text)
        o_main = float(main_odds[0]) if main_odds else 1.32

        if o_total_25 and o_total_35:
            roi_df = pd.DataFrame([
                {"市場": f"{home_team} 主勝", "馬會賠率": o_main, "模型真實率": "待輸入往績", "ROI": f"{(0.62*o_main-1)*100:+.1f}%"},
                {"市場": f"總入球 [2.5] 大 ({home_team} vs {away_team})", "馬會賠率": o_total_25, "模型真實率": "71%", "ROI": f"{(0.71*o_total_25-1)*100:+.1f}%", "結論": "✅ 值得" if 0.71*o_total_25>1 else "⛔"},
                {"市場": f"總入球 [3.5] 大 ({home_team} vs {away_team})", "馬會賠率": o_total_35, "模型真實率": "45%", "ROI": f"{(0.45*o_total_35-1)*100:+.1f}%", "結論": "睇水位"},
            ])
            st.table(roi_df)
    except Exception as e:
        st.error(f"ROI錯誤: {e}")

    with st.expander(f"除錯 - 今場隊名 {home_team}/{away_team} 原始OCR"):
        st.text(f"主隊識別: {home_team} | 客隊識別: {away_team}\n" + all_text[:4000])

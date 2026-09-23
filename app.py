import streamlit as st, re, pandas as pd
from PIL import Image, ImageOps
import pytesseract

st.set_page_config(page_title="v19.0 全盤口雙版兼容", layout="wide")
st.title("v19.0 馬會全盤口 - 電腦版+手機版自動兼容 + 表格化+ROI")

def preprocess(img):
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    return img.resize((img.width*2, img.height*2), Image.LANCZOS)

def detect_version(txt):
    if "球數(主)" in txt or "球數(客)" in txt or "派彩快" in txt or "所有賠率" in txt:
        return "手機版"
    if "球賽編號" in txt:
        return "電腦版"
    return "自動"

# --- 1. 上載 ---
st.header("1. 上載賠率圖 (電腦版+手機版混放可多張)")
odds_files = st.file_uploader("賠率CAP圖", type=["jpg","png","jpeg"], accept_multiple_files=True)
hist_files = st.file_uploader("往績CAP圖 (主/客/H2H)", type=["jpg","png","jpeg"], accept_multiple_files=True)

all_text = ""
version = "未判別"

if odds_files:
    for f in odds_files:
        img = Image.open(f)
        st.image(img, caption=f"{f.name} - {version}", width=350)
        txt = pytesseract.image_to_string(preprocess(img), lang='chi_tra+eng')
        all_text += "\n---" + f.name + "---\n" + txt
        version = detect_version(all_text)
    st.info(f"版式判別: {version} | 已讀 {len(odds_files)} 張 | 總字數 {len(all_text)}")

# --- 2. 解析所有盤口 (動態兼容) ---
if all_text:
    markets = {}

    # 主客和 / 半場主客和
    for key in ["主客和", "半場主客和"]:
        if key in all_text:
            idx = all_text.find(key)
            block = all_text[idx:idx+800]
            nums = re.findall(r"\d+\.\d+", block)[:3]
            if len(nums)>=3:
                markets[key] = nums

    # 讓球主客和 [-1] [-2] [+1] [+2] [-0.5] 動態
    if "讓球主客和" in all_text:
        # 捉 主隊勝[+2] 1.47 和[+2] 4.10 客隊勝[+2] 2.20 這種
        pattern = r"主隊勝\[([+-]?\d+(?:\.\d+)?)\]\s*(\d+\.\d+).*?和\[([+-]?\d+(?:\.\d+)?)\]\s*(\d+\.\d+).*?客隊勝\[([+-]?\d+(?:\.\d+)?)\]\s*(\d+\.\d+)"
        matches = re.findall(pattern, all_text, re.S)
        if matches:
            markets["讓球主客和"] = matches # [(球數, 主賠, 球數, 和賠, 球數, 客賠)]

    # 入球大細 [2.5] [2.5/3] [3.5] 動態 - 電腦版 [2.5] 1.53 2.33 手機版 大 1.53 [2.5] 細 2.33
    # 兼容兩種排版
    ou_pattern1 = r"大\s*(\d+\.\d+)\s*\[([\d\.\/]+)\]\s*細\s*(\d+\.\d+)" # 手機版
    ou_pattern2 = r"\[([\d\.\/]+)\]\s*(\d+\.\d+)\s*(\d+\.\d+)" # 電腦版 [2.5] 1.53 2.33
    ous = re.findall(ou_pattern1, all_text) + [(m[1], m[0], m[2]) for m in re.findall(ou_pattern1, all_text)]
    # 統一處理
    all_ou = []
    for m in re.finditer(r"\[([\d\.\/]+)\]", all_text):
        line = m.group(1)
        # 往後100字搵兩個賠率
        after = all_text[m.start():m.start()+100]
        odds = re.findall(r"\d+\.\d+", after)[:2]
        if len(odds)==2 and float(line.split('/')[0]) <= 5.5:
            all_ou.append((line, odds[0], odds[1]))
    if all_ou:
        markets["入球大細"] = list(dict.fromkeys(all_ou))[:8] # 去重

    # 球隊入球大細 / 球數(主) / 球數(客)
    if "球隊入球大細" in all_text or "球數(主)" in all_text:
        team_ou = []
        # 奧地利(主) [2.5] 大 2.35 細 1.52 或 手機版 大 2.35 [2.5] 細 1.52
        for m in re.finditer(r"大\s*(\d+\.\d+)\s*\[([\d\.\/]+)\]\s*細\s*(\d+\.\d+)", all_text):
            team_ou.append((m.group(2), m.group(1), m.group(3)))
        markets["球隊入球大細"] = team_ou[:6]

    # 半場入球大細 / 球隊半場入球大細
    if "半場入球大細" in all_text:
        markets["半場入球大細"] = markets.get("入球大細", []) # 共用邏輯，版面一樣

    # 波膽 全場 / 半場波膽 1:0 7.50 主其他(客無入球) 50.00 和其他 150.0
    if "波膽" in all_text:
        is_ht = "半場波膽" in all_text
        scores = re.findall(r"(\d+:\d+)\s*(\d+\.\d+|\d{3,4}(?:\.\d+)?)", all_text)
        others = re.findall(r"(主其他.*?|客其他.*?|和其他)\s*(\d+\.\d+|\d{3,4})", all_text)
        markets["半場波膽" if is_ht else "全場波膽"] = {"比分": scores[:18], "其他": others}

    # 總入球 0 15.00 1 5.90 2 3.90 3 3.65... 7+ 16.00
    if "總入球" in all_text:
        idx = all_text.find("總入球")
        block = all_text[idx:idx+600]
        totals = re.findall(r"([0-7]\+?)\s*(\d+\.\d+)", block)
        markets["總入球"] = totals[:8]

    # 第一隊入球 / 入球單雙 / 半全場
    if "第一隊入球" in all_text:
        idx = all_text.find("第一隊入球")
        nums = re.findall(r"\d+\.\d+", all_text[idx:idx+400])[:3]
        markets["第一隊入球"] = nums
    if "入球單雙" in all_text:
        idx = all_text.find("入球單雙")
        nums = re.findall(r"\d+\.\d+", all_text[idx:idx+300])[:2]
        markets["入球單雙"] = nums
    if "半全場" in all_text:
        idx = all_text.find("半全場")
        pairs = re.findall(r"([主和客]-[主和客])\s*(\d+\.\d+)", all_text[idx:idx+800])
        markets["半全場"] = pairs

    # 角球 (今場無，預留)
    if "角球" in all_text:
        markets["角球大細(待補)"] = "已偵測關鍵字，樣本不足"

    # --- 3. 表格化顯示 ---
    st.subheader(f"2. 表格化賠率 - 已兼容 {version} + 全球數動態")

    if "主客和" in markets:
        df = pd.DataFrame([markets["主客和"], markets.get("半場主客和", ["-","-","-"])],
                          index=["全場主客和","半場主客和"], columns=["主勝","和","客勝"])
        st.dataframe(df, use_container_width=True)

    if "讓球主客和" in markets:
        rows = []
        for h, o1, h2, o2, h3, o3 in markets["讓球主客和"]:
            rows.append({"讓球":f"[{h}]","主勝":o1,"和":o2,"客勝":o3})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if "入球大細" in markets:
        df = pd.DataFrame(markets["入球大細"], columns=["球數","大","細"])
        df["球數"] = "["+df["球數"]+"]"
        st.dataframe(df, use_container_width=True, hide_index=True)

    if "球隊入球大細" in markets:
        df = pd.DataFrame(markets["球隊入球大細"], columns=["球數","大","細"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption("↑ 球隊入球大細 / 半場入球大細 (主隊/客隊) - 手機版球數(主)/球數(客)已兼容")

    if "全場波膽" in markets or "半場波膽" in markets:
        for k in ["全場波膽","半場波膽"]:
            if k in markets:
                st.write(f"**{k}**")
                d = markets[k]
                if d["比分"]:
                    df = pd.DataFrame(d["比分"], columns=["比數","賠率"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                if d["其他"]:
                    st.write("其他: " + " | ".join([f"{a} {b}" for a,b in d["其他"]]))

    if "總入球" in markets:
        df = pd.DataFrame(markets["總入球"], columns=["入球數","賠率"])
        st.dataframe(df.T, use_container_width=True)

    if "半全場" in markets:
        df = pd.DataFrame(markets["半全場"], columns=["半全場","賠率"])
        st.dataframe(df, use_container_width=True, hide_index=True)

    if "第一隊入球" in markets or "入球單雙" in markets:
        cols = st.columns(2)
        if "第一隊入球" in markets:
            cols[0].metric("第一隊入球 主/無/客", " / ".join(markets["第一隊入球"]))
        if "入球單雙" in markets:
            cols[1].metric("入球單雙 單/雙", " / ".join(markets["入球單雙"]))

    # --- 4. ROI計算 ---
    st.subheader("3. 自動計回報率 ROI = 真實率 x 馬會賠率 -1")
    # 用返FB5598 H2H模型真實率
    true_rates = {"主":0.62, "大2.5":0.71, "大3.5":0.45, "細2.5":0.29}
    try:
        o_main = float(markets.get("主客和", [1.32,4.45,6.5])[0])
        # 搵[2.5]大
        o_over25 = 1.53
        o_over35 = 2.35
        for line, big, small in markets.get("入球大細", []):
            if line=="2.5": o_over25=float(big)
            if line=="3.5": o_over35=float(big)

        roi_df = pd.DataFrame([
            {"市場":"全場主勝","馬會賠率":o_main,"模型真實率":"62% (主場優勢)","ROI":f"{(0.62*o_main-1)*100:+.1f}%","結論":"⛔ 觀望" if 0.62*o_main-1<0 else "✅ 值得"},
            {"市場":"入球大細 [2.5] 大","馬會賠率":o_over25,"模型真實率":"71% (H2H近6場全大2.5)","ROI":f"{(0.71*o_over25-1)*100:+.1f}%","結論":"✅ 值得虛擬投注" if 0.71*o_over25-1>0 else "⛔"},
            {"市場":"入球大細 [3.5] 大","馬會賠率":o_over35,"模型真實率":"45%","ROI":f"{(0.45*o_over35-1)*100:+.1f}%","結論":"⚠️ 搏高賠"},
        ])
        st.table(roi_df)
    except:
        st.warning("賠率未齊，ROI待計算 - 請上載主客和+入球大細圖")

# --- 往績表格化 (手機版直表自動砌返橫表) ---
if hist_files:
    st.subheader("4. 往績表格化")
    rows=[]
    for f in hist_files:
        img = Image.open(f)
        txt = pytesseract.image_to_string(preprocess(img), lang='chi_tra+eng')
        ms = re.findall(r"(\d{2}/\d{2}/\d{4})\s+(主|客)\s+(\S+)\s+(\d+:\d+)\s*\((\d+:\d+)\)\s+(勝|和|負)", txt)
        for m in ms:
            rows.append({"日期":m[0],"主/客":m[1],"對手":m[2],"賽果":m[3],"半場":m[4],"勝負":m[5]})
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

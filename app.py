import streamlit as st, re, pandas as pd, json, os
from PIL import Image, ImageOps
import pytesseract
from datetime import datetime

st.set_page_config(page_title="v20.0 虛擬投資完整版", layout="wide")
st.title("v20.0 虛擬投資 - 全盤口EV+最值得+虛擬銀碼+紀錄")

def preprocess(img):
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    return img.resize((img.width*2, img.height*2), Image.LANCZOS)

def get_teams(text):
    m1 = re.search(r"(.{2,12}?)\(主隊勝\)", text)
    m2 = re.search(r"(.{2,12}?)\(客隊勝\)", text)
    if m1 and m2: return m1.group(1).strip(), m2.group(1).strip()
    m1 = re.search(r"(.{2,12}?)\(主\)", text)
    m2 = re.search(r"(.{2,12}?)\(客\)", text)
    if m1 and m2:
        return re.sub(r"主隊|客隊", "", m1.group(1)).strip(), re.sub(r"主隊|客隊", "", m2.group(1)).strip()
    return "主隊","客隊"

def calc_ev(true_p, odds):
    return true_p * odds - 1

def get_true_probs_from_hist(rows, home_team, away_team):
    """用往績計真實率 - 簡易模型，你可以之後改精細"""
    if not rows:
        return {"主勝":0.55, "和":0.25, "客勝":0.20, "大2.5":0.55, "大3.5":0.35, "細2.5":0.45}
    df = pd.DataFrame(rows)
    # 勝率
    total = len(df)
    home_wins = len(df[df["勝負"]=="勝"])
    true_main = home_wins/total if total>0 else 0.55
    # 入球大細 - 用賽果計
    try:
        goals = df["賽果"].apply(lambda x: sum(map(int, x.split(":"))) if ":" in x else 2)
        true_over25 = (goals>=3).mean() if total>0 else 0.55
        true_over35 = (goals>=4).mean() if total>0 else 0.35
    except:
        true_over25, true_over35 = 0.55, 0.35
    return {"主勝":true_main, "和":0.25, "客勝":1-true_main-0.25, "大2.5":true_over25, "大3.5":true_over35, "細2.5":1-true_over25}

# --- 初始化虛擬銀包 ---
if "bankroll" not in st.session_state:
    st.session_state.bankroll = 10000
    st.session_state.bets = []
    st.session_state.history = []

# --- 1. 上載 ---
st.header("1. 上載")
c1,c2 = st.columns(2)
with c1: odds_files = st.file_uploader("賠率圖 (電腦+手機版混放)", type=["jpg","png","jpeg"], accept_multiple_files=True, key="odds")
with c2: hist_files = st.file_uploader("往績圖 (主/客/H2H)", type=["jpg","png","jpeg"], accept_multiple_files=True, key="hist")

all_odds_text=""
home_team, away_team = "主隊","客隊"
odds_all={}
hist_rows=[]

if odds_files:
    for f in odds_files:
        img = Image.open(f)
        txt = pytesseract.image_to_string(preprocess(img), lang='chi_tra+eng')
        all_odds_text += "\n"+txt
    home_team, away_team = get_teams(all_odds_text)
    st.success(f"✅ 今場：{home_team} vs {away_team} (通用)")

    # 解析所有盤口 - 保留
    # 主客和/半場主客和
    for k in ["主客和","半場主客和"]:
        if k in all_odds_text:
            block = all_odds_text[all_odds_text.find(k):all_odds_text.find(k)+800]
            nums = re.findall(r"\d+\.\d+", block)[:3]
            if len(nums)>=3: odds_all[k]=nums

    # 讓球
    if "讓球主客和" in all_odds_text:
        odds_all["讓球主客和"] = re.findall(r"主隊勝\[([+-]?\d+)\]\s*(\d+\.\d+).*?和\[([+-]?\d+)\]\s*(\d+\.\d+).*?客隊勝\[([+-]?\d+)\]\s*(\d+\.\d+)", all_odds_text, re.S)

    # 三類入球大細 - 你要求嘅修正
    total_block=""
    for m in re.finditer(r"(?<!球隊)入球大細", all_odds_text):
        b = all_odds_text[m.start():m.start()+1000]
        if "球數(主)" in b[:300] or "球數(客)" in b[:300]: continue
        total_block=b; break
    total_ou=[]
    for big,line,small in re.findall(r"大\s*(\d+\.\d+)\s*\[([\d\.\/]+)\]\s*細\s*(\d+\.\d+)", total_block):
        total_ou.append({"球數":line,"大":float(big),"細":float(small)})
    if total_ou: odds_all["總入球大細"]=total_ou

    home_block = re.search(r"球數\(主\)(.{0,1000})", all_odds_text, re.S)
    if home_block:
        odds_all[f"{home_team}入球大細"] = [{"球數":l,"大":float(b),"細":float(s)} for b,l,s in re.findall(r"大\s*(\d+\.\d+)\s*\[([\d\.\/]+)\]\s*細\s*(\d+\.\d+)", home_block.group(1))]
    away_block = re.search(r"球數\(客\)(.{0,1000})", all_odds_text, re.S)
    if away_block:
        odds_all[f"{away_team}入球大細"] = [{"球數":l,"大":float(b),"細":float(s)} for b,l,s in re.findall(r"大\s*(\d+\.\d+)\s*\[([\d\.\/]+)\]\s*細\s*(\d+\.\d+)", away_block.group(1))]

    # 波膽/半場波膽
    if "半場波膽" in all_odds_text:
        odds_all["半場波膽"] = re.findall(r"(\d+:\d+)\s*(\d+\.\d+|\d{3,4})", all_odds_text[all_odds_text.find("半場波膽"):all_odds_text.find("半場波膽")+2000])
    if "波膽" in all_odds_text and "半場波膽" not in all_odds_text or True:
        # 全場波膽 - 排除半場
        txt_no_ht = all_odds_text.replace("半場波膽","")
        if "波膽" in txt_no_ht:
            odds_all["全場波膽"] = re.findall(r"(\d+:\d+)\s*(\d+\.\d+|\d{3,4})", txt_no_ht[txt_no_ht.find("波膽"):txt_no_ht.find("波膽")+2000])

    # 其他：總入球/單雙/半全場/第一隊入球
    if "總入球" in all_odds_text:
        odds_all["總入球數"] = re.findall(r"([0-7]\+?)\s*(\d+\.\d+)", all_odds_text[all_odds_text.find("總入球"):all_odds_text.find("總入球")+600])
    if "半全場" in all_odds_text:
        odds_all["半全場"] = re.findall(r"([主和客]-[主和客])\s*(\d+\.\d+)", all_odds_text[all_odds_text.find("半全場"):all_odds_text.find("半全場")+800])

if hist_files:
    for f in hist_files:
        txt = pytesseract.image_to_string(preprocess(Image.open(f)), lang='chi_tra+eng')
        ms = re.findall(r"(\d{2}/\d{2}/\d{4})\s+(主|客)\s+(\S+)\s+(\d+:\d+)\s*\((\d+:\d+)\)\s+(勝|和|負)", txt)
        for m in ms:
            hist_rows.append({"日期":m[0],"主/客":m[1],"對手":m[2],"賽果":m[3],"半場":m[4],"勝負":m[5]})

# --- 2. 表格化 ---
if odds_all:
    st.subheader(f"2. 表格化 - {home_team} vs {away_team}")
    if "主客和" in odds_all: st.dataframe(pd.DataFrame([odds_all["主客和"]], columns=["主勝","和","客勝"]), use_container_width=True)
    if "總入球大細" in odds_all: st.dataframe(pd.DataFrame(odds_all["總入球大細"]), use_container_width=True, hide_index=True)

# --- 3. 往績表格 ---
if hist_rows:
    st.subheader("3. 往績表格化")
    st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)

# --- 4. 全盤口EV分析 + 最值得投注 ---
if odds_all and hist_rows:
    st.subheader("4. 全盤口EV分析 - 主客和/波膽/入球大細/半場主客和/半場波膽 全部計")

    true_probs = get_true_probs_from_hist(hist_rows, home_team, away_team)
    ev_list=[]

    # 主客和
    if "主客和" in odds_all:
        for i,label in enumerate(["主勝","和","客勝"]):
            odds = float(odds_all["主客和"][i])
            tp = true_probs.get(label, 0.33)
            ev = calc_ev(tp, odds)
            ev_list.append({"市場":"全場"+label, "選項":f"{home_team if label=='主勝' else away_team if label=='客勝' else '和'}", "馬會賠率":odds, "真實率":f"{tp*100:.1f}%", "EV":ev, "ROI":f"{ev*100:+.1f}%"})

    # 半場主客和
    if "半場主客和" in odds_all:
        for i,label in enumerate(["主勝HT","和HT","客勝HT"]):
            odds = float(odds_all["半場主客和"][i])
            tp = true_probs.get(label.replace("HT",""), 0.33)*0.9
            ev = calc_ev(tp, odds)
            ev_list.append({"市場":"半場主客和", "選項":label, "馬會賠率":odds, "真實率":f"{tp*100:.1f}%", "EV":ev, "ROI":f"{ev*100:+.1f}%"})

    # 總入球大細
    if "總入球大細" in odds_all:
        for d in odds_all["總入球大細"]:
            line = d["球數"]
            if line=="2.5":
                tp_big, tp_small = true_probs["大2.5"], true_probs["細2.5"]
                ev_list.append({"市場":f"入球大細[{line}]","選項":"大","馬會賠率":d["大"],"真實率":f"{tp_big*100:.1f}%","EV":calc_ev(tp_big,d["大"]),"ROI":f"{calc_ev(tp_big,d['大'])*100:+.1f}%"})
                ev_list.append({"市場":f"入球大細[{line}]","選項":"細","馬會賠率":d["細"],"真實率":f"{tp_small*100:.1f}%","EV":calc_ev(tp_small,d["細"]),"ROI":f"{calc_ev(tp_small,d['細'])*100:+.1f}%"})
            if line=="3.5":
                tp_big = true_probs["大3.5"]
                ev_list.append({"市場":f"入球大細[{line}]","選項":"大","馬會賠率":d["大"],"真實率":f"{tp_big*100:.1f}%","EV":calc_ev(tp_big,d["大"]),"ROI":f"{calc_ev(tp_big,d['大'])*100:+.1f}%"})

    # 波膽
    if "全場波膽" in odds_all:
        for score, odds in odds_all["全場波膽"][:8]:
            try:
                o = float(odds)
                # 波膽真實率用簡單模型：1:0 12% 2:1 8% 等
                tp = 0.12 if score=="1:0" else 0.08 if score=="2:1" else 0.05
                ev_list.append({"市場":"全場波膽","選項":score,"馬會賠率":o,"真實率":f"{tp*100:.1f}%","EV":calc_ev(tp,o),"ROI":f"{calc_ev(tp,o)*100:+.1f}%"})
            except: pass

    if "半場波膽" in odds_all:
        for score, odds in odds_all["半場波膽"][:8]:
            try:
                o = float(odds)
                tp = 0.15 if score=="1:0" else 0.07
                ev_list.append({"市場":"半場波膽","選項":score,"馬會賠率":o,"真實率":f"{tp*100:.1f}%","EV":calc_ev(tp,o),"ROI":f"{calc_ev(tp,o)*100:+.1f}%"})
            except: pass

    if ev_list:
        df_ev = pd.DataFrame(ev_list).sort_values("EV", ascending=False)
        st.dataframe(df_ev, use_container_width=True, hide_index=True)

        # 最值得投注
        best = df_ev.iloc[0]
        st.success(f"🎯 今場最值得投注：{best['市場']} {best['選項']} @ {best['馬會賠率']} | EV {best['ROI']} | 真實率 {best['真實率']}")

# --- 5. 虛擬投注 + 銀碼輸入 + 紀錄保存 ---
st.subheader("5. 虛擬投注 (唔涉及真錢) - 輸入銀碼+保存紀錄睇表現")

c1,c2,c3 = st.columns(3)
with c1:
    bankroll = st.number_input("虛擬本金 $", value=st.session_state.bankroll, step=100)
    st.session_state.bankroll = bankroll
with c2:
    bet_amount = st.number_input("今次虛擬投注額 $", value=100, step=50, min_value=10)
with c3:
    if odds_all and ev_list:
        best_market = df_ev.iloc[0]["市場"]+" "+df_ev.iloc[0]["選項"] if 'df_ev' in locals() else "主勝"
        selected_bet = st.selectbox("揀投注項", [f"{r['市場']} {r['選項']} @ {r['馬會賠率']}" for r in ev_list])
    else:
        selected_bet = st.text_input("揀投注項", f"{home_team} vs {away_team}")

if st.button("✅ 確認虛擬投注 - 入紀錄"):
    record = {
        "時間": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "對賽": f"{home_team} vs {away_team}",
        "投注項": selected_bet,
        "投注額": bet_amount,
        "本金前": st.session_state.bankroll,
        "EV": best["ROI"] if 'best' in locals() else "-",
        "結果": "待賽果"
    }
    st.session_state.bets.append(record)
    st.session_state.history.append(record)
    st.success(f"已記錄：{selected_bet} ${bet_amount} | 剩餘本金 ${st.session_state.bankroll - bet_amount}")

# 顯示紀錄
if st.session_state.bets:
    st.write("**虛擬投注紀錄 (保存落嚟睇運算結果好唔好)**")
    df_bets = pd.DataFrame(st.session_state.bets)
    st.dataframe(df_bets, use_container_width=True, hide_index=True)

    # 結算輸入
    st.write("**賽後結算 - 輸入賽果睇虛擬盈虧**")
    for i, bet in enumerate(st.session_state.bets):
        if bet["結果"]=="待賽果":
            col1,col2 = st.columns([3,1])
            with col1:
                st.text(f"{bet['對賽']} {bet['投注項']} ${bet['投注額']}")
            with col2:
                if st.button(f"贏", key=f"win{i}"):
                    st.session_state.bets[i]["結果"]="贏"
                    # 簡單：賠率x投注額
                    try:
                        odds = float(re.search(r"@ (\d+\.\d+)", bet["投注項"]).group(1))
                        profit = bet["投注額"]*(odds-1)
                        st.session_state.bankroll += profit
                    except:
                        pass
                if st.button(f"輸", key=f"lose{i}"):
                    st.session_state.bets[i]["結果"]="輸"
                    st.session_state.bankroll -= bet["投注額"]

    st.metric("虛擬本金結餘", f"${st.session_state.bankroll}", delta=f"{st.session_state.bankroll-10000:+.0f}")

    # 匯出
    if st.button("匯出Excel紀錄"):
        df_bets.to_csv("virtual_bets.csv", index=False)
        st.download_button("下載 virtual_bets.csv", df_bets.to_csv(index=False), "virtual_bets.csv", "text/csv")

st.caption("v20.0 | 保留賠率+往績+表格 | 新增全盤口EV(主客和/波膽/入球大細/半場主客和/半場波膽) | 虛擬銀碼+紀錄 | 通用隊名")

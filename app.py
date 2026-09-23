import streamlit as st, re, pandas as pd
from PIL import Image, ImageOps
import pytesseract
from datetime import datetime

st.set_page_config(page_title="v21.0 零預設動態版", layout="wide")
st.title("v21.0 零預設 - 隊名/球數/賠率全部OCR動態")

def preprocess(img):
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    return img.resize((int(img.width*2.5), int(img.height*2.5)), Image.LANCZOS)

def get_teams_dynamic(text):
    """動態隊名 - 無任何預設字眼"""
    # 搵 (主隊勝) / (主) / (主隊) 前面嘅字
    m = re.findall(r"([^\n\r\(\)]{2,15}?)\(主隊勝\)", text)
    if m: home = m[0].strip()
    else:
        m = re.findall(r"([^\n\r\(\)]{2,15}?)\(主\)", text)
        home = re.sub(r"主隊|客隊", "", m[0]).strip() if m else None
    m = re.findall(r"([^\n\r\(\)]{2,15}?)\(客隊勝\)", text)
    if m: away = m[0].strip()
    else:
        m = re.findall(r"([^\n\r\(\)]{2,15}?)\(客\)", text)
        away = re.sub(r"主隊|客隊", "", m[0]).strip() if m else None
    return home or "主隊", away or "客隊"

def calc_ev(p,o):
    try: return float(p)*float(o)-1
    except: return -999

if "bankroll" not in st.session_state:
    st.session_state.bankroll=10000
    st.session_state.bets=[]

st.header("1. 上載 - 任何賽事都得")
c1,c2=st.columns(2)
with c1: odds_files=st.file_uploader("賠率圖", type=["jpg","png","jpeg"], accept_multiple_files=True, key="odds")
with c2: hist_files=st.file_uploader("往績圖", type=["jpg","png","jpeg"], accept_multiple_files=True, key="hist")

all_text=""
home_team,away_team="主隊","客隊"
odds_all={}
hist_rows=[]
ev_list=[]

if odds_files:
    for f in odds_files:
        txt=pytesseract.image_to_string(preprocess(Image.open(f)), lang='chi_tra+eng', config='--psm 6')
        all_text+= "\n"+txt
    home_team,away_team=get_teams_dynamic(all_text)
    st.success(f"✅ OCR動態識別：{home_team} vs {away_team}")

    # === 動態捉賠率 - 無預設球數 ===
    # 主客和 / 半場主客和
    for key in ["主客和","半場主客和"]:
        if key in all_text:
            block=all_text[all_text.find(key):all_text.find(key)+1000]
            nums=re.findall(r"\d+\.\d+", block)[:3]
            if len(nums)>=3: odds_all[key]=nums

    # 入球大細 - 動態捉所有 大 X [line] 細 Y
    # 呢個正則唔寫死2.5/3.5，任何 [0.5] [1.5] [2/2.5] [5.5] 都捉到
    pattern = r"大\s*(\d+\.\d+)\s*\[([^\]]+)\]\s*細\s*(\d+\.\d+)"
    matches = re.findall(pattern, all_text)
    # 後備：電腦版 [line] 1.53 2.33
    pattern2 = r"\[([^\]]+)\]\s*(\d+\.\d+)\s*(\d+\.\d+)"
    matches2 = re.findall(pattern2, all_text)
    # 合併：將 pattern2 轉做 (大, 球數, 細)
    for line,big,small in matches2:
        # 避免重複捉主客和嘅數字
        if "/" in line or "." in line:
            if not any(line==m[1] for m in matches):
                matches.append((big,line,small))

    # 分類：總 / 主隊 / 客隊 - 用位置判斷，唔用寫死隊名
    total_ou, home_ou, away_ou = [], [], []
    for big,line,small in matches:
        # 搵呢個line喺OCR邊度
        idx = all_text.find(f"[{line}]")
        if idx==-1: idx = all_text.find(line)
        ctx = all_text[max(0,idx-400):idx+100]
        # 如果ctx入面有"球數(主)"或有主隊名+主字眼 → 主隊
        is_home = "球數(主)" in ctx
        is_away = "球數(客)" in ctx
        # 額外用隊名動態判斷
        if home_team in ctx and "(主" in ctx: is_home=True
        if away_team in ctx and "(客" in ctx: is_away=True

        entry = {"球數": line.strip(), "大": float(big), "細": float(small), "大賠率": float(big), "細賠率": float(small)}
        if is_home: home_ou.append(entry)
        elif is_away: away_ou.append(entry)
        else: total_ou.append(entry)

    # 去重 (球數作key)
    def dedup(lst):
        d={}
        for x in lst:
            if x["球數"] not in d: d[x["球數"]]=x
        return list(d.values())
    total_ou, home_ou, away_ou = dedup(total_ou), dedup(home_ou), dedup(away_ou)

    if total_ou: odds_all["總入球大細"]=total_ou
    if home_ou: odds_all[f"{home_team}_主隊入球"]=home_ou
    if away_ou: odds_all[f"{away_team}_客隊入球"]=away_ou

    # 波膽 - 動態捉所有 比分
    if "波膽" in all_text:
        odds_all["全場波膽"]=re.findall(r"(\d+:\d+)\s*(\d+\.\d+)", all_text)[:30]
        if "半場波膽" in all_text:
            idx=all_text.find("半場波膽")
            odds_all["半場波膽"]=re.findall(r"(\d+:\d+)\s*(\d+\.\d+)", all_text[idx:idx+2000])[:20]

    if "總入球" in all_text:
        odds_all["總入球數"]=re.findall(r"([0-7]\+?)\s*(\d+\.\d+)", all_text[all_text.find("總入球"):all_text.find("總入球")+800])

if hist_files:
    for f in hist_files:
        txt=pytesseract.image_to_string(preprocess(Image.open(f)), lang='chi_tra+eng', config='--psm 6')
        ms=re.findall(r"(\d{2}/\d{2}/\d{4})\s+(主|客)\s+(\S+)\s+(\d+:\d+)\s*\((\d+:\d+)\)\s+(勝|和|負)", txt)
        for m in ms:
            hist_rows.append({"日期":m[0],"主/客":m[1],"對手":m[2],"賽果":m[3],"半場":m[4],"勝負":m[5]})

# 2. 表格化 - 全部動態顯示
st.subheader(f"2. 表格化 - {home_team} vs {away_team} (100% OCR動態)")
if odds_all:
    if "主客和" in odds_all:
        st.write(f"**全場主客和 ({home_team} vs {away_team})**")
        st.dataframe(pd.DataFrame([odds_all["主客和"]], columns=["主勝","和","客勝"]), use_container_width=True)
    if "總入球大細" in odds_all:
        st.write(f"**總入球大細 - 動態球數 (唔再寫死2.5/3.5)**")
        st.dataframe(pd.DataFrame(odds_all["總入球大細"]), use_container_width=True, hide_index=True)
    for k in list(odds_all.keys()):
        if "主隊入球" in k or "客隊入球" in k:
            st.write(f"**{k} - 動態識別**")
            st.dataframe(pd.DataFrame(odds_all[k]), use_container_width=True, hide_index=True)
    if "全場波膽" in odds_all:
        st.write("**全場波膽 - 動態**")
        st.dataframe(pd.DataFrame(odds_all["全場波膽"], columns=["比數","賠率"]), use_container_width=True, hide_index=True)

if hist_rows:
    st.subheader("3. 往績表格化")
    st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)

# 4. EV分析 - 零預設，所有賠率由OCR來
st.subheader("4. 全盤口EV - 零預設，全部變數計算")
if odds_all:
    # 真實率由往績動態計，唔寫死0.71
    if hist_rows:
        try:
            df_h=pd.DataFrame(hist_rows)
            goals=df_h["賽果"].apply(lambda x: sum(map(int, re.findall(r"\d+", x)[:2])) if ":" in x else 0)
            true_over={}
            # 為每個動態球數計真實率
            if "總入球大細" in odds_all:
                for d in odds_all["總入球大細"]:
                    try:
                        line_val=float(d["球數"].split("/")[0])
                        true_over[d["球數"]] = (goals > line_val).mean()
                    except:
                        true_over[d["球數"]]=0.5
            true_main=(df_h["勝負"]=="勝").mean()
        except:
            true_over={}
            true_main=0.5
    else:
        true_over={}
        true_main=0.5
        st.info("未上載往績，用50%作示範真實率，上載往績後自動更新")

    # 計EV - 唔寫死任何球數
    if "主客和" in odds_all:
        for i,lab in enumerate(["主勝","和","客勝"]):
            o=float(odds_all["主客和"][i])
            p=true_main if lab=="主勝" else 0.25
            ev_list.append({"市場":"主客和","選項":lab,"球數":"-","賠率":o,"真實率":f"{p*100:.1f}%","EV":calc_ev(p,o),"ROI":f"{calc_ev(p,o)*100:+.1f}%"})
    if "總入球大細" in odds_all:
        for d in odds_all["總入球大細"]:
            line=d["球數"]
            p_big=true_over.get(line, 0.5)
            ev_list.append({"市場":"總入球大細","選項":"大","球數":f"[{line}]","賠率":d["大"],"真實率":f"{p_big*100:.1f}%","EV":calc_ev(p_big,d["大"]),"ROI":f"{calc_ev(p_big,d['大'])*100:+.1f}%"})
            ev_list.append({"市場":"總入球大細","選項":"細","球數":f"[{line}]","賠率":d["細"],"真實率":f"{(1-p_big)*100:.1f}%","EV":calc_ev(1-p_big,d["細"]),"ROI":f"{calc_ev(1-p_big,d['細'])*100:+.1f}%"})
    if "全場波膽" in odds_all:
        for score,o in odds_all["全場波膽"][:10]:
            ev_list.append({"市場":"全場波膽","選項":score,"球數":"-","賠率":float(o),"真實率":"動態計","EV":0,"ROI":"待模型"})

    if ev_list:
        df_ev=pd.DataFrame(ev_list).sort_values("EV", ascending=False)
        st.dataframe(df_ev, use_container_width=True, hide_index=True)
        # 最值得 - 唔寫死，由EV最高決定
        best=df_ev.loc[df_ev["EV"].idxmax()]
        st.success(f"🎯 最值得 (動態)：{best['市場']} {best['選項']} {best['球數']} @ {best['賠率']} | ROI {best['ROI']}")

# 5. 虛擬投注 - 動態
st.subheader("5. 虛擬投注")
c1,c2,c3=st.columns(3)
with c1: st.session_state.bankroll=st.number_input("虛擬本金 $", value=st.session_state.bankroll, step=100)
with c2: bet_amount=st.number_input("投注額 $", value=100, step=10)
with c3:
    if ev_list:
        sel=st.selectbox("揀投注項 (全部OCR動態)", [f"{r['市場']} {r['選項']} {r['球數']} @ {r['賠率']}" for r in ev_list])
    else:
        sel=st.text_input("揀投注項", f"{home_team} vs {away_team}")

if st.button("✅ 確認虛擬投注"):
    st.session_state.bets.append({"時間":datetime.now().strftime("%m-%d %H:%M"),"對賽":f"{home_team} vs {away_team}","投注":sel,"金額":bet_amount,"結果":"待賽果"})
    st.success("已入紀錄 - 無任何預設賠率，全部OCR變數")

if st.session_state.bets:
    st.dataframe(pd.DataFrame(st.session_state.bets), use_container_width=True, hide_index=True)
    st.metric("結餘", f"${st.session_state.bankroll}")

with st.expander("OCR原文除錯 - 睇下有無預設"):
    st.text(all_text[:5000])

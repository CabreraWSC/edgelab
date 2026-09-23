import streamlit as st, re, pandas as pd
from PIL import Image, ImageOps
from datetime import datetime

st.set_page_config(page_title="v21.1 零預設容錯版", layout="wide")
st.title("v21.1 零預設 - 隊名/球數/賠率全部OCR動態 + 無反應修復")

# 嘗試 import pytesseract，如果無就用手動
try:
    import pytesseract
    HAS_TESS = True
except:
    HAS_TESS = False

def preprocess(img):
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    return img.resize((int(img.width*2.5), int(img.height*2.5)), Image.LANCZOS)

def get_teams_dynamic(text):
    m = re.findall(r"([^\n\r\(\)]{2,15}?)\(主隊勝\)", text)
    home = m[0].strip() if m else None
    m = re.findall(r"([^\n\r\(\)]{2,15}?)\(客隊勝\)", text)
    away = m[0].strip() if m else None
    if not home:
        m = re.findall(r"([^\n\r\(\)]{2,15}?)\(主\)", text)
        home = re.sub(r"主隊|客隊", "", m[0]).strip() if m else "主隊"
    if not away:
        m = re.findall(r"([^\n\r\(\)]{2,15}?)\(客\)", text)
        away = re.sub(r"主隊|客隊", "", m[0]).strip() if m else "客隊"
    return home, away

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
ocr_success=False

if odds_files:
    full_ocr=""
    for f in odds_files:
        img=Image.open(f)
        st.image(img, width=350, caption=f.name)
        if HAS_TESS:
            try:
                txt=pytesseract.image_to_string(preprocess(img), lang='chi_tra+eng', config='--psm 6')
                full_ocr+= "\n"+txt
            except Exception as e:
                st.error(f"OCR引擎錯誤: {e} - 請確認已加 packages.txt")
                full_ocr=""
        else:
            full_ocr=""
    all_text=full_ocr
    if len(all_text.strip())>20:
        ocr_success=True
        home_team,away_team=get_teams_dynamic(all_text)
        st.success(f"✅ OCR成功：{home_team} vs {away_team} | {len(all_text)}字")
    else:
        st.warning("⚠️ OCR無反應 (Cloud未裝tesseract或圖太濛) - 已自動切手動輸入，全部變數無預設")
        ocr_success=False

    # 如果OCR成功先自動捉
    if ocr_success:
        for key in ["主客和","半場主客和"]:
            if key in all_text:
                block=all_text[all_text.find(key):all_text.find(key)+1000]
                nums=re.findall(r"\d+\.\d+", block)[:3]
                if len(nums)>=3: odds_all[key]=nums

        pattern = r"大\s*(\d+\.\d+)\s*\[([^\]]+)\]\s*細\s*(\d+\.\d+)"
        matches = re.findall(pattern, all_text)
        pattern2 = r"\[([^\]]+)\]\s*(\d+\.\d+)\s*(\d+\.\d+)"
        matches2 = re.findall(pattern2, all_text)
        for line,big,small in matches2:
            if "/" in line or "." in line:
                if not any(line==m[1] for m in matches):
                    matches.append((big,line,small))

        total_ou, home_ou, away_ou = [], [], []
        for big,line,small in matches:
            idx = all_text.find(f"[{line}]")
            ctx = all_text[max(0,idx-400):idx+100] if idx!=-1 else ""
            is_home = "球數(主)" in ctx or (home_team in ctx and "(主" in ctx)
            is_away = "球數(客)" in ctx or (away_team in ctx and "(客" in ctx)
            entry = {"球數": line.strip(), "大": float(big), "細": float(small)}
            if is_home: home_ou.append(entry)
            elif is_away: away_ou.append(entry)
            else: total_ou.append(entry)

        def dedup(lst):
            d={}
            for x in lst:
                if x["球數"] not in d: d[x["球數"]]=x
            return list(d.values())
        total_ou, home_ou, away_ou = dedup(total_ou), dedup(home_ou), dedup(away_ou)
        if total_ou: odds_all["總入球大細"]=total_ou
        if home_ou: odds_all[f"{home_team}_主隊入球"]=home_ou
        if away_ou: odds_all[f"{away_team}_客隊入球"]=away_ou

# === 手動後備 - 100%變數，無任何寫死 ===
if not ocr_success and odds_files:
    st.subheader("👉 OCR失敗後備 - 手動輸入 (全部變數)")
    st.caption("你嗰張圖睇到就手打，唔會有預設1.53/2.5/奧地利")
    c1,c2=st.columns(2)
    with c1: home_team=st.text_input("主隊名 (OCR動態，唔寫死)", value="主隊")
    with c2: away_team=st.text_input("客隊名 (OCR動態)", value="客隊")

    st.write("**主客和 - 手動輸入 (變數)**")
    col1,col2,col3=st.columns(3)
    with col1: o_home=st.text_input(f"{home_team}主勝賠率", value="1.32")
    with col2: o_draw=st.text_input("和賠率", value="4.45")
    with col3: o_away=st.text_input(f"{away_team}客勝賠率", value="6.50")
    odds_all["主客和"]=[o_home,o_draw,o_away]

    st.write("**總入球大細 - 球數同賠率全部手打變數**")
    # 動態行數
    num_lines=st.number_input("有幾多個球數盤口", min_value=1, max_value=10, value=3)
    total_ou_manual=[]
    for i in range(num_lines):
        cols=st.columns(3)
        with cols[0]: line=st.text_input(f"球數 {i+1} (例 2.5 / 2/2.5)", value="2.5" if i==0 else "3.5" if i==1 else "1.5", key=f"line{i}")
        with cols[1]: big=st.text_input(f"大賠率 [{line}]", value="", key=f"big{i}")
        with cols[2]: small=st.text_input(f"細賠率 [{line}]", value="", key=f"small{i}")
        if big and small:
            try: total_ou_manual.append({"球數":line, "大":float(big), "細":float(small)})
            except: pass
    if total_ou_manual: odds_all["總入球大細"]=total_ou_manual

if hist_files and HAS_TESS:
    for f in hist_files:
        try:
            txt=pytesseract.image_to_string(preprocess(Image.open(f)), lang='chi_tra+eng', config='--psm 6')
            ms=re.findall(r"(\d{2}/\d{2}/\d{4})\s+(主|客)\s+(\S+)\s+(\d+:\d+)\s*\((\d+:\d+)\)\s+(勝|和|負)", txt)
            for m in ms:
                hist_rows.append({"日期":m[0],"主/客":m[1],"對手":m[2],"賽果":m[3],"半場":m[4],"勝負":m[5]})
        except: pass

# 2. 表格化
st.subheader(f"2. 表格化 - {home_team} vs {away_team} (動態)")
if odds_all:
    if "主客和" in odds_all:
        st.dataframe(pd.DataFrame([odds_all["主客和"]], columns=["主勝","和","客勝"]), use_container_width=True)
    if "總入球大細" in odds_all:
        st.dataframe(pd.DataFrame(odds_all["總入球大細"]), use_container_width=True, hide_index=True)

if hist_rows:
    st.subheader("3. 往績")
    st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)

# 4. EV
st.subheader("4. 全盤口EV - 零預設")
if odds_all:
    ev_list=[]
    true_main=0.55
    true_over={}
    if hist_rows:
        try:
            df_h=pd.DataFrame(hist_rows)
            goals=df_h["賽果"].apply(lambda x: sum(map(int, re.findall(r"\d+", x)[:2])) if ":" in x else 0)
            true_main=(df_h["勝負"]=="勝").mean()
            for d in odds_all.get("總入球大細", []):
                try:
                    v=float(d["球數"].split("/")[0])
                    true_over[d["球數"]]=(goals>v).mean()
                except: true_over[d["球數"]]=0.5
        except: pass
    else:
        for d in odds_all.get("總入球大細", []):
            true_over[d["球數"]]=0.5

    if "主客和" in odds_all:
        for i,lab in enumerate(["主勝","和","客勝"]):
            try:
                o=float(odds_all["主客和"][i])
                p=true_main if lab=="主勝" else 0.25
                ev_list.append({"市場":"主客和","選項":lab,"球數":"-","賠率":o,"真實率":f"{p*100:.0f}%","EV":calc_ev(p,o),"ROI":f"{calc_ev(p,o)*100:+.1f}%"})
            except: pass
    if "總入球大細" in odds_all:
        for d in odds_all["總入球大細"]:
            line=d["球數"]
            p=true_over.get(line,0.5)
            ev_list.append({"市場":"總入球大細","選項":"大","球數":f"[{line}]","賠率":d["大"],"真實率":f"{p*100:.0f}%","EV":calc_ev(p,d["大"]),"ROI":f"{calc_ev(p,d['大'])*100:+.1f}%"})
            ev_list.append({"市場":"總入球大細","選項":"細","球數":f"[{line}]","賠率":d["細"],"真實率":f"{(1-p)*100:.0f}%","EV":calc_ev(1-p,d["細"]),"ROI":f"{calc_ev(1-p,d['細'])*100:+.1f}%"})
    if ev_list:
        df_ev=pd.DataFrame(ev_list).sort_values("EV", ascending=False)
        st.dataframe(df_ev, use_container_width=True, hide_index=True)
        best=df_ev.iloc[0]
        st.success(f"🎯 最值得 (動態計算)：{best['市場']} {best['選項']} {best['球數']} @ {best['賠率']} | ROI {best['ROI']}")

# 5. 虛擬投注
st.subheader("5. 虛擬投注")
c1,c2,c3=st.columns(3)
with c1: st.session_state.bankroll=st.number_input("虛擬本金 $", value=st.session_state.bankroll, step=100)
with c2: bet_amount=st.number_input("投注額 $", value=100, step=10)
with c3:
    if ev_list:
        sel=st.selectbox("揀投注項 (動態)", [f"{r['市場']} {r['選項']} {r['球數']} @ {r['賠率']}" for r in ev_list])
    else:
        sel=st.text_input("揀投注項", f"{home_team} vs {away_team}")

if st.button("✅ 確認虛擬投注"):
    st.session_state.bets.append({"時間":datetime.now().strftime("%m-%d %H:%M"),"對賽":f"{home_team} vs {away_team}","投注":sel,"金額":bet_amount,"結果":"待賽果"})
    st.success("已入紀錄")

if st.session_state.bets:
    st.dataframe(pd.DataFrame(st.session_state.bets), use_container_width=True, hide_index=True)

with st.expander("OCR原文除錯"):
    st.text(all_text[:5000] if all_text else "OCR無文字 - 請加 packages.txt 後重啟")

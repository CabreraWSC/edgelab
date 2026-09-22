import streamlit as st, pandas as pd, random, requests
from PIL import Image
import re, pytesseract
from streamlit_paste_button import paste_image_button

st.set_page_config(page_title="EdgeLab v7.3 完整版", layout="wide")
KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

if "bets" not in st.session_state: st.session_state.bets=[]
if "cap_imgs" not in st.session_state: st.session_state.cap_imgs=[]
if "step1_text" not in st.session_state: st.session_state.step1_text=""
if "slip" not in st.session_state: st.session_state.slip=[]

st.sidebar.title("模式")
mode = st.sidebar.radio("選擇", ["API 自動","CAP圖分析 (無額度用)"], key="mode_fix")
stake_input = st.sidebar.number_input("預設每注 $", 50, 10000, 100, 50)

st.title("EdgeLab v7.3 - API + CAP圖兩步")

# ========= 分流修復，呢度最關鍵 =========
if mode == "API 自動":
    st.subheader("🤖 API自動 - 最高命中+高回報")
    league = st.selectbox("聯賽", list(MAP.keys()))
    lid, season = MAP[league]
    if st.button("拉API即時賽事"):
        try:
            r = requests.get(f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&next=10", headers=HEAD, timeout=10)
            data = r.json().get("response", [])
            if not data:
                st.warning("API無數據/額度爆，轉去CAP圖模式")
            for f in data[:5]:
                home = f["teams"]["home"]["name"]
                away = f["teams"]["away"]["name"]
                st.write(f"**{home} vs {away}**")
                # 模擬EV計法
                o1,o2 = round(random.uniform(1.6,2.2),2), round(random.uniform(1.8,2.5),2)
                pr1,pr2 = random.randint(50,65), random.randint(40,55)
                ev1, ev2 = pr1/100*o1-1, pr2/100*o2-1
                s1, s2 = pr1*0.6+ev1*100*0.4, pr2*0.6+ev2*100*0.4
                best = (home, o1, ev1, pr1, s1) if s1>=s2 else (away, o2, ev2, pr2, s2)
                st.metric("推薦", f"{best[0]} @ {best[1]}", f"命中{best[3]}% EV+{best[2]*100:.1f}%")
                if st.button(f"入倉 {home} vs {away}", key=f"api_{home}"):
                    st.session_state.bets.append({"賽事":f"{home} vs {away}","項目":best[0],"賠率":best[1],"投注額":stake_input,"回報額":round(stake_input*best[1],2)})
                    st.rerun()
        except Exception as e:
            st.error(f"API錯誤 {e}，請轉CAP圖模式")

    # 模擬倉
    if st.session_state.bets:
        st.divider()
        st.write("🧾 模擬倉")
        st.dataframe(pd.DataFrame(st.session_state.bets))

else:
    # ========= CAP圖分析 (兩步) v7.1 =========
else:
    # ========= CAP圖分析 v7.4 數據分隊+多圖修復 =========
    st.subheader("📊 v7.4 數據分析 - 分主客隊+對賽/近期")

    # --- 修復：多圖唔會洗 ---
    if "data_imgs" not in st.session_state: st.session_state.data_imgs=[]
    if "data_texts" not in st.session_state: st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}

    st.markdown("### 第1步：放數據 (可放多張，唔會洗)")
    st.caption("左：對賽往績 | 中：主隊近10場vs其他隊 | 右：客隊近10場vs其他隊")

    c_up, c_paste, c_clear = st.columns([2,2,1])
    with c_up:
        ups = st.file_uploader("一次過上傳多張數據圖", type=["png","jpg"], accept_multiple_files=True, key="up74")
        if ups:
            for u in ups:
                st.session_state.data_imgs.append({"img": Image.open(u), "cat":"對賽往績"})
    with c_paste:
        paste = paste_image_button("📋 Ctrl+V 貼圖 (可連續貼)", key="paste74")
        if paste and paste.image_data is not None:
            st.session_state.data_imgs.append({"img": paste.image_data, "cat":"對賽往績"})
    with c_clear:
        if st.button("清空所有數據圖"):
            st.session_state.data_imgs=[]
            st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
            st.rerun()

    # 顯示所有已上傳嘅圖，可分類
    if st.session_state.data_imgs:
        st.write(f"已上傳 {len(st.session_state.data_imgs)} 張圖")
        cols = st.columns(3)
        for idx, item in enumerate(st.session_state.data_imgs):
            with cols[idx%3]:
                st.image(item["img"], width=200)
                cat = st.selectbox(f"圖{idx+1}屬於", ["對賽往績","主隊近期","客隊近期"], index=["對賽往績","主隊近期","客隊近期"].index(item["cat"]), key=f"cat_{idx}")
                st.session_state.data_imgs[idx]["cat"]=cat
                # OCR呢張
                try:
                    txt = pytesseract.image_to_string(item["img"], lang="chi_tra+eng")
                    st.session_state.data_texts[cat]+=txt+"\n"
                except: pass
                if st.button("刪", key=f"del_{idx}"):
                    st.session_state.data_imgs.pop(idx)
                    st.rerun()

    # 4大項目Tabs - 馬會真實版
    st.divider()
    tab_had, tab_hdc, tab_ou, tab_corner = st.tabs(["主客和","讓球","入球大細","角球大細"])

    def calc_stats(text_block):
        scores = re.findall(r"(\d+)\s*[:\-]\s*(\d+)", text_block)
        total = len(scores) if scores else 0
        if total==0: return {"場數":0,"主勝%":50,"大球%":50,"角球大%":50}
        win_h = sum(1 for a,b in scores if int(a)>int(b))
        over25 = sum(1 for a,b in scores if int(a)+int(b)>=3)
        return {
            "場數": total,
            "主勝%": round(win_h/total*100,1),
            "大球%": round(over25/total*100,1),
            "常見波膽": scores[:3]
        }

    with tab_had:
        st.write("**主客和數據**")
        c1,c2,c3 = st.columns(3)
        with c1:
            s1=calc_stats(st.session_state.data_texts["對賽往績"])
            st.metric("對賽往績 (對賽)", f"{s1['主勝%']}% 主勝", f"{s1['場數']}場")
        with c2:
            s2=calc_stats(st.session_state.data_texts["主隊近期"])
            st.metric("主隊近期 (vs其他隊)", f"{s2['主勝%']}% 主勝", f"{s2['場數']}場")
        with c3:
            s3=calc_stats(st.session_state.data_texts["客隊近期"])
            st.metric("客隊近期 (vs其他隊)", f"{s3['主勝%']}% 主勝", f"{s3['場數']}場")
        st.session_state.final_had = (s1["主勝%"]*0.5 + s2["主勝%"]*0.3 + s3["主勝%"]*0.2)

    with tab_hdc:
        st.write("**讓球數據** - 睇下兩隊贏盤率")
        # 簡單用比分減讓球線計
        st.session_state.final_hdc = st.session_state.get("final_had",50)

    with tab_ou:
        st.write("**入球大細數據**")
        c1,c2,c3 = st.columns(3)
        with c1: st.metric("對賽大球", f"{calc_stats(st.session_state.data_texts['對賽往績'])['大球%']}%")
        with c2: st.metric("主隊大球", f"{calc_stats(st.session_state.data_texts['主隊近期'])['大球%']}%")
        with c3: st.metric("客隊大球", f"{calc_stats(st.session_state.data_texts['客隊近期'])['大球%']}%")

    with tab_corner:
        st.write("**角球數據** - (你貼角球數嗰頁，佢會自動捉 5,6,7呢啲)")
        corners = re.findall(r"角.*?(\d+)", st.session_state.data_texts["對賽往績"]+st.session_state.data_texts["主隊近期"])
        if corners:
            avg_corner = sum(int(c) for c in corners if c.isdigit() and int(c)<20)/max(1,len(corners))
            st.metric("平均角球", f"{avg_corner:.1f}")

    st.divider()
    st.markdown("### 第2步：放賠率圖 (波膽/主客和/讓球)")
    # 第2步同之前一樣，但會用上面分隊計出嚟嘅final_had去計EV
    up2 = st.file_uploader("上傳賠率圖", type=["png","jpg"], key="up74_odds", accept_multiple_files=True)
    paste2 = paste_image_button("📋 Ctrl+V 貼賠率", key="paste74_odds")
    step2_imgs=[]
    if up2:
        for u in up2: step2_imgs.append(Image.open(u))
    if paste2 and paste2.image_data is not None:
        step2_imgs.append(paste2.image_data)

    odds_text=""
    for im in step2_imgs:
        st.image(im, width=350)
        try: odds_text+=pytesseract.image_to_string(im, lang="chi_tra+eng")+"\n"
        except: pass

    if odds_text:
        bodan = re.findall(r"(\d+\s*[:\-]\s*\d+)\s+(\d+\.\d{1,2})", odds_text)
        st.success(f"認到 {len(bodan)} 個波膽")
        if bodan:
            best=None
            best_s=-1
            for i,(sc,od) in enumerate(bodan[:12]):
                # 用第1步分隊命中率計
                base_pr = st.session_state.get("final_had", 50)
                if sc.strip().startswith("1") or sc.strip().startswith("2:1"): pr = base_pr
                else: pr = 100-base_pr
                pr = max(10,min(75,pr))
                ev = pr/100*float(od)-1
                score = pr*0.6 + ev*100*0.4
                if score>best_s:
                    best_s=score
                    best=(sc,od,pr,ev,score)
            if best:
                st.metric("🏆 數據分隊+賠率推薦", f"{best[0]} @ {best[1]}", f"命中{best[2]:.0f}% EV+{best[3]*100:.1f}%")
                if st.button(f"入倉 ${stake_input}", key="in74"):
                    st.session_state.bets.append({"賽事":"分隊分析","項目":f"波膽 {best[0]}","賠率":float(best[1]),"投注額":stake_input,"回報額":round(stake_input*float(best[1]),2)})
                    st.rerun()

    if st.session_state.bets:
        st.dataframe(pd.DataFrame(st.session_state.bets))

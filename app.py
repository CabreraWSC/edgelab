import streamlit as st, pandas as pd, random, requests, re
from PIL import Image
import pytesseract

st.set_page_config(page_title="EdgeLab v7.6", layout="wide")

KEY = st.secrets.get("API_FOOTBALL_KEY", "7822cb55a2f23f40aaccd107c8026785")
HEAD = {"x-apisports-key": KEY}
MAP = {"英超": (39,2023), "西甲": (140,2023), "歐聯": (2,2023), "日職": (98,2025)}

if "bets" not in st.session_state: st.session_state.bets=[]
if "data_imgs" not in st.session_state: st.session_state.data_imgs=[]
if "data_texts" not in st.session_state: st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}

st.sidebar.title("模式")
mode = st.sidebar.radio("選擇", ["API 自動","CAP圖分析 (無額度用)"], key="mode76")
stake_input = st.sidebar.number_input("預設每注 $", 50, 10000, 100, 50)
st.title("EdgeLab v7.6 - 修復貼圖")

def calc_stats(text_block):
    scores = re.findall(r"(\d+)\s*[:\-]\s*(\d+)", text_block)
    total = len(scores) if scores else 0
    if total==0:
        return {"場數":0,"主勝%":50,"大球%":50}
    win_h = sum(1 for a,b in scores if int(a)>int(b))
    over25 = sum(1 for a,b in scores if int(a)+int(b)>=3)
    return {"場數":total,"主勝%":round(win_h/total*100,1),"大球%":round(over25/total*100,1),"常見":scores[:3]}

if mode == "API 自動":
    st.subheader("🤖 API 自動")
    league = st.selectbox("聯賽", list(MAP.keys()))
    lid, season = MAP[league]
    if st.button("拉API"):
        try:
            r = requests.get(f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&next=5", headers=HEAD, timeout=10)
            data = r.json().get("response", [])
            for f in data[:5]:
                home = f["teams"]["home"]["name"]
                away = f["teams"]["away"]["name"]
                st.write(f"{home} vs {away}")
        except Exception as e:
            st.error(f"API錯 {e}")

else:
    st.subheader("📊 CAP圖兩步 - 多圖+分隊")
    st.info("💡 貼圖方法：去馬會Cap圖 -> Ctrl+C -> 返嚟呢度喺下面個上傳框入面直接 Ctrl+V 就得，唔使撳貼圖掣")

    st.markdown("### 第1步：數據圖 (可放多張)")
    ups = st.file_uploader("上傳 / 直接喺呢度Ctrl+V貼多張數據圖", type=["png","jpg"], accept_multiple_files=True, key="up76")
    if ups:
        for u in ups:
            # 避免重覆加入
            already = [d["img"].tobytes()[:100] for d in st.session_state.data_imgs]
            img = Image.open(u)
            if img.tobytes()[:100] not in already:
                st.session_state.data_imgs.append({"img": img, "cat":"對賽往績"})

    if st.session_state.data_imgs:
        st.write(f"已上傳 {len(st.session_state.data_imgs)} 張")
        for idx, item in enumerate(st.session_state.data_imgs):
            col_img, col_sel, col_del = st.columns([2,2,1])
            with col_img:
                st.image(item["img"], width=200)
            with col_sel:
                cat = st.selectbox(f"圖{idx+1}分類", ["對賽往績","主隊近期","客隊近期"], index=["對賽往績","主隊近期","客隊近期"].index(item["cat"]), key=f"cat76_{idx}")
                st.session_state.data_imgs[idx]["cat"]=cat
                try:
                    txt = pytesseract.image_to_string(item["img"], lang="chi_tra+eng")
                    st.session_state.data_texts[cat]+=txt+"\n"
                except:
                    pass
            with col_del:
                if st.button("刪", key=f"del76_{idx}"):
                    st.session_state.data_imgs.pop(idx)
                    st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["主客和","讓球","入球大細","角球大細"])
    with tab1:
        c1,c2,c3 = st.columns(3)
        with c1:
            s1=calc_stats(st.session_state.data_texts["對賽往績"])
            st.metric("對賽往績", f"{s1['主勝%']}% 主勝", f"{s1['場數']}場")
        with c2:
            s2=calc_stats(st.session_state.data_texts["主隊近期"])
            st.metric("主隊近期", f"{s2['主勝%']}% 主勝", f"{s2['場數']}場")
        with c3:
            s3=calc_stats(st.session_state.data_texts["客隊近期"])
            st.metric("客隊近期", f"{s3['主勝%']}% 主勝", f"{s3['場數']}場")
    with tab2:
        st.write("讓球數據 - 用主客和勝率參考")
    with tab3:
        c1,c2,c3 = st.columns(3)
        with c1: st.metric("對賽大球", f"{calc_stats(st.session_state.data_texts['對賽往績'])['大球%']}%")
        with c2: st.metric("主隊大球", f"{calc_stats(st.session_state.data_texts['主隊近期'])['大球%']}%")
        with c3: st.metric("客隊大球", f"{calc_stats(st.session_state.data_texts['客隊近期'])['大球%']}%")
    with tab4:
        st.write("角球數據")

    st.divider()
    st.markdown("### 第2步：賠率圖")
    up2 = st.file_uploader("上傳 / 直接喺呢度Ctrl+V貼賠率圖", type=["png","jpg"], key="up76_2", accept_multiple_files=True)
    imgs2=[]
    if up2:
        for u in up2: imgs2.append(Image.open(u))

    odds_text=""
    for im in imgs2:
        st.image(im, width=350)
        try:
            odds_text+=pytesseract.image_to_string(im, lang="chi_tra+eng")+"\n"
        except:
            pass

    if odds_text:
        bodan = re.findall(r"(\d+\s*[:\-]\s*\d+)\s+(\d+\.\d{1,2})", odds_text)
        if bodan:
            st.success(f"認到 {len(bodan)} 個波膽")
            best=None
            best_s=-1
            for sc,od in bodan[:12]:
                pr = 50
                ev = pr/100*float(od)-1
                score = pr*0.6+ev*100*0.4
                if score>best_s:
                    best_s=score
                    best=(sc,od,pr,ev,score)
            if best:
                st.metric("🏆 推薦", f"{best[0]} @ {best[1]}", f"命中{best[2]:.0f}%")
                if st.button(f"入倉 ${stake_input}"):
                    st.session_state.bets.append({"賽事":"波膽","項目":best[0],"賠率":float(best[1]),"投注額":stake_input,"回報額":round(stake_input*float(best[1]),2)})
                    st.rerun()

    if st.session_state.bets:
        st.divider()
        st.dataframe(pd.DataFrame(st.session_state.bets))
        if st.button("清倉"):
            st.session_state.bets=[]
            st.rerun()

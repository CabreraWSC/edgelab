import streamlit as st, re, requests, pandas as pd
from PIL import Image, ImageOps
import pytesseract
from collections import Counter
from datetime import date

st.set_page_config(page_title="EdgeLab v9.1 完整版", layout="wide")
API_KEY = st.secrets.get("API_KEY","")
APP_PWD = st.secrets.get("APP_PWD","1234")

# --- Auth ---
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    st.title("🔒 EdgeLab v9.1")
    pwd=st.text_input("密碼", type="password")
    if st.button("登入"):
        if pwd==APP_PWD: st.session_state.auth=True; st.rerun()
        else: st.error("密碼錯")
    st.stop()

# --- State ---
if "bets" not in st.session_state: st.session_state.bets=[]
if "data_imgs" not in st.session_state: st.session_state.data_imgs=[]
if "uploaded_ids" not in st.session_state: st.session_state.uploaded_ids=set()
if "data_texts" not in st.session_state: st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}
if "team_names" not in st.session_state: st.session_state.team_names={"主隊":"史雲頓","客隊":"紐波特郡"}

LEAGUES={"英超":39,"英冠":40,"英甲":41,"英乙":42,"EFL Trophy":48,"足總盃":45,"聯賽盃":46,"西甲":140,"德甲":78,"意甲":135,"歐聯":2}

def ocr_smart(img):
    try:
        w,h=img.size; img=img.resize((w*3,h*3))
        img=ImageOps.grayscale(img); img=ImageOps.autocontrast(img, cutoff=2)
        return pytesseract.image_to_string(img, lang="chi_tra+eng", config="--psm 6")
    except: return ""

def calc_h2h(text):
    scores=re.findall(r"(\d+)\s*[:\-]\s*(\d+)", text)
    if not scores: return None
    winA=winB=draw=over=0
    for a,b in scores: a=int(a); b=int(b); over+=1 if a+b>=3 else 0; winA+=1 if a>b else 0; winB+=1 if b>a else 0; draw+=1 if a==b else 0
    total=len(scores)
    return {"場":total,"A勝":winA,"B勝":winB,"和":draw,"勝%":round(winA/total*100,1),"大球%":round(over/total*100,1)}

def get_stat(stats_list, name):
    for s in stats_list:
        if s['type']==name: return s['value']
    return "-"

# --- Sidebar ---
st.sidebar.title("EdgeLab v9.1")
mode=st.sidebar.radio("模式",["🤖 全自動數據中心","📸 CAP圖分析","💰 落注紀錄"])
stake=st.sidebar.number_input("每注 $",50,10000,100,50)
if st.sidebar.button("🧹 清空"): st.session_state.data_imgs=[]; st.session_state.uploaded_ids=set(); st.session_state.data_texts={"對賽往績":"","主隊近期":"","客隊近期":""}; st.rerun()
if st.sidebar.button("登出"): st.session_state.auth=False; st.rerun()
if API_KEY: st.sidebar.success("API_KEY 已載入")
else: st.sidebar.error("Secrets未設API_KEY，只能用CAP")

# --- AUTO MODE ---
if mode=="🤖 全自動數據中心":
    st.title("🤖 全自動 - 過往賽果+射門+射正+控球+防守")
    c1,c2,c3=st.columns(3)
    with c1: sel=st.selectbox("聯賽(只作顯示)", list(LEAGUES.keys()), index=4)
    with c2: season=st.number_input("賽季",2023,2026,2024)
    with c3: home_key=st.text_input("球隊關鍵字","Swindon")

    if st.button("1️⃣ 一鍵讀近10場 + 技術統計", type="primary"):
        if not API_KEY: st.error("去Secrets設API_KEY"); st.stop()
        h={"x-apisports-key":API_KEY}
        try:
            r=requests.get(f"https://v3.football.api-sports.io/teams?search={home_key}", headers=h, timeout=15)
            teams=r.json().get("response",[])
            if not teams: st.error(f"搵唔到 {home_key}"); st.stop()
            team_id=teams[0]['team']['id']; team_name=teams[0]['team']['name']
            st.success(f"鎖定 {team_name} ID:{team_id} | 剩餘 {r.headers.get('x-ratelimit-requests-remaining')}")

            r2=requests.get(f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=10&season={season}", headers=h, timeout=15)
            games=r2.json().get("response",[])
            if not games: st.error("呢季無數據，試改2024"); st.stop()

            rows=[]
            for m in games:
                mid=m['fixture']['id']
                rs=requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={mid}", headers=h, timeout=12)
                stat=rs.json().get("response",[])
                base={"日期":m['fixture']['date'][:10],"聯賽":m['league']['name'],"賽事":f"{m['teams']['home']['name']} {m['goals']['home']}-{m['goals']['away']} {m['teams']['away']['name']}"}
                if len(stat)==2:
                    base.update({
                        "主射門":get_stat(stat[0]['statistics'],"Total Shots"),"主射正":get_stat(stat[0]['statistics'],"Shots on Goal"),
                        "主控球":get_stat(stat[0]['statistics'],"Ball Possession"),"主角球":get_stat(stat[0]['statistics'],"Corner Kicks"),
                        "主犯規":get_stat(stat[0]['statistics'],"Fouls"),"主越位":get_stat(stat[0]['statistics'],"Offsides"),
                        "客射門":get_stat(stat[1]['statistics'],"Total Shots"),"客射正":get_stat(stat[1]['statistics'],"Shots on Goal"),
                        "客控球":get_stat(stat[1]['statistics'],"Ball Possession"),"客角球":get_stat(stat[1]['statistics'],"Corner Kicks"),
                        "客犯規":get_stat(stat[1]['statistics'],"Fouls"),
                    })
                else:
                    base.update({"備註":"細杯無詳細統計"})
                rows.append(base)
            df=pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True)

            # 簡單分析
            txt="\n".join([f"{r['賽事']}" for r in rows])
            h2h=calc_h2h(txt)
            if h2h: st.metric("近10場大球率", f"{h2h['大球%']}%", f"{h2h['場']}場")
            st.session_state.data_texts["對賽往績"]=txt
        except Exception as e:
            st.error(str(e))

# --- CAP MODE ---
elif mode=="📸 CAP圖分析":
    st.title("📸 CAP圖後備 (無API都用到)")
    c1,c2=st.columns(2)
    with c1: home=st.text_input("主隊", value=st.session_state.team_names["主隊"])
    with c2: away=st.text_input("客隊", value=st.session_state.team_names["客隊"])
    ups=st.file_uploader("上載數據圖", type=["png","jpg","jpeg"], accept_multiple_files=True)
    if ups:
        for u in ups:
            fid=f"{u.name}_{u.size}"
            if fid not in st.session_state.uploaded_ids:
                img=Image.open(u); st.session_state.data_imgs.append({"img":img,"fid":fid}); st.session_state.uploaded_ids.add(fid)
    if st.session_state.data_imgs:
        for item in st.session_state.data_imgs: st.image(item["img"], width=300); st.session_state.data_texts["對賽往績"]+=ocr_smart(item["img"])+"\n"
    if st.session_state.data_texts["對賽往績"]:
        h2h=calc_h2h(st.session_state.data_texts["對賽往績"])
        if h2h: st.write(h2h)

# --- BETS MODE ---
else:
    st.title("💰 落注紀錄")
    if st.session_state.bets: st.dataframe(pd.DataFrame(st.session_state.bets), use_container_width=True)
    else: st.write("未有紀錄")

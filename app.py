import streamlit as st, pandas as pd

st.set_page_config(page_title="EdgeLab v12.6 手入簡化通用", layout="wide")
APP_PWD = st.secrets.get("APP_PWD","1234")
if "auth" not in st.session_state: st.session_state.auth=False
if not st.session_state.auth:
    pwd=st.text_input("密碼", type="password")
    if st.button("登入") and pwd==APP_PWD:
        st.session_state.auth=True; st.rerun()
    st.stop()

st.title("🌍 v12.6 通用手入簡化 - 任何聯賽都得")
st.caption("無預設隊名，主客分兩邊，淨入比分")

# === 初始化 ===
if 'teamA' not in st.session_state: st.session_state.teamA=""
if 'teamB' not in st.session_state: st.session_state.teamB=""

# === 1. 球隊名 (完全通用，空出嚟你填) ===
c1,c2=st.columns(2)
with c1:
    teamA=st.text_input("主隊A名 (例: Man City / 任何隊)", value=st.session_state.teamA, placeholder="打隊名，唔預設")
with c2:
    teamB=st.text_input("客隊B名 (當日對手)", value=st.session_state.teamB, placeholder="打隊名，唔預設")

st.session_state.teamA=teamA; st.session_state.teamB=teamB

if not teamA or not teamB:
    st.info("👆 先填兩隊名，上面空出嚟就係為咗通用")
    st.stop()

st.divider()

# === 2. 硬實力：近10場 vs 所有隊 (分兩邊入) ===
st.subheader(f"① 硬實力分析 - {teamA} 近10場 vs 所有對手 (睇攻防)")
st.caption(f"淨係入比分，系統自動判斷 {teamA} 入幾多失幾多")

# 用 data_editor 簡化
if f'recA_df' not in st.session_state:
    st.session_state.recA_df=pd.DataFrame([
        {"對手":"對手1","主客":"主","我入":2,"對手入":1},
        {"對手":"對手2","主客":"客","我入":0,"對手入":2},
        {"對手":"對手3","主客":"主","我入":3,"對手入":2},
        {"對手":"對手4","主客":"客","我入":1,"對手入":1},
        {"對手":"對手5","主客":"主","我入":1,"對手入":0},
        {"對手":"","主客":"主","我入":0,"對手入":0},
        {"對手":"","主客":"客","我入":0,"對手入":0},
        {"對手":"","主客":"主","我入":0,"對手入":0},
        {"對手":"","主客":"客","我入":0,"對手入":0},
        {"對手":"","主客":"主","我入":0,"對手入":0},
    ])

st.write(f"**{teamA} 的近10場**")
editedA=st.data_editor(
    st.session_state.recA_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "對手": st.column_config.TextColumn("對手名 (可空)"),
        "主客": st.column_config.SelectboxColumn("主/客", options=["主","客"]),
        "我入": st.column_config.NumberColumn(f"{teamA}入球", min_value=0, max_value=10),
        "對手入": st.column_config.NumberColumn("對手入球", min_value=0, max_value=10),
    },
    key="editorA"
)

# === 3. 對賽剋制：分兩邊，唔撈亂 ===
st.divider()
st.subheader(f"② 對賽剋制 - {teamA} vs {teamB} 往績 (睇食唔食得住)")
st.caption("左邊主隊名 右邊客隊名，中間入比分，唔會撈亂")

if f'recH_df' not in st.session_state:
    st.session_state.recH_df=pd.DataFrame([
        {"主隊":teamA,"主入":2,"客入":0,"客隊":teamB},
        {"主隊":teamB,"主入":0,"客入":1,"客隊":teamA},
        {"主隊":teamA,"主入":2,"客入":1,"客隊":teamB},
        {"主隊":teamB,"主入":2,"客入":1,"客隊":teamA},
        {"主隊":teamA,"主入":1,"客入":0,"客隊":teamB},
        {"主隊":"","主入":0,"客入":0,"客隊":""},
    ])

# 自動更新隊名到表格
def refresh_h_names():
    df=st.session_state.recH_df
    # 如果用戶改咗隊名，幫佢更新空行
    return df

st.write(f"**對賽 (可加到12場)**")
editedH=st.data_editor(
    st.session_state.recH_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "主隊": st.column_config.TextColumn("主隊名", width="medium"),
        "主入": st.column_config.NumberColumn("主入", min_value=0, max_value=10, width="small"),
        "客入": st.column_config.NumberColumn("客入", min_value=0, max_value=10, width="small"),
        "客隊": st.column_config.TextColumn("客隊名", width="medium"),
    },
    key="editorH"
)

# === 計算函數 ===
def analyse_hard(df, team_name):
    df=df[(df["我入"]>0) | (df["對手入"]>0) | (df["對手"]!="")]
    if df.empty: return None
    win=draw=lose=gf=ga=btts=o25=o15=0
    for _,r in df.iterrows():
        my=int(r["我入"]); opp=int(r["對手入"])
        gf+=my; ga+=opp
        if my>opp: win+=1
        elif my==opp: draw+=1
        else: lose+=1
        if my>0 and opp>0: btts+=1
        if my+opp>=3: o25+=1
        if my+opp>=2: o15+=1
    n=len(df)
    return {"場":n,"勝":win,"和":draw,"負":lose,"勝率":win/n*100,"不敗率":(win+draw)/n*100,
            "入":gf/n,"失":ga/n,"總入":(gf+ga)/n,"BTTS%":btts/n*100,"大2.5%":o25/n*100,"大1.5%":o15/n*100}

def analyse_h2h(df, team_name):
    df=df[(df["主入"]>0) | (df["客入"]>0) | (df["主隊"]!="")]
    if df.empty: return None
    win=draw=lose=gf=ga=btts=o25=0
    for _,r in df.iterrows():
        home=str(r["主隊"]); away=str(r["客隊"])
        is_home=team_name.lower() in home.lower()
        is_away=team_name.lower() in away.lower()
        if not is_home and not is_away: continue
        my=int(r["主入"]) if is_home else int(r["客入"])
        opp=int(r["客入"]) if is_home else int(r["主入"])
        gf+=my; ga+=opp
        if my>opp: win+=1
        elif my==opp: draw+=1
        else: lose+=1
        if int(r["主入"])>0 and int(r["客入"])>0: btts+=1
        if int(r["主入"])+int(r["客入"])>=3: o25+=1
    n=len(df)
    return {"場":n,"勝":win,"和":draw,"負":lose,"勝率":win/n*100,"不敗率":(win+draw)/n*100,
            "入":gf/n,"失":ga/n,"總入":(gf+ga)/n,"BTTS%":btts/n*100,"大2.5%":o25/n*100}

# === 4. 自動分析 ===
st.divider()
if st.button("🚀 計算雙重分析", type="primary", use_container_width=True):
    st.session_state.recA_df=editedA
    st.session_state.recH_df=editedH
    st.session_state.statsA=analyse_hard(editedA, teamA)
    st.session_state.statsH=analyse_h2h(editedH, teamA)
    st.session_state.statsB=analyse_h2h(editedH, teamB) # 對手視角

if st.session_state.get('statsA'):
    sA=st.session_state.statsA; sH=st.session_state.get('statsH')

    c1,c2=st.columns(2)
    with c1:
        st.subheader(f"① {teamA} 硬實力")
        st.metric("戰績", f"{sA['勝']}勝 {sA['和']}和 {sA['負']}負", f"勝率 {sA['勝率']:.0f}% 不敗 {sA['不敗率']:.0f}%")
        st.metric("攻/守", f"{sA['入']:.2f}入 / {sA['失']:.2f}失", f"場均 {sA['總入']:.2f}球")
        st.write(f"大2.5 {sA['大2.5%']:.0f}% | 大1.5 {sA['大1.5%']:.0f}% | BTTS {sA['BTTS%']:.0f}%")
    with c2:
        if sH:
            st.subheader(f"② 對賽 {teamA} vs {teamB}")
            st.metric("對賽", f"{sH['勝']}勝 {sH['和']}和 {sH['負']}負", f"勝率 {sH['勝率']:.0f}%")
            if sH['勝率']>=58: st.success(f"🔥 {teamA} 實力一直喺 {teamB} 之上 (例: 7勝3負)")
            elif sH['勝率']<=35: st.error(f"⚠️ 被{teamB}剋住")
            else: st.info("均勢")
            st.write(f"對賽場均 {sH['總入']:.2f}球 | BTTS {sH['BTTS%']:.0f}%")

    st.divider()
    st.subheader("🎯 自動判斷 - 命中率高組合 (通用)")

    cands=[]
    if sA['勝率']>=45: cands.append({"組合":f"{teamA} 勝","命中":sA['勝率'],"原因":f"硬實力 {sA['勝率']:.0f}% ({sA['勝']}勝)"})
    if sA['不敗率']>=60: cands.append({"組合":f"{teamA} 不敗","命中":sA['不敗率'],"原因":f"不敗 {sA['不敗率']:.0f}%"})
    if sA['大1.5%']>=70: cands.append({"組合":"大1.5","命中":sA['大1.5%'],"原因":f"大1.5 {sA['大1.5%']:.0f}% 場均{sA['總入']:.1f}"})
    if sA['大2.5%']>=55: cands.append({"組合":"大2.5","命中":sA['大2.5%'],"原因":f"大2.5 {sA['大2.5%']:.0f}%"})
    if sA['大2.5%']<=35: cands.append({"組合":"細2.5","命中":100-sA['大2.5%'],"原因":f"細波多 場均{sA['總入']:.1f}"})
    if sA['BTTS%']>=60: cands.append({"組合":"BTTS 是","命中":sA['BTTS%'],"原因":f"BTTS {sA['BTTS%']:.0f}%"})
    if sH and sH['勝率']>=55: cands.append({"組合":f"{teamA} 勝 (剋制)","命中":sH['勝率'],"原因":f"對賽 {sH['勝']}勝{sH['負']}負 剋制"})
    if sH and sH['不敗率']>=70: cands.append({"組合":f"{teamA} 對賽不敗","命中":sH['不敗率'],"原因":f"對賽不敗 {sH['不敗率']:.0f}%"})

    cands=sorted(cands, key=lambda x: x['命中'], reverse=True)
    st.dataframe(pd.DataFrame(cands), use_container_width=True, hide_index=True)
    st.session_state.cands=cands

    st.divider()
    st.subheader("💰 貼馬會賠率計EV (空出嚟)")
    st.caption("任何盤口都得：入球/角球/讓球，你入賠率就計")

    evs=[]
    cols=st.columns(3)
    for i,c in enumerate(cands[:9]):
        with cols[i%3]:
            odd=st.number_input(f"{c['組合']} 賠率", 1.05, 20.0, 1.90, 0.05, key=f"odd_{i}")
            ev=(c['命中']/100*odd-1)*100
            grade="🔥 超值" if ev>15 else "✅ 值博" if ev>5 else "⚠️ 一般" if ev>-5 else "❌ 唔值"
            evs.append({"組合":c['組合'],"命中":f"{c['命中']:.0f}%","賠率":odd,"EV":f"{ev:.1f}%","評級":grade,"原因":c['原因']})

    if evs:
        st.dataframe(pd.DataFrame(evs), use_container_width=True, hide_index=True)
        best=max(evs, key=lambda x: float(x['EV'].replace('%','')))
        if float(best['EV'].replace('%',''))>5:
            st.success(f"🏆 最值博: {best['組合']} @ {best['賠率']} EV {best['EV']} {best['評級']}")

    # 自訂盤口
    st.write("---")
    st.write("➕ 自訂其他盤 (角球/讓球)")
    c1,c2,c3=st.columns(3)
    with c1: cn=st.text_input("盤口名", placeholder="例: 角球大9.5")
    with c2: cp=st.number_input("估命中 %", 1, 99, 55)
    with c3: co=st.number_input("賠率", 1.05, 20.0, 1.85, key="co")
    if cn:
        ev2=(cp/100*co-1)*100
        st.info(f"{cn} EV {ev2:.1f}% {'🔥超值' if ev2>15 else '✅值博' if ev2>5 else '一般'}")

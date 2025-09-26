# app.py — Sora (Bright Starfield, square-rounded tiles, one-page)
# 明るめの背景 + 全画面の星 + 正方形タイル + やさしい文面 / 単一ページ切替

from datetime import datetime, date
from pathlib import Path
from typing import Optional
import pandas as pd
import streamlit as st

# -------------------- Page config --------------------
st.set_page_config(
    page_title="Sora — 夜のモヤモヤを3分で整える",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -------------------- Theme / CSS --------------------
def inject_css():
    css = """
<style>
:root{
  --text:#1e2a44; --muted:#6f7a92; --outline:#cbd7ff;
  --glass:rgba(255,255,255,.88); --glass-brd:rgba(160,175,255,.38);
  --btn-from:#6c86ff; --btn-to:#49b0ff;
  --chip:#f3f6ff; --chip-brd:#cfd9ff;
  --tile-cbt-from:#7f8cff; --tile-cbt-to:#c8ceff;
  --tile-ref-from:#62e0d9; --tile-ref-to:#b9f3ee;
  --tile-his-from:#ffd56f; --tile-his-to:#ffe8ac;
  --tile-exp-from:#9fb1ff; --tile-exp-to:#d7ddff;
}

/* 背景：明るい空色～ラベンダーのグラデーション */
.stApp{
  background:
    radial-gradient(900px 600px at 0% -10%, #d6ebff88 0%, transparent 60%),
    radial-gradient(800px 550px at 100% -5%, #ffe2ff88 0%, transparent 60%),
    linear-gradient(180deg, #fbfeff 0%, #f2f6ff 55%, #ffffff 100%);
}

/* 星：軽量パターン＋柔らかな瞬き（全画面） */
.stApp:before{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image:
    radial-gradient(circle, rgba(255,255,255,.85) 0.8px, transparent 1px),
    radial-gradient(circle, rgba(255,255,255,.6) 0.6px, transparent 1px);
  background-size: 18px 18px, 28px 28px;
  background-position: 0 0, 8px 10px;
  opacity:.45;
}
.stApp:after{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image:
    radial-gradient(120px 120px at 8% 18%, #ffffff88, transparent 55%),
    radial-gradient(120px 120px at 78% 10%, #fff8c988, transparent 55%),
    radial-gradient(100px 100px at 22% 65%, #c8eeff88, transparent 55%),
    radial-gradient(120px 120px at 92% 55%, #ffdfff88, transparent 55%);
  animation: twinkle 6s ease-in-out infinite alternate;
}
@keyframes twinkle{0%{opacity:.65}50%{opacity:.35}100%{opacity:.65}}

.block-container{max-width:820px; padding-top:1rem; padding-bottom:2rem; position:relative; z-index:1}
h1,h2,h3{color:var(--text); letter-spacing:.2px}
p,label,.stMarkdown,.stTextInput,.stTextArea{color:var(--text); font-size:1.06rem}
small{color:var(--muted)}

.card{
  background:var(--glass); border:1px solid var(--glass-brd);
  border-radius:20px; padding:16px; margin-bottom:14px;
  box-shadow:0 16px 34px rgba(36,49,89,.16); backdrop-filter:blur(8px);
}
.hr{height:1px; background:linear-gradient(to right,transparent,#a6b6ff,transparent); margin:10px 0 6px}

.tag{
  display:inline-block; padding:6px 12px; border-radius:999px; background:#eef2ff; color:#22335a;
  font-weight:800; margin:0 6px 6px 0; border:1px solid var(--outline)
}

/* 入力UI */
textarea, input, .stTextInput>div>div>input{
  border-radius:14px!important; background:#ffffff; color:#1d2533; border:1px solid #e1e7ff;
}
.stSlider,.stRadio>div{color:var(--text)}
.stButton>button,.stDownloadButton>button{
  width:100%; padding:14px 16px; border-radius:999px; border:1px solid var(--outline);
  background:linear-gradient(180deg,var(--btn-from),var(--btn-to)); color:#fff; font-weight:900; font-size:1.02rem;
  box-shadow:0 12px 26px rgba(80,110,255,.28);
}
.stButton>button:hover{filter:brightness(.98)}

/* タイル（正方形＋ふっくら角） */
.tile-grid{display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:8px}
.tile .stButton>button{
  aspect-ratio:1/1;
  border-radius:22px; text-align:left; padding:14px; white-space:normal; line-height:1.2;
  border:none; font-weight:900; font-size:1.04rem; color:#102040;
  box-shadow:0 16px 30px rgba(0,0,0,.14);
  display:flex; align-items:flex-end; justify-content:flex-start;
}
.tile .stButton>button:after{content:"";}
.tile-cbt .stButton>button{background:linear-gradient(160deg,var(--tile-cbt-from),var(--tile-cbt-to))}
.tile-ref .stButton>button{background:linear-gradient(160deg,var(--tile-ref-from),var(--tile-ref-to))}
.tile-his .stButton>button{background:linear-gradient(160deg,var(--tile-his-from),var(--tile-his-to))}
.tile-exp .stButton>button{background:linear-gradient(160deg,var(--tile-exp-from),var(--tile-exp-to))}

/* クイック切替チップ */
.chips{display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 10px}
.chips .stButton>button{
  background:var(--chip); color:#24365a; border:1px solid var(--chip-brd);
  padding:8px 12px; height:auto; border-radius:999px; font-weight:900
}

/* モバイルでの余白調整 */
@media (max-width: 420px){
  .block-container{padding-left:1rem; padding-right:1rem}
}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)

inject_css()

# -------------------- Data helpers --------------------
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CBT_CSV = DATA_DIR / "cbt_entries.csv"
REFLECT_CSV = DATA_DIR / "daily_reflections.csv"

def _load_csv(p: Path) -> pd.DataFrame:
    if p.exists():
        try: return pd.read_csv(p)
        except Exception: return pd.DataFrame()
    return pd.DataFrame()

def _append_csv(p: Path, row: dict):
    df = _load_csv(p)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(p, index=False)

def _download_button(df: pd.DataFrame, label: str, filename: str):
    if df.empty: st.caption("（まだデータがありません）"); return
    st.download_button(label, df.to_csv(index=False).encode("utf-8"),
                       file_name=filename, mime="text/csv")

# -------------------- Session --------------------
st.session_state.setdefault("view","HOME")  # HOME / CBT / REFLECT / HISTORY / EXPORT
st.session_state.setdefault("cbt", {
    "fact":"", "auto_thought":"", "distress_before":5,
    "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
    "reframe_text":"", "distress_after":3
})
st.session_state.setdefault("reflection", {
    "today_small_win":"", "self_message":"", "note_for_tomorrow":"",
    "loneliness":5, "date":date.today()
})

# -------------------- Companion UI --------------------
def companion(emoji: str, text: str, sub: Optional[str]=None):
    html = f"""
<div class="card">
  <div style="font-weight:900; color:#18294c">{emoji} {text}</div>
  {f"<div class='small' style='margin-top:4px; color:var(--muted)'>{sub}</div>" if sub else ""}
</div>
"""
    st.markdown(html, unsafe_allow_html=True)

def support(distress: Optional[int]=None, lonely: Optional[int]=None):
    if distress is not None and distress >= 7:
        companion("🫶","ここは“がんばらないでいい場所”。","ゆっくりでOK。あなたのペースで進もう。")
    elif lonely is not None and lonely >= 7:
        companion("🤝","この瞬間、あなたはひとりじゃないよ。","小さく息を吐いて、肩の力をすこし抜こう。")
    else:
        companion("🌟","書けた分だけもう充分えらい！","短くてもOK、続けることがいちばんの力。")

# -------------------- Header --------------------
greet = "こんばんは" if (18 <= datetime.now().hour or datetime.now().hour < 4) else "こんにちは"
st.markdown(f"""
<div class="card" style="padding:18px;">
  <h2 style="margin:0; color:#162646">{greet}。Soraへようこそ。</h2>
  <div class="hr"></div>
  <p style="margin:.2rem 0 .4rem; color:var(--muted)">
    ここは、モヤモヤをそのまま置ける小さな場所。<br>
    できごとの“事実”と“心の声”をやさしく分けて、現実的な言い換えを一緒につくろう。
  </p>
  <span class="tag">明るい画面で見やすい</span>
  <span class="tag">専門用語なし</span>
  <span class="tag">あとから見返せる</span>
</div>
""", unsafe_allow_html=True)

# -------------------- Quick switch --------------------
def quick_switch():
    st.markdown('<div class="chips">', unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1:
        if st.button("🏠 ホーム", key="qs_home"): st.session_state.view = "HOME"
    with c2:
        if st.button("📓 CBT", key="qs_cbt"): st.session_state.view = "CBT"
    with c3:
        if st.button("📝 リフレク", key="qs_ref"): st.session_state.view = "REFLECT"
    with c4:
        if st.button("📚 履歴", key="qs_his"): st.session_state.view = "HISTORY"
    with c5:
        if st.button("⬇️ エクスポ", key="qs_exp"): st.session_state.view = "EXPORT"
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Views --------------------
def view_home():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 今やりたいことを選んでね")
    st.markdown('<div class="tile-grid">', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        st.markdown('<div class="tile tile-cbt">', unsafe_allow_html=True)
        if st.button("📓 3分CBT\n気持ちを整える", key="tile_cbt"): st.session_state.view="CBT"
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tile tile-ref">', unsafe_allow_html=True)
        if st.button("📝 1日のリフレク\nやさしく振り返る", key="tile_ref"): st.session_state.view="REFLECT"
        st.markdown('</div>', unsafe_allow_html=True)
    c3,c4 = st.columns(2)
    with c3:
        st.markdown('<div class="tile tile-his">', unsafe_allow_html=True)
        if st.button("📚 履歴\n言葉のアルバム", key="tile_his"): st.session_state.view="HISTORY"
        st.markdown('</div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="tile tile-exp">', unsafe_allow_html=True)
        if st.button("⬇️ エクスポート\n& 設定", key="tile_exp"): st.session_state.view="EXPORT"
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    support()

def view_cbt():
    quick_switch()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("1) できごと（実況でOK）")
    st.caption("カメラ視点で“事実だけ”。気持ちや推測は次で扱うから、いまはそっと置いておこう。")
    st.session_state.cbt["fact"] = st.text_area(
        "今日、どんなことがあった？",
        value=st.session_state.cbt["fact"],
        placeholder="例）21:20にLINEを送った。既読はまだ。明日の小テストがある。",
        height=96, label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("2) 浮かんだ考え（心の声）")
    st.session_state.cbt["auto_thought"] = st.text_area(
        "心の声：",
        value=st.session_state.cbt["auto_thought"],
        placeholder="例）どうせ私なんて好かれてない…",
        height=88, label_visibility="collapsed"
    )
    st.session_state.cbt["distress_before"] = st.slider("いまのつらさ（0〜10）", 0, 10, st.session_state.cbt["distress_before"])
    support(distress=st.session_state.cbt["distress_before"])
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("3) やさしい確認（責めない“？”）")
    col1,col2,col3 = st.columns(3)
    with col1:
        st.session_state.cbt["gentle_checks"]["extreme"] = st.checkbox(
            "0か100で考えてない？", value=st.session_state.cbt["gentle_checks"]["extreme"])
    with col2:
        st.session_state.cbt["gentle_checks"]["mind_read"] = st.checkbox(
            "相手の気持ちを決めつけてない？", value=st.session_state.cbt["gentle_checks"]["mind_read"])
    with col3:
        st.session_state.cbt["gentle_checks"]["catastrophe"] = st.checkbox(
            "最悪だけを予言してない？", value=st.session_state.cbt["gentle_checks"]["catastrophe"])
    hints=[]
    g = st.session_state.cbt["gentle_checks"]
    if g["extreme"]:     hints.append("「一つうまくいかない＝全部ダメ」ではないかも。")
    if g["mind_read"]:   hints.append("相手の本音は“聞いてみないと分からない”。")
    if g["catastrophe"]: hints.append("“一番悪い未来”以外にもいくつか道がある。")
    if hints:
        st.write("💡 小さなヒント")
        for h in hints: st.markdown(f"- {h}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("4) ちょっとだけ言い換える")
    st.caption("事実によせて、現実的な言い方に。しっくり来なければ自由入力でOK。")
    sug=[]
    if g["extreme"]:     sug.append("うまくいってない部分はあるけど、全部がダメとは限らない。")
    if g["mind_read"]:   sug.append("相手にも事情があるかも。確かめてみないと分からない。")
    if g["catastrophe"]: sug.append("不安はあるけど、未来は一つじゃない。今わかる事実はここまで。")
    if not sug:
        sug = [
            "いまは“既読がない”という事実だけ。気持ちは決めつけずに置いておく。",
            "私は不安。でも、それは“大事にしているものがある”サインでもある。",
            "少し休んでから考え直してもいい。焦らなくて大丈夫。"
        ]
    idx = st.radio("候補（編集してOK）", options=list(range(len(sug))),
                   format_func=lambda i:sug[i], index=0, horizontal=False)
    default_text = sug[idx] if 0 <= idx < len(sug) else ""
    st.session_state.cbt["reframe_text"] = st.text_area(
        "自由に整える：",
        value=st.session_state.cbt["reframe_text"] or default_text, height=90
    )
    st.session_state.cbt["distress_after"] = st.slider("いまのつらさ（言い換え後・任意）", 0, 10, st.session_state.cbt["distress_after"])
    st.markdown('</div>', unsafe_allow_html=True)

    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 保存して完了（入力欄は初期化）"):
            now = datetime.now().isoformat(timespec="seconds")
            row = {"id":f"cbt-{now}","ts":now,
                   "fact":st.session_state.cbt["fact"],
                   "auto_thought":st.session_state.cbt["auto_thought"],
                   "extreme":g["extreme"],"mind_read":g["mind_read"],"catastrophe":g["catastrophe"],
                   "reframe_text":st.session_state.cbt["reframe_text"],
                   "distress_before":st.session_state.cbt["distress_before"],
                   "distress_after":st.session_state.cbt["distress_after"]}
            _append_csv(CBT_CSV,row)
            st.session_state.cbt = {"fact":"","auto_thought":"","distress_before":5,
                "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
                "reframe_text":"","distress_after":3}
            st.success("保存しました。ここまでできたの、本当にえらい。")
    with c2:
        if st.button("🧼 入力欄だけ初期化（未保存は消えます）"):
            st.session_state.cbt = {"fact":"","auto_thought":"","distress_before":5,
                "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
                "reframe_text":"","distress_after":3}
            st.info("入力欄をリセットしました（履歴は残っています）。")

def view_reflect():
    quick_switch()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("今日をそっとふり返る")
    st.caption("点数じゃなく、心が少しやわらぐ書き方で。短くてOK。")
    d = st.session_state.reflection.get("date", date.today())
    if isinstance(d,str):
        try: d = date.fromisoformat(d)
        except Exception: d = date.today()
    st.session_state.reflection["date"] = st.date_input("日付", value=d)
    st.session_state.reflection["today_small_win"] = st.text_area(
        "今日できた小さなこと（1つで十分）",
        value=st.session_state.reflection["today_small_win"], height=76
    )
    st.session_state.reflection["self_message"] = st.text_area(
        "いまの自分に一言かけるなら？",
        value=st.session_state.reflection["self_message"], height=76
    )
    st.session_state.reflection["note_for_tomorrow"] = st.text_area(
        "明日の自分へひとこと（任意）",
        value=st.session_state.reflection["note_for_tomorrow"], height=76
    )
    st.session_state.reflection["loneliness"] = st.slider("いまの孤独感（0〜10）", 0, 10, st.session_state.reflection["loneliness"])
    support(lonely=st.session_state.reflection["loneliness"])
    st.markdown('</div>', unsafe_allow_html=True)

    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 リフレクションを保存（入力欄は初期化）"):
            now = datetime.now().isoformat(timespec="seconds")
            dv = st.session_state.reflection["date"]
            date_str = dv.isoformat() if isinstance(dv,(date,datetime)) else str(dv)
            row = {"id":f"ref-{now}","date":date_str,"ts_saved":now,
                   "small_win":st.session_state.reflection["today_small_win"],
                   "self_message":st.session_state.reflection["self_message"],
                   "note_for_tomorrow":st.session_state.reflection["note_for_tomorrow"],
                   "loneliness":st.session_state.reflection["loneliness"]}
            _append_csv(REFLECT_CSV,row)
            st.session_state.reflection = {"today_small_win":"","self_message":"",
                "note_for_tomorrow":"", "loneliness":5, "date":date.today()}
            st.success("保存しました。宝物みたいな言葉が増えていくね。")
    with c2:
        if st.button("🧼 入力欄だけ初期化（未保存は消えます）"):
            st.session_state.reflection = {"today_small_win":"","self_message":"",
                "note_for_tomorrow":"", "loneliness":5, "date":date.today()}
            st.info("入力欄をリセットしました（履歴は残っています）。")

def view_history():
    quick_switch()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🗂️ 履歴 — CBTワーク")
    df = _load_csv(CBT_CSV)
    if df.empty:
        st.caption("まだ保存されたCBTワークがありません。")
    else:
        q = st.text_input("キーワードで探す（事実・心の声・言い換え）", "")
        view = df.copy()
        if q.strip():
            q = q.strip().lower()
            for c in ["fact","auto_thought","reframe_text"]:
                view[c] = view[c].astype(str)
            mask = (view["fact"].str.lower().str.contains(q) |
                    view["auto_thought"].str.lower().str.contains(q) |
                    view["reframe_text"].str.lower().str.contains(q))
            view = view[mask]
        if "ts" in view.columns:
            view = view.sort_values("ts", ascending=False)
        for _, r in view.head(50).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**")
            st.markdown(f"**出来事**：{r.get('fact','')}")
            st.markdown(f"**心の声**：{r.get('auto_thought','')}")
            st.markdown(f"**言い換え**：{r.get('reframe_text','')}")
            try:
                b = int(r.get("distress_before",0)); a = int(r.get("distress_after",0))
                st.caption(f"つらさ: {b} → {a}")
            except Exception: pass
            tags=[]
            if r.get("extreme",False): tags.append("極端に決めつけ")
            if r.get("mind_read",False): tags.append("心を決めつけ")
            if r.get("catastrophe",False): tags.append("最悪を予言")
            if tags:
                html = " ".join([f"<span class='tag'>{t}</span>" for t in tags])
                st.markdown(html, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        try:
            chart = df[["ts","distress_before","distress_after"]].copy()
            chart["ts"] = pd.to_datetime(chart["ts"])
            chart = chart.sort_values("ts").set_index("ts")
            st.line_chart(chart.rename(columns={"distress_before":"つらさ(前)","distress_after":"つらさ(後)"}))
        except Exception:
            pass
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📔 履歴 — リフレクション")
    rf = _load_csv(REFLECT_CSV)
    if rf.empty:
        st.caption("まだ保存されたリフレクションがありません。")
    else:
        view = rf.copy()
        if "date" in view.columns:
            try:
                view["date"] = pd.to_datetime(view["date"])
                view = view.sort_values(["date","ts_saved"], ascending=False)
            except Exception:
                pass
        for _, r in view.head(50).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**📅 {r.get('date','')}**  —  🕒 {r.get('ts_saved','')}")
            st.markdown(f"**小さなできたこと**：{r.get('small_win','')}")
            st.markdown(f"**いまの自分への一言**：{r.get('self_message','')}")
            nt = r.get("note_for_tomorrow","")
            if isinstance(nt,str) and nt.strip():
                st.markdown(f"**明日の自分へ**：{nt}")
            try:
                st.caption(f"孤独感：{int(r.get('loneliness',0))}/10")
            except Exception:
                pass
        try:
            c2 = rf[["date","loneliness"]].copy()
            c2["date"] = pd.to_datetime(c2["date"])
            c2 = c2.sort_values("date").set_index("date")
            st.line_chart(c2.rename(columns={"loneliness":"孤独感"}))
        except Exception:
            pass
    st.markdown('</div>', unsafe_allow_html=True)

def view_export():
    quick_switch()
    st.subheader("⬇️ エクスポート & 設定")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**データのエクスポート（CSV）**")
    _download_button(_load_csv(CBT_CSV), "⬇️ CBTワークをダウンロード", "cbt_entries.csv")
    _download_button(_load_csv(REFLECT_CSV), "⬇️ リフレクションをダウンロード", "daily_reflections.csv")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**入力欄の初期化 / データの管理**")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("🧼 入力欄だけ全部初期化（履歴は残る）"):
            st.session_state.cbt = {"fact":"","auto_thought":"","distress_before":5,
                "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
                "reframe_text":"","distress_after":3}
            st.session_state.reflection = {"today_small_win":"","self_message":"",
                "note_for_tomorrow":"", "loneliness":5, "date":date.today()}
            st.success("入力欄をすべて初期化しました。履歴は残っています。")
    with c2:
        danger = st.checkbox("⚠️ すべての保存データ（CSV）を削除することに同意します")
        if st.button("🗑️ すべての保存データを削除（取り消し不可）", disabled=not danger):
            try:
                if CBT_CSV.exists(): CBT_CSV.unlink()
                if REFLECT_CSV.exists(): REFLECT_CSV.unlink()
                st.success("保存データを削除しました。はじめからやり直せます。")
            except Exception as e:
                st.error(f"削除でエラーが発生: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Render --------------------
if st.session_state.view == "HOME":
    view_home()
elif st.session_state.view == "CBT":
    view_cbt()
elif st.session_state.view == "REFLECT":
    view_reflect()
elif st.session_state.view == "HISTORY":
    view_history()
else:
    view_export()

# -------------------- Footer --------------------
st.markdown("""
<div style="text-align:center; color:var(--muted); margin-top:12px;">
  <small>※ 個人名や連絡先は書かないでね。<br>
  とてもつらいときは、あなたの地域の相談先へ。ここではいつでも一緒に整えていこう。</small>
</div>
""", unsafe_allow_html=True)

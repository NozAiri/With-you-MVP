# app.py — Sora (Bright & friendly, star-sprinkled, one-page tiles)

from datetime import datetime, date
from pathlib import Path
from typing import Optional
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Sora — 夜のモヤモヤをやさしく整える",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------- Theme (明るい星空 / 正方形タイル) ----------
def build_css(stars: bool = True) -> str:
    return f"""
    <style>
    :root{{
      --text:#1d2a44; --muted:#62708b; --outline:#cfd9ff;
      --card-bg:rgba(255,255,255,.92); --card-border:rgba(170,185,255,.45);
      --btn-from:#7aa7ff; --btn-to:#5fc3ff;
      --tile-cbt-from:#7f8bff; --tile-cbt-to:#bfc3ff;
      --tile-ref-from:#57e1d6; --tile-ref-to:#aaf1ea;
      --tile-his-from:#ffd56e; --tile-his-to:#ffe7ad;
      --tile-exp-from:#9aa8ff; --tile-exp-to:#ced4ff;
      --chip:#f4f6ff;
    }}

    /* 背景：明るい空色〜ラベンダー＋星を全面に */
    .stApp{{
      background:
        radial-gradient(1200px 800px at 10% -10%, #cfe6ffaa 0%, transparent 60%),
        radial-gradient(900px 700px at 100% 0%, #ffe3ff99 0%, transparent 65%),
        linear-gradient(180deg, #f8fbff 0%, #eef3ff 55%, #ffffff 100%);
    }}
    {"".join([
    """
    .stApp:before{
      content:""; position:fixed; inset:-20% -10% -10% -10%; pointer-events:none; z-index:0;
      /* 大小2層の星（優しくきらめく） */
      background-image:
        radial-gradient(1.6px 1.6px at 8% 15%, #a6c9ffcc, transparent 38%),
        radial-gradient(1.6px 1.6px at 18% 35%, #ffffffcc, transparent 40%),
        radial-gradient(1.8px 1.8px at 30% 10%, #ffdfffcc, transparent 40%),
        radial-gradient(1.4px 1.4px at 45% 22%, #fffbe0cc, transparent 40%),
        radial-gradient(1.2px 1.2px at 65% 18%, #ffffffcc, transparent 40%),
        radial-gradient(1.6px 1.6px at 80% 8%,  #bfeaffcc, transparent 40%),
        radial-gradient(1.8px 1.8px at 90% 26%, #d9f1ffcc, transparent 40%),
        radial-gradient(1.4px 1.4px at 72% 44%, #ffffffaa, transparent 40%),
        radial-gradient(1.2px 1.2px at 12% 58%, #ffffffaa, transparent 40%),
        radial-gradient(1.6px 1.6px at 34% 70%, #fff3b5cc, transparent 40%),
        radial-gradient(1.2px 1.2px at 55% 78%, #ffffffcc, transparent 40%),
        radial-gradient(1.6px 1.6px at 86% 62%, #cfe9ffcc, transparent 40%);
      background-repeat:no-repeat; opacity:.9;
      animation: twinkle1 6s ease-in-out infinite alternate;
    }
    .stApp:after{
      content:""; position:fixed; inset:-25% -15% -15% -15%; pointer-events:none; z-index:0;
      background-image:
        radial-gradient(1.0px 1.0px at 5% 10%, #ffffffaa, transparent 40%),
        radial-gradient(1.0px 1.0px at 22% 6%, #ffffffaa, transparent 40%),
        radial-gradient(1.0px 1.0px at 48% 14%, #ffffffaa, transparent 40%),
        radial-gradient(1.0px 1.0px at 70% 8%, #ffffffaa, transparent 40%),
        radial-gradient(1.0px 1.0px at 82% 30%, #ffffffaa, transparent 40%),
        radial-gradient(1.0px 1.0px at 60% 52%, #ffffffaa, transparent 40%),
        radial-gradient(1.0px 1.0px at 28% 68%, #ffffffaa, transparent 40%),
        radial-gradient(1.0px 1.0px at 90% 80%, #ffffffaa, transparent 40%);
      background-repeat:no-repeat; opacity:.65;
      animation: twinkle2 9s ease-in-out infinite alternate;
    }
    @keyframes twinkle1 { 0%{opacity:.95} 50%{opacity:.55} 100%{opacity:.95} }
    @keyframes twinkle2 { 0%{opacity:.7} 50%{opacity:.4} 100%{opacity:.7} }
    """
    ]) if stars else "" )}

    .block-container{{max-width:820px; padding-top:1.0rem; padding-bottom:2.0rem; position:relative; z-index:1}}
    h1,h2,h3{{color:var(--text)}}
    p,label,.stMarkdown,.stTextInput,.stTextArea{{color:var(--text); font-size:1.06rem}}
    small,.help{{color:var(--muted)!important; font-size:.92rem}}

    .card{{
      background:var(--card-bg); border:1px solid var(--card-border); border-radius:22px;
      padding:16px; box-shadow:0 18px 36px rgba(63,100,180,.18); margin-bottom:14px; backdrop-filter:blur(8px);
    }}
    .hr{{height:1px; background:linear-gradient(to right, transparent, #a9b8ff, transparent); margin:10px 0 6px}}
    .tag{{display:inline-block; padding:6px 12px; border-radius:999px; background:#eef2ff; color:#2b3c63;
      font-weight:800; margin:0 6px 6px 0; border:1px solid var(--outline)}}

    /* 入力の見た目もやさしく */
    textarea, input, .stTextInput>div>div>input{{
      border-radius:14px!important; background:#ffffff; color:#182540; border:1px solid #dfe6ff;
    }}

    /* ボタン */
    .stButton>button, .stDownloadButton>button{{
      width:100%; padding:14px 16px; border-radius:999px; border:1px solid var(--outline);
      background:linear-gradient(180deg, var(--btn-from), var(--btn-to)); color:#fff; font-weight:900; font-size:1.02rem;
      box-shadow:0 12px 26px rgba(95,150,255,.28);
    }}
    .stButton>button:hover{{filter:brightness(.97)}}

    /* ----- ホームのタイル（正方形＋丸み） ----- */
    .tile-grid{{display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:8px}}
    .tile .stButton>button{{
      aspect-ratio:1 / 1;  /* 正方形 */
      border-radius:24px; text-align:left; padding:16px; white-space:normal; line-height:1.25;
      border:none; font-weight:900; font-size:1.06rem; box-shadow:0 16px 32px rgba(0,0,0,.14); color:#0e1a33;
    }}
    .tile .sub{{display:block; margin-top:6px; font-weight:700; font-size:.95rem; opacity:.9}}
    .tile-cbt .stButton>button{{background:linear-gradient(160deg,var(--tile-cbt-from),var(--tile-cbt-to))}}
    .tile-ref .stButton>button{{background:linear-gradient(160deg,var(--tile-ref-from),var(--tile-ref-to))}}
    .tile-his .stButton>button{{background:linear-gradient(160deg,var(--tile-his-from),var(--tile-his-to))}}
    .tile-exp .stButton>button{{background:linear-gradient(160deg,var(--tile-exp-from),var(--tile-exp-to))}}
    .tile .stButton>button:after{{content:"›"; float:right; font-size:1.6rem; opacity:.9; color:#0e1a33}}

    /* セクション上のクイック切替 */
    .chips{{display:flex; gap:8px; flex-wrap:wrap; margin:6px 0 10px}}
    .chips .stButton>button{{background:var(--chip); color:#263556; border:1px solid var(--outline);
      padding:8px 12px; height:auto; border-radius:999px; font-weight:800}}
    </style>
    """

st.markdown(build_css(stars=True), unsafe_allow_html=True)

# ---------- Data helpers ----------
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
CBT_CSV = DATA_DIR / "cbt_entries.csv"
REFLECT_CSV = DATA_DIR / "daily_reflections.csv"

def _load_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        try: return pd.read_csv(path)
        except Exception: return pd.DataFrame()
    return pd.DataFrame()

def _append_csv(path: Path, row: dict):
    df = _load_csv(path)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False)

def _download_button(df: pd.DataFrame, label: str, filename: str):
    if df.empty: st.caption("（まだデータがありません）"); return
    st.download_button(label, df.to_csv(index=False).encode("utf-8"),
                       file_name=filename, mime="text/csv")

# ---------- State ----------
if "view" not in st.session_state: st.session_state.view = "HOME"
if "cbt" not in st.session_state:
    st.session_state.cbt = {"fact":"", "auto_thought":"", "distress_before":5,
        "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
        "reframe_text":"", "distress_after":3}
if "reflection" not in st.session_state:
    st.session_state.reflection = {"today_small_win":"", "self_message":"",
        "note_for_tomorrow":"", "loneliness":5, "date":date.today()}

# ---------- Friendly helper ----------
def companion(emoji: str, text: str, sub: Optional[str]=None):
    st.markdown(f"""
    <div class="card">
      <div style="font-weight:900;">{emoji} {text}</div>
      {f"<div class='small' style='margin-top:4px; color:var(--muted)'>{sub}</div>" if sub else ""}
    </div>
    """, unsafe_allow_html=True)

def support(distress: Optional[int]=None, lonely: Optional[int]=None):
    if distress is not None and distress >= 7:
        companion("🕊️","いまは“がんばる”より“やさしくする”時間。","深呼吸ひとつでOK。ここに一緒にいるよ。")
    elif lonely is not None and lonely >= 7:
        companion("🤝","この瞬間、あなたは独りじゃないよ。","ゆっくりでいい。言葉はちゃんと届くから。")
    else:
        companion("🌟","書けた分だけ、もう前進してる。","短くても十分。続けていけば大丈夫。")

# ---------- Header ----------
greet = "こんばんは" if (18 <= datetime.now().hour or datetime.now().hour < 4) else "こんにちは"
st.markdown(f"""
<div class="card" style="padding:18px;">
  <h2 style="margin:0;">{greet}、Soraへようこそ。</h2>
  <div class="hr"></div>
  <p style="margin:.2rem 0 .4rem;">
    ここは、夜の気持ちにそっと寄り添う小さな場所。<br>
    事実と心の声を分けて、やさしい言い換えを一緒に見つけよう。
  </p>
  <span class="tag">3分でできる</span>
  <span class="tag">やさしいことば</span>
  <span class="tag">あとから見返せる</span>
</div>
""", unsafe_allow_html=True)

# ---------- Quick switch ----------
def quick_switch():
    st.markdown('<div class="chips">', unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1:
        if st.button("🏠 ホーム"): st.session_state.view="HOME"
    with c2:
        if st.button("📓 CBT"): st.session_state.view="CBT"
    with c3:
        if st.button("📝 リフレク"): st.session_state.view="REFLECT"
    with c4:
        if st.button("📚 履歴"): st.session_state.view="HISTORY"
    with c5:
        if st.button("⬇️ エクスポ"): st.session_state.view="EXPORT"
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Views ----------
def view_home():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### いま、したいことを選んでね")
    st.markdown('<div class="tile-grid">', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        st.markdown('<div class="tile tile-cbt">', unsafe_allow_html=True)
        if st.button("📓 いま整える\n（3分CBT）", key="tile_cbt"): st.session_state.view="CBT"
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="tile tile-ref">', unsafe_allow_html=True)
        if st.button("📝 今日をふんわり振り返る\n（リフレク）", key="tile_ref"): st.session_state.view="REFLECT"
        st.markdown('</div>', unsafe_allow_html=True)
    c3,c4 = st.columns(2)
    with c3:
        st.markdown('<div class="tile tile-his">', unsafe_allow_html=True)
        if st.button("📚 言葉のアルバム\n（履歴）", key="tile_his"): st.session_state.view="HISTORY"
        st.markdown('</div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="tile tile-exp">', unsafe_allow_html=True)
        if st.button("⬇️ まとめる・設定\n（エクスポート）", key="tile_exp"): st.session_state.view="EXPORT"
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    support()

def view_cbt():
    quick_switch()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("1) できごと（実況でOK）")
    st.caption("カメラ視点で“事実だけ”。気持ちや推測は次で扱うから、いまは置いておこう。")
    st.session_state.cbt["fact"]=st.text_area("今日、どんなことがあった？",
        value=st.session_state.cbt["fact"],
        placeholder="例）21:20にメッセージ送信。いまは既読なし。明日は早起きの予定。",
        height=96, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("2) 浮かんだ考え（心の声）")
    st.session_state.cbt["auto_thought"]=st.text_area("心の声：",
        value=st.session_state.cbt["auto_thought"],
        placeholder="例）きっと嫌われた…／また失敗するかも…", height=88, label_visibility="collapsed")
    st.session_state.cbt["distress_before"]=st.slider("いまのつらさ（0〜10）",0,10,st.session_state.cbt["distress_before"])
    support(distress=st.session_state.cbt["distress_before"])
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("3) やさしい確認（責めない“？”）")
    col1,col2,col3=st.columns(3)
    with col1:
        st.session_state.cbt["gentle_checks"]["extreme"]=st.checkbox("0か100で決めつけてない？",
            value=st.session_state.cbt["gentle_checks"]["extreme"])
    with col2:
        st.session_state.cbt["gentle_checks"]["mind_read"]=st.checkbox("相手の心を読みすぎてない？",
            value=st.session_state.cbt["gentle_checks"]["mind_read"])
    with col3:
        st.session_state.cbt["gentle_checks"]["catastrophe"]=st.checkbox("“最悪”だけを想像してない？",
            value=st.session_state.cbt["gentle_checks"]["catastrophe"])
    hints=[]; g=st.session_state.cbt["gentle_checks"]
    if g["extreme"]:     hints.append("一つうまくいかない＝全部ダメ、じゃないかも。")
    if g["mind_read"]:   hints.append("相手の気持ちは、聞いてみないと分からない。")
    if g["catastrophe"]: hints.append("未来は一つじゃない。いま分かる事実に戻ってみよう。")
    if hints:
        st.write("💡 小さなヒント")
        for h in hints: st.markdown(f"- {h}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("4) ちょっとだけ言い換える")
    st.caption("事実に寄せて、現実的でやさしい言い方に。ピンと来なければ自由入力でOK。")
    sug=[]
    if g["extreme"]:     sug.append("まだうまくいってない部分はあるけど、全部がダメとは限らない。")
    if g["mind_read"]:   sug.append("相手にも事情があるかも。確認してみないと分からない。")
    if g["catastrophe"]: sug.append("不安はあるけど、未来は一つじゃない。いま分かる事実はここまで。")
    if not sug:
        sug=["いまは“既読がない”という事実だけ。気持ちは決めつけずに置いておく。",
             "不安なのは、それだけ大切に思っているから。私は私を責めなくて大丈夫。",
             "少し休んでから考え直してみる。焦らなくていい。"]
    idx=st.radio("候補（編集してOK）", options=list(range(len(sug))),
                 format_func=lambda i:sug[i], index=0, horizontal=False)
    default_text=sug[idx] if 0<=idx<len(sug) else ""
    st.session_state.cbt["reframe_text"]=st.text_area("自由に整える：",
        value=st.session_state.cbt["reframe_text"] or default_text, height=90)
    st.session_state.cbt["distress_after"]=st.slider("いまのつらさ（言い換え後・任意）",0,10,st.session_state.cbt["distress_after"])
    st.markdown('</div>', unsafe_allow_html=True)

    c1,c2=st.columns(2)
    with c1:
        if st.button("💾 保存して完了（入力欄は初期化）"):
            now=datetime.now().isoformat(timespec="seconds")
            row={"id":f"cbt-{now}","ts":now,
                 "fact":st.session_state.cbt["fact"],
                 "auto_thought":st.session_state.cbt["auto_thought"],
                 "extreme":g["extreme"],"mind_read":g["mind_read"],"catastrophe":g["catastrophe"],
                 "reframe_text":st.session_state.cbt["reframe_text"],
                 "distress_before":st.session_state.cbt["distress_before"],
                 "distress_after":st.session_state.cbt["distress_after"]}
            _append_csv(CBT_CSV,row)
            st.session_state.cbt={"fact":"", "auto_thought":"", "distress_before":5,
                "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
                "reframe_text":"", "distress_after":3}
            st.success("保存できたよ。ここまで来られたの、とってもえらい。")
    with c2:
        if st.button("🧼 入力欄だけ初期化（未保存は消えます）"):
            st.session_state.cbt={"fact":"", "auto_thought":"", "distress_before":5,
                "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
                "reframe_text":"", "distress_after":3}
            st.info("入力欄をリセットしました（履歴は残っています）。")

def view_reflect():
    quick_switch()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("今日をそっとふり返る")
    st.caption("点数じゃなく、心が少し軽くなる書き方で。短くてOK。")
    d=st.session_state.reflection.get("date", date.today())
    if isinstance(d,str):
        try: d=date.fromisoformat(d)
        except Exception: d=date.today()
    st.session_state.reflection["date"]=st.date_input("日付", value=d)
    st.session_state.reflection["today_small_win"]=st.text_area(
        "今日できた小さなこと（1つで十分）", value=st.session_state.reflection["today_small_win"], height=76)
    st.session_state.reflection["self_message"]=st.text_area(
        "いまの自分にかけたい一言", value=st.session_state.reflection["self_message"], height=76)
    st.session_state.reflection["note_for_tomorrow"]=st.text_area(
        "明日の自分へ（任意）", value=st.session_state.reflection["note_for_tomorrow"], height=76)
    st.session_state.reflection["loneliness"]=st.slider("いまの心細さ（0〜10）",0,10,st.session_state.reflection["loneliness"])
    support(lonely=st.session_state.reflection["loneliness"])
    st.markdown('</div>', unsafe_allow_html=True)

    c1,c2=st.columns(2)
    with c1:
        if st.button("💾 リフレクションを保存（入力欄は初期化）"):
            now=datetime.now().isoformat(timespec="seconds")
            dv=st.session_state.reflection["date"]
            date_str=dv.isoformat() if isinstance(dv,(date,datetime)) else str(dv)
            row={"id":f"ref-{now}","date":date_str,"ts_saved":now,
                 "small_win":st.session_state.reflection["today_small_win"],
                 "self_message":st.session_state.reflection["self_message"],
                 "note_for_tomorrow":st.session_state.reflection["note_for_tomorrow"],
                 "loneliness":st.session_state.reflection["loneliness"]}
            _append_csv(REFLECT_CSV,row)
            st.session_state.reflection={"today_small_win":"", "self_message":"",
                "note_for_tomorrow":"", "loneliness":5, "date":date.today()}
            st.success("保存できたよ。あなたの言葉、ちゃんと残っていく。")
    with c2:
        if st.button("🧼 入力欄だけ初期化（未保存は消えます）"):
            st.session_state.reflection={"today_small_win":"", "self_message":"",
                "note_for_tomorrow":"", "loneliness":5, "date":date.today()}
            st.info("入力欄をリセットしました（履歴は残っています）。")

def view_history():
    quick_switch()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📘 言葉のアルバム（CBT）")
    df=_load_csv(CBT_CSV)
    if df.empty: st.caption("まだ保存されたCBTワークがありません。")
    else:
        q=st.text_input("キーワードで探す（事実・心の声・言い換え）", "")
        view=df.copy()
        if q.strip():
            q=q.strip().lower()
            for c in ["fact","auto_thought","reframe_text"]:
                view[c]=view[c].astype(str)
            mask=(view["fact"].str.lower().str.contains(q)|
                  view["auto_thought"].str.lower().str.contains(q)|
                  view["reframe_text"].str.lower().str.contains(q))
            view=view[mask]
        if "ts" in view.columns: view=view.sort_values("ts", ascending=False)
        for _,r in view.head(50).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**🕒 {r.get('ts','')}**")
            st.markdown(f"**出来事**：{r.get('fact','')}")
            st.markdown(f"**心の声**：{r.get('auto_thought','')}")
            st.markdown(f"**言い換え**：{r.get('reframe_text','')}")
            try:
                b=int(r.get("distress_before",0)); a=int(r.get("distress_after",0))
                st.caption(f"つらさ: {b} → {a}")
            except Exception: pass
            tags=[]
            if r.get("extreme",False): tags.append("極端に決めつけ")
            if r.get("mind_read",False): tags.append("心を決めつけ")
            if r.get("catastrophe",False): tags.append("最悪を予言")
            if tags:
                st.markdown(" ".join([f"<span class='tag'>{t}</span>" for t in tags]),
                            unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        try:
            chart=df[["ts","distress_before","distress_after"]].copy()
            chart["ts"]=pd.to_datetime(chart["ts"])
            chart=chart.sort_values("ts").set_index("ts")
            st.line_chart(chart.rename(columns={"distress_before":"つらさ(前)","distress_after":"つらさ(後)"}))
        except Exception: pass
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📔 言葉のアルバム（リフレク）")
    rf=_load_csv(REFLECT_CSV)
    if rf.empty: st.caption("まだ保存されたリフレクションがありません。")
    else:
        view=rf.copy()
        if "date" in view.columns:
            try:
                view["date"]=pd.to_datetime(view["date"])
                view=view.sort_values(["date","ts_saved"], ascending=False)
            except Exception: pass
        for _,r in view.head(50).iterrows():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"**📅 {r.get('date','')}**  —  🕒 {r.get('ts_saved','')}")
            st.markdown(f"**小さなできたこと**：{r.get('small_win','')}")
            st.markdown(f"**いまの自分への一言**：{r.get('self_message','')}")
            nt=r.get("note_for_tomorrow","")
            if isinstance(nt,str) and nt.strip():
                st.markdown(f"**明日の自分へ**：{nt}")
            try: st.caption(f"心細さ：{int(r.get('loneliness',0))}/10")
            except Exception: pass
        try:
            c2=rf[["date","loneliness"]].copy()
            c2["date"]=pd.to_datetime(c2["date"])
            c2=c2.sort_values("date").set_index("date")
            st.line_chart(c2.rename(columns={"loneliness":"心細さ"}))
        except Exception: pass
    st.markdown('</div>', unsafe_allow_html=True)

def view_export():
    quick_switch()
    st.subheader("⬇️ エクスポート & 設定")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**データをCSVで保存**")
    _download_button(_load_csv(CBT_CSV), "⬇️ CBTワークをダウンロード", "cbt_entries.csv")
    _download_button(_load_csv(REFLECT_CSV), "⬇️ リフレクションをダウンロード", "daily_reflections.csv")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("**入力欄の初期化 / データの管理**")
    c1,c2=st.columns(2)
    with c1:
        if st.button("🧼 入力欄だけ全部初期化（履歴は残る）"):
            st.session_state.cbt={"fact":"", "auto_thought":"", "distress_before":5,
                "gentle_checks":{"extreme":False,"mind_read":False,"catastrophe":False},
                "reframe_text":"", "distress_after":3}
            st.session_state.reflection={"today_small_win":"", "self_message":"",
                "note_for_tomorrow":"", "loneliness":5, "date":date.today()}
            st.success("入力欄を初期化しました。履歴はそのまま残っています。")
    with c2:
        danger=st.checkbox("⚠️ すべての保存データ（CSV）を削除することに同意します")
        if st.button("🗑️ すべての保存データを削除（取り消し不可）", disabled=not danger):
            try:
                if CBT_CSV.exists(): CBT_CSV.unlink()
                if REFLECT_CSV.exists(): REFLECT_CSV.unlink()
                st.success("保存データを削除しました。ここから新しく始められます。")
            except Exception as e:
                st.error(f"削除でエラーが発生: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- Render ----------
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

# ---------- Footer ----------
st.markdown("""
<div style="text-align:center; color:var(--muted); margin-top:12px;">
  <small>※ 個人名や連絡先は書かないでね。<br>
  とてもつらいときは、あなたの地域の相談先に連絡してね。</small>
</div>
""", unsafe_allow_html=True)
